
from django.urls import path

from .api_views import (
    ReadyDocumentsView,
    GenerateQuizView,
    QuizDetailView,
    StartQuizAttemptView,
    SubmitQuizAttemptView,
    QuizResultView,
    TopicDifficultyRecommendationView,
    PerformanceResetView,
)

urlpatterns = [
    path(
        "documents/",
        ReadyDocumentsView.as_view(),
        name="ready-documents",
    ),

    path(
        "generate/",
        GenerateQuizView.as_view(),
        name="generate-quiz",
    ),

    path(
        "<int:quiz_id>/",
        QuizDetailView.as_view(),
        name="quiz-detail",
    ),

    path(
        "<int:quiz_id>/start/",
        StartQuizAttemptView.as_view(),
        name="start-quiz-attempt",
    ),

    path(
        "attempts/<int:attempt_id>/submit/",
        SubmitQuizAttemptView.as_view(),
        name="submit-quiz-attempt",
    ),
    path(
    "attempts/<int:attempt_id>/result/",
    QuizResultView.as_view(),
    name="quiz-result",
    ),
    path(
    "recommend-difficulty/",
    TopicDifficultyRecommendationView.as_view(),
    name="recommend-quiz-difficulty",
    ),
    path(
    "reset-performance/",
    PerformanceResetView.as_view(),
    name="reset-performance",
    ),
]
