
from django.db.models import (
    Count,
    Sum,
    F,
    Q,
    OuterRef,
    Subquery,
)

from apps.quiz.models import Quiz, QuizAttempt
from apps.recommendations.models import PerformanceReset
from apps.documents.models import Document


def get_topic_performance(student, document_id, topic="all"):
    """
    Calculate performance for a selected PDF and topic.

    All-topic resets apply to every topic.
    Topic-specific resets apply only to that topic.
    Previous attempts remain preserved in the database.
    """

    topic = topic.strip()
    is_all_topics = topic.casefold() == "all"

    attempts = QuizAttempt.objects.filter(
        student=student,
        status="completed",
        quiz__document_id=document_id,
    )

    if not is_all_topics:
        attempts = attempts.filter(
            quiz__topic__iexact=topic
        )

    reset_events = PerformanceReset.objects.filter(
        student=student,
        document_id=document_id,
    )

    if is_all_topics:
        reset_events = reset_events.filter(
            Q(topic__iexact="all")
            | Q(topic__iexact=OuterRef("quiz__topic"))
        )
    else:
        reset_events = reset_events.filter(
            Q(topic__iexact="all")
            | Q(topic__iexact=topic)
        )

    attempts = attempts.annotate(
        reset_cutoff=Subquery(
            reset_events.order_by("-reset_at").values("reset_at")[:1]
        )
    ).filter(
        Q(reset_cutoff__isnull=True)
        | Q(completed_at__gt=F("reset_cutoff"))
    )

    stats = attempts.aggregate(
        attempt_count=Count("id"),
        total_score=Sum("score"),
        total_marks=Sum("total_marks"),
    )

    attempt_count = stats["attempt_count"] or 0
    total_score = stats["total_score"] or 0
    total_marks = stats["total_marks"] or 0

    selected_topic = (
        "All Topics" if is_all_topics else topic
    )

    if attempt_count == 0 or total_marks <= 0:
        return {
            "document_id": document_id,
            "topic": selected_topic,
            "attempt_count": 0,
            "total_score": 0,
            "total_marks": 0,
            "percentage": None,
            "recommended_difficulty": "medium",
            "message": (
                "No previous performance data found for this selection. "
                "Medium difficulty is recommended."
            ),
        }

    percentage = (total_score / total_marks) * 100

    if percentage < 50:
        difficulty = "easy"
    elif percentage < 70:
        difficulty = "medium"
    else:
        difficulty = "hard"

    return {
        "document_id": document_id,
        "topic": selected_topic,
        "attempt_count": attempt_count,
        "total_score": float(total_score),
        "total_marks": float(total_marks),
        "percentage": round(percentage, 2),
        "recommended_difficulty": difficulty,
        "message": (
            f"Based on your previous performance ({percentage:.2f}%), "
            f"{difficulty} difficulty is recommended."
        ),
    }


def generate_personalized_recommendations(student):
    """
    Generate document-wise and topic-wise recommendations.

    Only completed attempts after the latest applicable reset
    are considered.
    """

    topic_groups = (
        QuizAttempt.objects.filter(
            student=student,
            status="completed",
        )
        .values(
            "quiz__document_id",
            "quiz__topic",
        )
        .distinct()
        .order_by(
            "quiz__document_id",
            "quiz__topic",
        )
    )

    # Fetch document titles efficiently.
    document_ids = {
        group["quiz__document_id"]
        for group in topic_groups
    }

    documents = Document.objects.in_bulk(document_ids)

    recommendations = []

    for group in topic_groups:
        document_id = group["quiz__document_id"]
        topic = group["quiz__topic"]

        document = documents.get(document_id)

        performance = get_topic_performance(
            student=student,
            document_id=document_id,
            topic=topic,
        )

        if performance["percentage"] is None:
            continue

        percentage = performance["percentage"]

        if percentage < 50:
            category = "Needs Practice"
            priority = "High"

            message = (
                f"You need more practice in {topic}. "
                "Revise the fundamental concepts and review "
                "the questions you answered incorrectly."
            )

            suggestion = (
                "Revise the topic and attempt another practice quiz."
            )

        elif percentage < 70:
            category = "Developing"
            priority = "Medium"

            message = (
                f"You are making progress in {topic}. "
                "Review difficult concepts to improve your understanding."
            )

            suggestion = (
                "Review your previous answers and practise again."
            )

        else:
            category = "Strong"
            priority = "Low"

            message = (
                f"You are performing well in {topic}. "
                "Continue learning beyond the basic concepts."
            )

            suggestion = (
                "Try a more challenging quiz or advanced concepts."
            )

        recommendations.append({
            "document_id": document_id,
            "document_title": (
                document.title if document else "Unknown Document"
            ),
            "topic": topic,
            "attempt_count": performance["attempt_count"],
            "percentage": percentage,
            "category": category,
            "priority": priority,
            "message": message,
            "suggestion": suggestion,
        })

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    recommendations.sort(
        key=lambda item: (
            priority_order[item["priority"]],
            item["percentage"],
        )
    )

    return recommendations


def get_document_topics(student, document_id):
    """
    Return topics from quizzes generated by the student
    using the selected PDF.
    """

    return list(
        Quiz.objects.filter(
            created_by=student,
            document_id=document_id,
        )
        .values_list("topic", flat=True)
        .distinct()
        .order_by("topic")
    )
