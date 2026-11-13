from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.db.models import Sum, Count
from django.utils.decorators import method_decorator
from apps.quiz.models import Quiz, QuizAttempt,StudentAnswer
from apps.recommendations.services import generate_personalized_recommendations
from .models import TutorSession, ChatMessage
from apps.documents.models import Document
from apps.documents.rag import generate_rag_answer


@method_decorator(login_required, name="dispatch")
class DashboardView(View):
    def get(self, request):

        total_docs = Document.objects.filter(
            owner=request.user
        ).count()

        chat_sessions = TutorSession.objects.filter(
            user=request.user
        ).count()

        total_quizzes = Quiz.objects.filter(
            created_by=request.user
        ).count()

        recommendations = generate_personalized_recommendations(
            request.user
        )

        context = {
            "total_docs": total_docs,
            "total_quizzes": total_quizzes,
            "chat_sessions": chat_sessions,
            "recommendations": recommendations,
        }

        return render(
            request,
            "tutor/dashboard.html",
            context
        )


@method_decorator(login_required, name="dispatch")
class TutorChatView(View):

    def get(self, request, session_id=None):

        all_sessions = TutorSession.objects.filter(
            user=request.user
        )

        if session_id:
            active_session = get_object_or_404(
                TutorSession,
                id=session_id,
                user=request.user
            )
        else:
            active_session = all_sessions.first()

            if not active_session:
                active_session = TutorSession.objects.create(
                    user=request.user,
                    title="First Study Session"
                )

        # Remove old error messages from the chat
        active_session.messages.filter(
            content__icontains="⚠️"
        ).delete()

        active_session.messages.filter(
            content__icontains="Error communicating"
        ).delete()

        messages = active_session.messages.all()

        return render(
            request,
            "tutor/chat.html",
            {
                "active_session": active_session,
                "chat_messages": messages,
                "past_sessions": all_sessions,
            }
        )

    def post(self, request, session_id=None):

        # ---------------------------------------------------------
        # 1. Get user question
        # ---------------------------------------------------------

        user_message = request.POST.get(
            "message",
            ""
        ).strip()

        if not user_message:
            return JsonResponse(
                {
                    "error": "Message cannot be empty"
                },
                status=400
            )

        # ---------------------------------------------------------
        # 2. Get / create chat session
        # ---------------------------------------------------------

        if session_id:

            session = get_object_or_404(
                TutorSession,
                id=session_id,
                user=request.user
            )

        else:

            session = TutorSession.objects.filter(
                user=request.user
            ).first()

            if not session:
                session = TutorSession.objects.create(
                    user=request.user,
                    title="New Study Session"
                )

        # ---------------------------------------------------------
        # 3. Save user's message
        # ---------------------------------------------------------

        ChatMessage.objects.create(
            session=session,
            role="user",
            content=user_message
        )

        # ---------------------------------------------------------
        # 4. Rename new/default session
        # ---------------------------------------------------------

        default_titles = [
            "New Study Session",
            "First Study Session",
            "New Chat",
        ]

        if session.title in default_titles:

            summary_title = (
                user_message[:25].capitalize()
                + ("..." if len(user_message) > 25 else "")
            )

            session.title = summary_title
            session.save(
                update_fields=["title"]
            )

        # ---------------------------------------------------------
        # 5. Generate RAG answer
        # ---------------------------------------------------------

        try:

            result = generate_rag_answer(
                question=user_message,
                owner_id=request.user.id,
                n_results=5,
            )

            ai_reply = result["answer"]
            sources = result["sources"]

        except Exception as e:

            print(
                f"[RAG ERROR] {type(e).__name__}: {e}"
            )

            return JsonResponse(
                {
                    "error": "The tutor could not generate a response.",
                    "reply": (
                        "⚠️ **Tutor Error**: "
                        "Something went wrong while generating the answer."
                    ),
                    "session_title": session.title,
                    "session_id": session.id,
                    "sources": [],
                },
                status=500
            )

        # ---------------------------------------------------------
        # 6. Save AI response
        # ---------------------------------------------------------

        if ai_reply:

            ChatMessage.objects.create(
                session=session,
                role="model",
                content=ai_reply
            )

        # ---------------------------------------------------------
        # 7. Return response to frontend
        # ---------------------------------------------------------

        return JsonResponse(
            {
                "reply": ai_reply,
                "sources": sources,
                "session_title": session.title,
                "session_id": session.id,
            }
        )


@method_decorator(login_required, name="dispatch")
class NewSessionView(View):

    def get(self, request):

        new_session = TutorSession.objects.create(
            user=request.user,
            title="New Chat"
        )

        return redirect(
            "tutor_chat_session",
            session_id=new_session.id
        )


