from django.db.models import Count, Sum

from apps.quiz.models import QuizAttempt


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
