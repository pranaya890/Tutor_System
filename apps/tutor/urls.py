from django.urls import path
from .views import (
    DashboardView,
    TutorChatView,
    NewSessionView,
    ClearSessionView,
    QuizzesView,
    QuizTakeView,
    QuizHistoryView,
    QuizResultPageView,
    PerformanceAnalysisView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('chat/', TutorChatView.as_view(), name='tutor_chat'),
    path('chat/<int:session_id>/', TutorChatView.as_view(), name='tutor_chat_session'),
    path('chat/new/', NewSessionView.as_view(), name='new_session'),
    path('chat/<int:session_id>/clear/', ClearSessionView.as_view(), name='clear_session'),
    path('quizzes/', QuizzesView.as_view(), name='quizzes'),
    path(
    'quizzes/<int:quiz_id>/take/',
    QuizTakeView.as_view(),
    name='take_quiz',
),

path(
    'quizzes/attempts/<int:attempt_id>/result/',
    QuizResultPageView.as_view(),
    name='quiz_result_page',
),
path(
    'quizzes/history/',
    QuizHistoryView.as_view(),
    name='quiz_history',
),
path(
    'quizzes/analysis/',
    PerformanceAnalysisView.as_view(),
    name='performance_analysis',
),

]
