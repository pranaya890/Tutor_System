import logging

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.documents.models import Document
from apps.recommendations.services import (get_topic_performance,get_document_topics,)
from .models import Quiz,QuizAttempt, StudentAnswer
from .services import generate_quiz, evaluate_short_answer
from apps.recommendations.models import PerformanceReset


logger = logging.getLogger(__name__)

class ReadyDocumentsView(APIView):
    """
    Return ready PDF documents belonging to the logged-in student.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = Document.objects.filter(
            owner=request.user,
            status="ready",
        ).order_by("-uploaded_at")

        data = [
            {
                "id": document.id,
                "title": document.title,
                "uploaded_at": document.uploaded_at,
            }
            for document in documents
        ]

        return Response(data)




class TopicDifficultyRecommendationView(APIView):
    """
    Recommend quiz difficulty based on completed attempts
    from a selected PDF and optionally a specific topic.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        document_id = request.query_params.get("document_id")
        topic = request.query_params.get("topic", "all").strip()

        if not document_id:
            return Response(
                {"error": "Document ID is required."},
                status=400,
            )

        try:
            document_id = int(document_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid document ID."},
                status=400,
            )

        if not topic:
            topic = "all"

        document = get_object_or_404(
            Document,
            id=document_id,
            owner=request.user,
            status="ready",
        )

        topics = get_document_topics(
            student=request.user,
            document_id=document.id,
        )

        performance = get_topic_performance(
            student=request.user,
            document_id=document.id,
            topic=topic,
        )

        performance["available_topics"] = topics

        return Response(performance)


class PerformanceResetView(APIView):
    """
    Reset adaptive performance for one topic or all topics
    within a selected PDF. Previous quiz attempts are preserved.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_id = request.data.get("document_id")
        topic = str(request.data.get("topic", "all")).strip()

        if not document_id:
            return Response(
                {"error": "Document ID is required."},
                status=400,
            )

        try:
            document_id = int(document_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid document ID."},
                status=400,
            )

        if not topic:
            topic = "all"

        document = get_object_or_404(
            Document,
            id=document_id,
            owner=request.user,
            status="ready",
        )

        if topic.casefold() == "all":
            topic = "all"
        else:
            available_topics = get_document_topics(
                student=request.user,
                document_id=document.id,
            )

            matching_topic = next(
                (
                    existing_topic
                    for existing_topic in available_topics
                    if existing_topic.casefold() == topic.casefold()
                ),
                None,
            )

            if matching_topic is None:
                return Response(
                    {"error": "Topic not found in this document."},
                    status=400,
                )

            topic = matching_topic

        reset = PerformanceReset.objects.create(
            student=request.user,
            document=document,
            topic=topic,
        )

        return Response(
            {
                "message": (
                    "Performance reset successfully. "
                    "Previous quiz attempts have been preserved."
                ),
                "document_id": document.id,
                "topic": reset.topic,
                "reset_at": reset.reset_at,
            },
            status=201,
        )





class GenerateQuizView(APIView):
    """
    Generate a quiz using content from one selected document.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_id = request.data.get("document_id")
        topic = request.data.get("topic", "")
        difficulty = request.data.get("difficulty", "medium")
        total_questions = request.data.get("total_questions", 10)

        if not document_id:
            return Response(
                {"error": "Document ID is required."},
                status=400,
            )

        if not isinstance(topic, str) or not topic.strip():
            return Response(
                {"error": "A valid topic is required."},
                status=400,
            )

        topic = topic.strip()

        try:
            total_questions = int(total_questions)
        except (TypeError, ValueError):
            return Response(
                {"error": "Total questions must be a number."},
                status=400,
            )

        document = get_object_or_404(
            Document,
            id=document_id,
            owner=request.user,
            status="ready",
        )

        try:
            quiz = generate_quiz(
                user=request.user,
                document_id=document.id,
                topic=topic,
                difficulty=difficulty,
                total_questions=total_questions,
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=400,
            )

        return Response(
            {
                "message": "Quiz generated successfully.",
                "quiz_id": quiz.id,
                "title": quiz.title,
                "topic": quiz.topic,
                "difficulty": quiz.difficulty,
                "total_questions": quiz.questions.count(),
                "document_id": document.id,
            },
            status=201,
        )


