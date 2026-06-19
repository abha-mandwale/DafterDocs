# DafterDocs Backend

Converted version of the original DafterDocs project:

- `FastAPI` for APIs and page serving
- `Jinja2` for HTML templates
- `htmx` for upload submission and live polling
- `Tailwind CSS` via CDN for styling
- `PostgreSQL` as the default database

## What stays the same

These API endpoints are preserved:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/documents/process`
- `GET /api/documents/{jobId}`
- `GET /api/documents/{documentId}/export?format=pdf|docx|txt`

## New UI routes

- `GET /`
- `GET /workspace`
- `POST /ui/process`
- `GET /ui/jobs/{jobId}`

## Quick start

```bash
cd dafterdocs/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
createdb dafterdocs
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Notes

- The browser stores the JWT in `localStorage` and attaches it to API and htmx requests.
- Tailwind and htmx are loaded from CDN to keep the conversion lightweight.
- OCR, translation, summary, conclusion, and export logic are ported from the original FastAPI backend.