@method_decorator(login_required, name="dispatch")
class ClearSessionView(View):

    def post(self, request, session_id):

        session = get_object_or_404(
            TutorSession,
            id=session_id,
            user=request.user
        )

        session.messages.all().delete()

        session.title = "New Chat"

        session.save(
            update_fields=["title"]
        )

        return JsonResponse(
            {
                "success": True
            }
        )



@method_decorator(login_required, name="dispatch")
class QuizzesView(View):

    def get(self, request):

        # Only show ready documents belonging to this student.
        ready_documents = Document.objects.filter(
            owner=request.user,
            status="ready",
        ).order_by("-uploaded_at")

        # Only show quizzes created by this student.
        quizzes = Quiz.objects.filter(
            created_by=request.user,
            is_active=True,
        ).select_related(
            "document"
        ).prefetch_related(
            "questions"
        ).order_by("-created_at")

        context = {
            "ready_documents": ready_documents,
            "quizzes": quizzes,
            "total_quizzes": quizzes.count(),
        }

        return render(
            request,
            "tutor/quizzes.html",
            context,
        )

@method_decorator(login_required, name="dispatch")
class QuizTakeView(View):

    def get(self, request, quiz_id):
        quiz = get_object_or_404(
            Quiz,
            id=quiz_id,
            created_by=request.user,
            is_active=True,
        )

        return render(
            request,
            "tutor/quiz_take.html",
            {"quiz": quiz},
        )


@method_decorator(login_required, name="dispatch")
class QuizResultPageView(View):

    def get(self, request, attempt_id):
        attempt = get_object_or_404(
            QuizAttempt.objects.select_related("quiz"),
            id=attempt_id,
            student=request.user,
        )

        return render(
            request,
            "tutor/quiz_result.html",
            {"attempt": attempt},
        )


@method_decorator(login_required, name="dispatch")
class QuizHistoryView(View):

    def get(self, request):

        # Fetch only this student's quiz attempts.
        attempts = QuizAttempt.objects.filter(
            student=request.user
        ).select_related(
            "quiz",
            "quiz__document"
        ).order_by("-started_at")

        # Separate completed and unfinished attempts.
        completed_attempts = attempts.filter(
            status="completed"
        )

        in_progress_attempts = attempts.filter(
            status="in_progress"
        )

        # Calculate completed quiz statistics.
        total_completed = completed_attempts.count()

        total_attempts = attempts.count()

        total_score = sum(
            attempt.score or 0
            for attempt in completed_attempts
        )

        total_marks = sum(
            attempt.total_marks or 0
            for attempt in completed_attempts
        )

        average_percentage = (
            (total_score / total_marks) * 100
            if total_marks > 0
            else 0
        )

        context = {
            "attempts": attempts,
            "completed_attempts": completed_attempts,
            "in_progress_attempts": in_progress_attempts,
            "total_attempts": total_attempts,
            "total_completed": total_completed,
            "total_in_progress": in_progress_attempts.count(),
            "average_percentage": round(average_percentage, 2),
        }

        return render(
            request,
            "tutor/quiz_history.html",
            context
        )



@method_decorator(login_required, name="dispatch")
class PerformanceAnalysisView(View):

    def get(self, request):

        # Only analyze completed attempts belonging to this student.
        completed_attempts = QuizAttempt.objects.filter(
            student=request.user,
            status="completed",
        )

        # Group attempts by quiz topic.
        topic_stats = completed_attempts.values(
            "quiz__topic"
        ).annotate(
            attempt_count=Count("id"),
            total_score=Sum("score"),
            total_marks=Sum("total_marks"),
        ).order_by("quiz__topic")

        # Calculate topic percentages and performance categories.
        topics = []

        for item in topic_stats:

            score = item["total_score"] or 0
            marks = item["total_marks"] or 0

            percentage = (
                (score / marks) * 100
                if marks > 0
                else 0
            )

            if percentage >= 70:
                category = "Strong"
            elif percentage < 50:
                category = "Needs Practice"
            else:
                category = "Developing"

            topics.append({
                "topic": item["quiz__topic"],
                "attempt_count": item["attempt_count"],
                "total_score": score,
                "total_marks": marks,
                "percentage": round(percentage, 2),
                "category": category,
            })

        # Overall performance.
        total_score = completed_attempts.aggregate(
            total=Sum("score")
        )["total"] or 0

        total_marks = completed_attempts.aggregate(
            total=Sum("total_marks")
        )["total"] or 0

        overall_percentage = (
            (total_score / total_marks) * 100
            if total_marks > 0
            else 0
        )

        context = {
            "topics": topics,
            "total_completed": completed_attempts.count(),
            "total_topics": len(topics),
            "overall_percentage": round(overall_percentage, 2),
            "total_score": total_score,
            "total_marks": total_marks,
        }

        return render(
            request,
            "tutor/performance_analysis.html",
            context,
        )