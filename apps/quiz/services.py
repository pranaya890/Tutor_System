
import json
import re

from django.db import transaction
from django.conf import settings
from google import genai

from apps.documents.models import Document
from apps.documents.vector_store import search_document_chunks

from .models import Quiz, Question


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


def parse_quiz_response(response_text):
    """
    Convert Gemini's JSON response into Python data.
    """

    response_text = response_text.strip()

    # Remove Markdown code fences if Gemini includes them.
    response_text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response_text,
        flags=re.IGNORECASE,
    )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Gemini returned an invalid JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("Invalid quiz response format.")

    questions = data.get("questions")

    if not isinstance(questions, list):
        raise ValueError("The response does not contain a question list.")

    return data


def validate_questions(questions, expected_count):
    """
    Validate generated questions before saving them.
    """

    if len(questions) != expected_count:
        raise ValueError(
            f"Expected {expected_count} questions, "
            f"but Gemini generated {len(questions)}."
        )

    valid_types = {"mcq", "true_false", "short_answer"}

    for index, question in enumerate(questions, start=1):

        if not isinstance(question, dict):
            raise ValueError(f"Question {index} is invalid.")

        question_text = question.get("question_text")
        question_type = question.get("question_type")
        options = question.get("options", [])
        correct_answer = question.get("correct_answer")
        explanation = question.get("explanation", "")

        if not isinstance(question_text, str) or not question_text.strip():
            raise ValueError(f"Question {index} has no question text.")

        if question_type not in valid_types:
            raise ValueError(f"Question {index} has an invalid type.")

        if not isinstance(options, list):
            raise ValueError(f"Question {index} has invalid options.")

        if question_type == "mcq":
            if len(options) < 2:
                raise ValueError(f"Question {index} needs at least two options.")

            if not isinstance(correct_answer, str):
                raise ValueError(f"Question {index} has an invalid answer.")

            if correct_answer not in options:
                raise ValueError(
                    f"Question {index}'s correct answer is not one of its options."
                )

        elif question_type == "true_false":
            if correct_answer not in ["True", "False"]:
                raise ValueError(
                    f"Question {index} must have True or False as its answer."
                )

            question["options"] = ["True", "False"]

        elif question_type == "short_answer":
            if not isinstance(correct_answer, str) or not correct_answer.strip():
                raise ValueError(
                    f"Question {index} needs a valid short answer."
                )

            question["options"] = []

        if not isinstance(explanation, str):
            raise ValueError(f"Question {index} has an invalid explanation.")




def evaluate_short_answer(question, student_answer):
    """
    Evaluate a student's short answer using Gemini.

    Returns:
        {
            "is_correct": bool,
            "marks_obtained": float,
            "feedback": str
        }
    """

    prompt = f"""
You are a fair and careful educational quiz evaluator.

Evaluate the student's answer using the expected answer
and explanation provided below.

QUESTION:
{question.question_text}

EXPECTED ANSWER:
{question.correct_answer}

EXPLANATION:
{question.explanation}

STUDENT ANSWER:
{student_answer}

MAXIMUM MARKS:
{question.marks}

Evaluation rules:
1. Evaluate meaning and conceptual understanding, not exact wording.
2. Accept equivalent terminology and valid alternative explanations.
3. Award partial marks when the answer demonstrates partial understanding.
4. Award zero marks for irrelevant, empty, or "I don't know" answers.
5. Do not award marks for unsupported or incorrect claims.
6. Do not penalize grammar or spelling unless meaning is unclear.
7. Give concise, constructive feedback.
8. Do not invent facts beyond the expected answer and explanation.

Return valid JSON only:

{{
    "is_correct": true,
    "marks_obtained": 1,
    "feedback": "A concise explanation of the evaluation."
}}

The is_correct field should be true only when the answer
demonstrates sufficient understanding to receive full marks.
For partial marks, use false.
"""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
    )

    response_text = interaction.output_text

    if not response_text:
        raise ValueError("Gemini returned an empty evaluation.")

    data = parse_quiz_response(
        response_text.replace(
            '"questions"',
            '"questions"',
        )
    ) if False else None

    response_text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response_text.strip(),
        flags=re.IGNORECASE,
    )

    try:
        evaluation = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Gemini returned invalid evaluation JSON."
        ) from exc

    is_correct = evaluation.get("is_correct")
    marks_obtained = evaluation.get("marks_obtained")
    feedback = evaluation.get("feedback")

    if not isinstance(is_correct, bool):
        raise ValueError("Invalid correctness value from Gemini.")

    if isinstance(marks_obtained, bool) or not isinstance(
        marks_obtained, (int, float)
    ):
        raise ValueError("Invalid marks returned by Gemini.")

    if not isinstance(feedback, str) or not feedback.strip():
        raise ValueError("Invalid feedback returned by Gemini.")

    marks_obtained = float(marks_obtained)

    if not 0 <= marks_obtained <= question.marks:
        raise ValueError("Gemini returned marks outside the allowed range.")

    if is_correct and marks_obtained != question.marks:
        raise ValueError("Inconsistent full-mark evaluation.")

    return {
        "is_correct": is_correct,
        "marks_obtained": marks_obtained,
        "feedback": feedback.strip(),
    }



