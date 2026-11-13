from django.db.models import Count, Sum, F, Q, OuterRef, Subquery

from apps.quiz.models import Quiz,QuizAttempt

from apps.recommendations.models import PerformanceReset

def generate_personalized_recommendations(student):
    """
    Generate topic-wise study recommendations
    based on a student's completed quiz attempts.
    """

    completed_attempts = QuizAttempt.objects.filter(
        student=student,
        status="completed",
    )

    topic_stats = completed_attempts.values(
        "quiz__topic"
    ).annotate(
        attempt_count=Count("id"),
        total_score=Sum("score"),
        total_marks=Sum("total_marks"),
    ).order_by("quiz__topic")

    recommendations = []

    for item in topic_stats:
        topic = item["quiz__topic"]
        score = item["total_score"] or 0
        marks = item["total_marks"] or 0

        if marks <= 0:
            continue

        percentage = (score / marks) * 100

        if percentage < 50:
            category = "Needs Practice"
            priority = "High"
            message = (
                f"You need more practice in {topic}. "
                "Revise the fundamental concepts and review "
                "the questions you answered incorrectly."
            )
            suggestion = "Revise the topic and attempt another practice quiz."

        elif percentage < 70:
            category = "Developing"
            priority = "Medium"
            message = (
                f"You are making progress in {topic}. "
                "Review difficult concepts to improve your understanding."
            )
            suggestion = "Review your previous answers and practise again."

        else:
            category = "Strong"
            priority = "Low"
            message = (
                f"You are performing well in {topic}. "
                "Continue learning beyond the basic concepts."
            )
            suggestion = "Try a more challenging quiz or advanced concepts."

        recommendations.append({
            "topic": topic,
            "attempt_count": item["attempt_count"],
            "percentage": round(percentage, 2),
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
        key=lambda item: priority_order[item["priority"]]
    )

    return recommendations


def get_topic_performance(student, document_id, topic="all"):
    """
    Calculate performance using only completed attempts
    after the latest applicable performance reset.
    """

    topic = topic.strip()
    is_all_topics = topic.casefold() == "all"

    attempts = QuizAttempt.objects.filter(
        student=student,
        status="completed",
        quiz__document_id=document_id,
    )

    # Filter attempts for a specific topic when selected.
    if not is_all_topics:
        attempts = attempts.filter(
            quiz__topic__iexact=topic
        )

    # Find the latest applicable reset for each attempt.
    reset_events = PerformanceReset.objects.filter(
        student=student,
        document_id=document_id,
    )

    if is_all_topics:
        reset_events = reset_events.filter(
            Q(topic="all") |
            Q(topic=OuterRef("quiz__topic"))
        )
    else:
        reset_events = reset_events.filter(
            Q(topic="all") |
            Q(topic__iexact=topic)
        )

    attempts = attempts.annotate(
        reset_cutoff=Subquery(
            reset_events.order_by("-reset_at").values("reset_at")[:1]
        )
    ).filter(
        Q(reset_cutoff__isnull=True) |
        Q(completed_at__gt=F("reset_cutoff"))
    )

    stats = attempts.aggregate(
        attempt_count=Count("id"),
        total_score=Sum("score"),
        total_marks=Sum("total_marks"),
    )

    attempt_count = stats["attempt_count"] or 0
    total_score = stats["total_score"] or 0
    total_marks = stats["total_marks"] or 0

    selected_topic = "All Topics" if is_all_topics else topic

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