class QuizDetailView(APIView):
    """
    Retrieve quiz details and questions without revealing answers.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        quiz = get_object_or_404(
            Quiz,
            id=quiz_id,
            created_by=request.user,
            is_active=True,
        )

        questions = quiz.questions.all()

        question_data = [
            {
                "id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "options": question.options,
                "marks": question.marks,
            }
            for question in questions
        ]

        return Response(
            {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "topic": quiz.topic,
                "difficulty": quiz.difficulty,
                "total_questions": questions.count(),
                "questions": question_data,
            }
        )


class StartQuizAttemptView(APIView):
    """
    Start a new quiz attempt for the authenticated student.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(
            Quiz,
            id=quiz_id,
            created_by=request.user,
            is_active=True,
        )

        questions = list(quiz.questions.all())

        if not questions:
            return Response(
                {"error": "This quiz has no questions."},
                status=400,
            )

        total_marks = sum(
            question.marks for question in questions
        )

        attempt = QuizAttempt.objects.create(
            student=request.user,
            quiz=quiz,
            total_marks=total_marks,
        )

        question_data = [
            {
                "id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "options": question.options,
                "marks": question.marks,
            }
            for question in questions
        ]

        return Response(
            {
                "message": "Quiz attempt started.",
                "attempt_id": attempt.id,
                "quiz_id": quiz.id,
                "total_questions": len(questions),
                "total_marks": total_marks,
                "status": attempt.status,
                "questions": question_data,
            },
            status=201,
        )



class SubmitQuizAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):

        # Get the attempt belonging to the logged-in student.
        attempt = get_object_or_404(
            QuizAttempt,
            id=attempt_id,
            student=request.user
        )

        if attempt.status == "completed":
            return Response(
                {"error": "This quiz attempt has already been submitted."},
                status=400
            )

        answers = request.data.get("answers", [])

        if not isinstance(answers, list):
            return Response(
                {"error": "Answers must be provided as a list."},
                status=400
            )

        validated_answers = []
        seen_question_ids = set()

        # Validate submitted answers before evaluating them.
        for item in answers:

            if not isinstance(item, dict):
                return Response(
                    {"error": "Each answer must be an object."},
                    status=400
                )

            question_id = item.get("question_id")
            student_answer = item.get("answer")

            if question_id is None or student_answer is None:
                return Response(
                    {
                        "error": (
                            "Each answer must contain "
                            "question_id and answer."
                        )
                    },
                    status=400
                )

            try:
                question_id = int(question_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "Invalid question ID."},
                    status=400
                )

            if question_id in seen_question_ids:
                return Response(
                    {"error": "Duplicate question answers are not allowed."},
                    status=400
                )

            seen_question_ids.add(question_id)

            question = attempt.quiz.questions.filter(
                id=question_id
            ).first()

            if question is None:
                return Response(
                    {
                        "error": (
                            f"Question {question_id} does not "
                            "belong to this quiz."
                        )
                    },
                    status=400
                )

            if not isinstance(student_answer, str):
                return Response(
                    {"error": "Answer must be a string."},
                    status=400
                )

            student_answer = student_answer.strip()

            if not student_answer:
                return Response(
                    {
                        "error": (
                            f"Answer for question {question_id} "
                            "cannot be empty."
                        )
                    },
                    status=400
                )

            # Validate MCQ options.
            if question.question_type == "mcq":
                options = question.options or []

                if student_answer not in options:
                    return Response(
                        {
                            "error": (
                                f"Invalid option for question "
                                f"{question_id}."
                            )
                        },
                        status=400
                    )

            # Validate True/False answers.
            elif question.question_type == "true_false":
                if student_answer.casefold() not in [
                    "true", "false"
                ]:
                    return Response(
                        {
                            "error": (
                                f"Invalid True/False answer "
                                f"for question {question_id}."
                            )
                        },
                        status=400
                    )

            validated_answers.append(
                (question, student_answer)
            )

        # Save and evaluate submitted answers.
        with transaction.atomic():

            locked_attempt = QuizAttempt.objects.select_for_update().get(
                id=attempt_id,
                student=request.user
            )

            if locked_attempt.status == "completed":
                return Response(
                    {
                        "error": (
                            "This quiz attempt has already been submitted."
                        )
                    },
                    status=400
                )

            for question, student_answer in validated_answers:

                is_correct = None
                marks_obtained = 0
                feedback = ""

                # MCQ evaluation.
                if question.question_type == "mcq":

                    is_correct = (
                        student_answer.casefold()
                        == str(question.correct_answer).strip().casefold()
                    )

                # True/False evaluation.
                elif question.question_type == "true_false":

                    is_correct = (
                        student_answer.casefold()
                        == str(question.correct_answer).strip().casefold()
                    )

                # Gemini short-answer evaluation.
                elif question.question_type == "short_answer":

                    try:
                        evaluation = evaluate_short_answer(
                            question,
                            student_answer
                        )

                        is_correct = evaluation["is_correct"]
                        marks_obtained = evaluation["marks_obtained"]
                        feedback = evaluation["feedback"]

                    except Exception:
                        logger.exception(
                            "Gemini evaluation failed for question %s",
                            question.id
                        )

                        # Preserve the answer if Gemini is unavailable.
                        is_correct = None
                        marks_obtained = 0
                        feedback = (
                            "Your answer was saved, but AI evaluation "
                            "is temporarily unavailable."
                        )

                # Apply automatic grading for MCQ and True/False.
                if question.question_type != "short_answer":

                    if is_correct:
                        marks_obtained = question.marks
                        feedback = "Correct answer."

                    else:
                        marks_obtained = 0
                        feedback = "Incorrect answer."

                StudentAnswer.objects.update_or_create(
                    attempt=locked_attempt,
                    question=question,
                    defaults={
                        "answer": student_answer,
                        "is_correct": is_correct,
                        "marks_obtained": marks_obtained,
                        "feedback": feedback,
                    }
                )

            # Calculate score using all saved answers.
            saved_answers = StudentAnswer.objects.filter(
                attempt=locked_attempt
            )

            score = saved_answers.aggregate(
                total=Sum("marks_obtained")
            )["total"] or 0

            answered_count = saved_answers.count()

            total_questions = locked_attempt.quiz.questions.count()

            pending_evaluation = saved_answers.filter(
                is_correct__isnull=True
            ).count()

            # Update attempt details.
            locked_attempt.score = score
            locked_attempt.total_marks = locked_attempt.quiz.questions.aggregate(
                total=Sum("marks")
            )["total"] or 0

            if answered_count == total_questions:
                locked_attempt.status = "completed"
                locked_attempt.completed_at = timezone.now()

            locked_attempt.save()

        return Response(
            {
                "message": "Answers submitted successfully.",
                "attempt_id": locked_attempt.id,
                "score": float(score),
                "total_marks": float(locked_attempt.total_marks),
                "answered_questions": answered_count,
                "total_questions": total_questions,
                "pending_evaluation": pending_evaluation,
                "status": locked_attempt.status,
            },
            status=200
        )


