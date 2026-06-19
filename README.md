# DafterDocs

DafterDocs is a FastAPI-based document processing app for uploading files, extracting text, translating content, generating summaries, and exporting results. This repository is a web conversion of the earlier mobile-focused project, with a server-rendered UI built on Jinja2 and htmx while keeping the backend API flow intact.

## Features

- Email/password authentication with JWT-based sessions
- Browser workspace for uploading and processing documents
- OCR support for PDF and image files
- Translation, summary generation, and conclusion drafting
- Live job progress updates in the UI
- Export processed output as PDF, DOCX, or TXT
- PostgreSQL-backed persistence for users and document jobs

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Jinja2
- htmx
- Tailwind CSS via CDN
- Tesseract OCR
- OpenAI API with local fallback behavior when no API key is configured

## Supported Files

- PDF
- DOCX
- PNG
- JPG / JPEG
- TXT

## Project Structure

```text
dafterdocs/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── config.py
│   │   └── main.py
│   ├── static/
│   ├── templates/
│   ├── storage/
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## Main Routes

### UI Routes

- `GET /` - login and registration page
- `GET /workspace` - document workspace
- `POST /ui/process` - submit a document from the web UI
- `GET /ui/jobs/{jobId}` - fetch job status partial for live updates

### API Routes

- `GET /health` - health check
- `POST /api/auth/register` - create a user account
- `POST /api/auth/login` - authenticate and receive a JWT
- `POST /api/documents/process` - upload and start processing a document
- `GET /api/documents/{jobId}` - fetch processing status and result
- `GET /api/documents/{documentId}/export?format=pdf|docx|txt` - export output

## Processing Pipeline

Each uploaded document moves through these stages:

1. Uploading
2. OCR extraction
3. Translation
4. Summary generation
5. Conclusion drafting
6. Export-ready completion

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Tesseract OCR installed and available in `PATH`
- Tesseract language data for the languages you want to process

### Run Locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
createdb dafterdocs
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Environment Configuration

Important settings from `backend/.env.example`:

- `DATABASE_URL` - default PostgreSQL connection string
- `JWT_SECRET_KEY` - JWT signing secret
- `OPENAI_API_KEY` - optional; enables model-backed translation and summarization
- `OPENAI_MODEL` - defaults to `gpt-4o-mini`
- `TESSERACT_CMD` - optional explicit path to the Tesseract binary
- `PDF_FONT_PATH` - optional Unicode font path for better Hindi PDF export support

## Notes

- If `OPENAI_API_KEY` is not set, the app still runs and falls back to basic local translation/summary behavior.
- JWT session data is stored in the browser and attached to API and htmx requests from the frontend.
- Uploaded files and generated exports are stored under `backend/storage/`.

## Backend Details

More backend-specific notes are available in [backend/README.md](backend/README.md).
