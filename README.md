# GenAI-Powered Personalized Tutor System

An AI-powered adaptive learning platform that uses Retrieval-Augmented Generation (RAG) and generative AI to provide personalized learning experiences, document-based question answering, automated quiz generation, and performance-based study recommendations.

## 1. Project Overview

The GenAI-Powered Personalized Tutor System is designed to help students learn from their own study materials through an interactive AI tutor.

Students can upload PDF documents, ask questions about their study materials, generate quizzes, evaluate their learning performance, and receive personalized recommendations based on their quiz results.

The system uses Retrieval-Augmented Generation (RAG) to retrieve relevant information from uploaded documents before generating AI-powered responses.

## 2. Key Features

### User Management
- Student registration and login.
- Email-based authentication.
- Student profile management.

### Document Management
- Upload PDF study materials.
- Extract and process document content.
- Split documents into smaller chunks.
- Generate embeddings for document chunks.
- Store and retrieve document information using ChromaDB.

### AI-Powered Tutor
- Interactive AI tutor chat.
- Ask questions about uploaded study materials.
- Retrieve relevant document context using RAG.
- Generate contextual answers using generative AI.

### AI Quiz Generation
- Generate quizzes from uploaded learning materials.
- Support different quiz difficulty levels.
- Evaluate quiz submissions.
- Display quiz results and learning history.

### Adaptive Learning
- Recommend quiz difficulty based on previous performance.
- Analyze student performance topic by topic.
- Calculate attempts, total scores, and percentages.
- Identify strong, developing, and weak topics.
- Allow students to reset their learning performance.

### Personalized Recommendations
- Generate recommendations based on quiz performance.
- Identify topics requiring additional practice.
- Suggest topics for revision.
- Provide personalized learning suggestions.

### Student Dashboard
- Display overall learning performance.
- Show completed quiz attempts and scores.
- Display topic-wise performance.
- Identify strong and weak learning areas.
- Show adaptive difficulty and personalized recommendations.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web application framework |
| Django REST Framework | API development |
| Google Gemini API | Generative AI integration |
| ChromaDB | Vector database |
| PyMuPDF | PDF text extraction |
| Python-dotenv | Environment variable management |
| SQLite | Relational database |
| HTML, CSS, JavaScript | Frontend development |

## 4. RAG Architecture

The system uses Retrieval-Augmented Generation to answer questions based on uploaded study documents.

The general workflow is:

1. Student uploads a PDF document.
2. The system extracts text from the PDF.
3. Extracted text is divided into smaller chunks.
4. Embeddings are generated for the document chunks.
5. Document embeddings are stored in ChromaDB.
6. Student submits a question through the AI tutor.
7. Relevant document chunks are retrieved using vector similarity search.
8. Retrieved context is used to generate a contextual AI response.

## 5. Adaptive Learning Workflow

The adaptive learning system analyzes completed quiz attempts to understand student performance.

- Performance is calculated for individual topics.
- Topics are categorized according to their performance.
- Quiz difficulty is recommended based on previous scores.
- Personalized recommendations identify areas requiring improvement.
- Students can reset performance records to begin tracking their progress again.

The difficulty recommendation currently follows these thresholds:

| Performance | Recommended Difficulty |
|---|---|
| Below 50% | Easy |
| 50% to below 70% | Medium |
| 70% or above | Hard |

When no previous performance data is available, medium difficulty is recommended.

## 6. Project Structure

```text
Tutor_System/
│
├── apps/
│   ├── accounts/
│   ├── tutor/
│   ├── documents/
│   ├── quiz/
│   ├── recommendations/
│   └── analytics/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
│   ├── accounts/
│   ├── documents/
│   └── tutor/
│
├── static/
├── media/
├── vector_store/
├── manage.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 7. Installation and Setup

### Prerequisites

- Python 3.14 or a compatible Python version.
- pip.
- Git.
- Google Gemini API key.

### Step 1: Clone the Repository

```bash
git clone https://github.com/pranaya890/Tutor_System.git
cd Tutor_System
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment.

**Linux/macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory.

```env
SECRET_KEY=your_django_secret_key
DEBUG=True

GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=
DEEPSEEK_API_KEY=
```

Add the API keys required by the AI providers configured in your application.

Never commit your `.env` file or expose API keys publicly.

### Step 5: Apply Database Migrations

```bash
python manage.py migrate
```

### Step 6: Create a Superuser

```bash
python manage.py createsuperuser
```

### Step 7: Run the Development Server

```bash
python manage.py runserver
```

Open the application in your browser:

```text
http://127.0.0.1:8000/
```

## 8. Environment Configuration

The application uses environment variables for configuration.

| Variable | Description |
|---|---|
| SECRET_KEY | Django secret key |
| DEBUG | Enables or disables Django debug mode |
| GEMINI_API_KEY | Google Gemini API key |
| GROQ_API_KEY | Groq API key |
| DEEPSEEK_API_KEY | DeepSeek API key |

## 9. Database and Vector Storage

The project uses SQLite for relational data, including student accounts, documents, quizzes, attempts, and performance records.

ChromaDB is used for storing and retrieving document embeddings for the RAG functionality.

Uploaded documents are stored in the media directory.

## 10. Testing

Run the Django test suite using:

```bash
python manage.py test
```

Check the Django project configuration:

```bash
python manage.py check
```

## 11. Future Enhancements

Potential improvements include:

- More advanced adaptive learning algorithms.
- Additional AI model integrations.
- Improved learning analytics and visualizations.
- Support for additional document formats.
- More detailed learning progress tracking.

## 12. Author

**Project:** GenAI-Powered Personalized Tutor System

**Repository:** https://github.com/pranaya890/Tutor_System