class QuizResultView(APIView):
    """
    Return the result and answer-wise feedback for a student's quiz attempt.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):

        attempt = get_object_or_404(
            QuizAttempt.objects.select_related("quiz"),
            id=attempt_id,
            student=request.user,
        )

        questions = attempt.quiz.questions.all()

        saved_answers = {
            answer.question_id: answer
            for answer in attempt.answers.all()
        }

        results = []

        correct_count = 0
        incorrect_count = 0
        pending_count = 0

        for question in questions:

            student_answer = saved_answers.get(question.id)

            if student_answer is None:
                answer_data = None
                is_correct = None
                marks_obtained = 0
                feedback = "Not answered."
            else:
                answer_data = student_answer.answer
                is_correct = student_answer.is_correct
                marks_obtained = student_answer.marks_obtained
                feedback = student_answer.feedback

                if is_correct is True:
                    correct_count += 1

                elif is_correct is False:
                    incorrect_count += 1

                else:
                    pending_count += 1

            results.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "options": question.options,
                "submitted_answer": answer_data,
                "is_correct": is_correct,
                "marks": question.marks,
                "marks_obtained": marks_obtained,
                "feedback": feedback,
            })

        percentage = (
            (attempt.score / attempt.total_marks) * 100
            if attempt.total_marks > 0
            else 0
        )

        return Response({
            "attempt_id": attempt.id,
            "quiz_title": attempt.quiz.title,
            "topic": attempt.quiz.topic,
            "difficulty": attempt.quiz.difficulty,
            "status": attempt.status,
            "score": attempt.score,
            "total_marks": attempt.total_marks,
            "percentage": round(percentage, 2),
            "total_questions": questions.count(),
            "answered_questions": len(saved_answers),
            "correct_answers": correct_count,
            "incorrect_answers": incorrect_count,
            "pending_evaluation": pending_count,
            "results": results,
        })