def generate_quiz(
    user,
    document_id,
    topic,
    difficulty="medium",
    total_questions=10,
):
    """
    Generate a quiz using content from one selected PDF.

    Only documents owned by the logged-in user and marked ready
    are allowed.
    """

    # 1. Validate input.
    if not topic or not topic.strip():
        raise ValueError("Please provide a quiz topic.")

    if difficulty not in ["easy", "medium", "hard"]:
        raise ValueError("Invalid quiz difficulty.")

    if not 1 <= total_questions <= 20:
        raise ValueError("Question count must be between 1 and 20.")

    # 2. Verify document ownership and processing status.
    try:
        document = Document.objects.get(
            id=document_id,
            owner=user,
            status="ready",
        )
    except Document.DoesNotExist:
        raise ValueError(
            "Selected document does not exist, is not ready, "
            "or does not belong to you."
        )

    # 3. Retrieve chunks ONLY from the selected PDF.
    results = search_document_chunks(
        query=topic,
        owner_id=user.id,
        document_id=document.id,
        n_results=min(max(total_questions, 5), 15),
    )

    chunks = results.get("documents", [[]])[0]

    if not chunks:
        raise ValueError(
            "No relevant content was found for this topic in the selected PDF."
        )

    context = "\n\n---\n\n".join(chunks)

    # 4. Prepare Gemini prompt.
    prompt = f"""
You are an educational assessment question generator.

Generate exactly {total_questions} questions using ONLY
the provided document context.

Quiz topic: {topic}
Difficulty: {difficulty}

Requirements:
- Questions must be based on the provided context.
- Do not invent facts or use outside knowledge.
- Questions must be clear and educationally useful.
- Include a mixture of question types:
  mcq, true_false, and short_answer.
- MCQ questions must have four options.
- The correct answer for MCQ must exactly match one option.
- True/False answers must be either "True" or "False".
- Short-answer questions must have a clear expected answer.
- Include a short explanation for every question.
- Return valid JSON only. Do not include Markdown.

Required JSON structure:

{{
    "title": "Quiz title",
    "description": "Short quiz description",
    "questions": [
        {{
            "question_text": "Question here",
            "question_type": "mcq",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "correct_answer": "Option A",
            "explanation": "Explanation here"
        }}
    ]
}}

For true_false questions, use:
"options": ["True", "False"]

For short_answer questions, use:
"options": []

Document context:
{context}
"""

    # 5. Generate questions using Gemini.
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
    )

    response_text = interaction.output_text

    if not response_text:
        raise ValueError("Gemini returned an empty response.")

    # 6. Parse and validate Gemini response.
    data = parse_quiz_response(response_text)

    questions_data = data["questions"]

    validate_questions(
        questions_data,
        total_questions,
    )

    # 7. Save quiz and questions together.
    with transaction.atomic():

        quiz = Quiz.objects.create(
            document=document,
            title=data.get("title", f"{topic} Quiz"),
            description=data.get("description", ""),
            topic=topic,
            difficulty=difficulty,
            total_questions=total_questions,
            created_by=user,
        )

        question_objects = []

        for question in questions_data:
            question_objects.append(
                Question(
                    quiz=quiz,
                    question_text=question["question_text"],
                    question_type=question["question_type"],
                    options=question.get("options", []),
                    correct_answer=question["correct_answer"],
                    explanation=question.get("explanation", ""),
                    marks=1,
                )
            )

        Question.objects.bulk_create(question_objects)

    return quiz
