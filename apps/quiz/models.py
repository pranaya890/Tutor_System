
from django.conf import settings
from django.db import models
from apps.documents.models import Document



class Quiz(models.Model):

    

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]


    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="quizzes"
        )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    topic = models.CharField(max_length=255)
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default="medium"
    )

    total_questions = models.PositiveIntegerField(default=10)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quizzes"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Question(models.Model):

    QUESTION_TYPES = [
        ("mcq", "Multiple Choice"),
        ("true_false", "True / False"),
        ("short_answer", "Short Answer"),
    ]

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default="mcq"
    )

    # Example: ["Option A", "Option B", "Option C", "Option D"]
    options = models.JSONField(default=list, blank=True)

    # Stores the correct answer or answers.
    correct_answer = models.JSONField()

    explanation = models.TextField(blank=True)

    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.question_text[:80]


class QuizAttempt(models.Model):

    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts"
    )

    score = models.FloatField(default=0)
    total_marks = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_progress"
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.quiz}"


class StudentAnswer(models.Model):

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="student_answers"
    )

    # JSON supports MCQ, multiple selections and text answers.
    answer = models.JSONField()

    is_correct = models.BooleanField(null=True, blank=True)
    marks_obtained = models.FloatField(default=0)
    feedback = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_question_per_attempt"
            )
        ]

    def __str__(self):
        return f"{self.attempt} - {self.question_id}"
