import json
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..models import DocumentJob
from ..schemas import DocumentResult
from .llm import LLMService
from .ocr import OCRService


settings = get_settings()
logger = logging.getLogger(__name__)


def update_job(
    db: Session,
    job: DocumentJob,
    *,
    status: str,
    progress: int,
    message: str,
    error: Optional[str] = None,
) -> None:
    job.status = status
    job.progress = progress
    job.message = message
    if error:
        job.error = error
    db.add(job)
    db.commit()
    db.refresh(job)


def run_document_pipeline(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(DocumentJob, job_id)
        if not job:
            return

        llm_service = LLMService()

        update_job(
            db,
            job,
            status='uploading',
            progress=14,
            message='Uploading document securely...',
        )
        time.sleep(settings.processing_step_delay_seconds)

        update_job(
            db,
            job,
            status='ocr',
            progress=36,
            message='Running OCR for printed and handwritten text...',
        )
        original_text = OCRService.extract_text(
            job.file_path,
            source_language=job.source_language,
        )
        job.original_text = original_text
        db.add(job)
        db.commit()
        db.refresh(job)
        time.sleep(settings.processing_step_delay_seconds)

        update_job(
            db,
            job,
            status='translating',
            progress=62,
            message='Detecting language and translating text...',
        )
         
        translated_text = llm_service.translate_text(
            original_text,
            source_language=job.source_language,
            target_language=job.target_language,
        )
        job.translated_text = translated_text
        db.add(job)
        db.commit()
        db.refresh(job)
        time.sleep(settings.processing_step_delay_seconds)

        update_job(
            db,
            job,
            status='summarizing',
            progress=83,
            message='Generating summary bullets...',
        )
        summary, conclusion = llm_service.summarize_and_conclude(
            translated_text,
            target_language=job.target_language,
        )
        job.summary_json = json.dumps(summary)
        db.add(job)
        db.commit()
        db.refresh(job)
        time.sleep(settings.processing_step_delay_seconds)

        update_job(
            db,
            job,
            status='concluding',
            progress=94,
            message='Drafting final conclusion...',
        )
        job.conclusion = conclusion
        db.add(job)
        db.commit()
        db.refresh(job)
        time.sleep(settings.processing_step_delay_seconds)

        update_job(
            db,
            job,
            status='completed',
            progress=100,
            message='Processing completed.',
        )
    except Exception as exc:
        logger.exception('Document pipeline failed for job_id=%s', job_id)
        job = db.get(DocumentJob, job_id)
        if job:
            failure_message = (
                f'Pipeline execution failed: {exc}'
                if settings.debug
                else 'Pipeline execution failed.'
            )
            update_job(
                db,
                job,
                status='failed',
                progress=100,
                message=failure_message,
                error=str(exc),
            )
    finally:
        db.close()


def job_to_result(job: DocumentJob) -> DocumentResult:
    summary = []
    if job.summary_json:
        try:
            parsed = json.loads(job.summary_json)
            if isinstance(parsed, list):
                summary = [str(item) for item in parsed]
        except Exception:
            summary = []

    return DocumentResult(
        id=job.id,
        sourceLanguage=job.source_language,
        targetLanguage=job.target_language,
        originalText=job.original_text or '',
        translatedText=job.translated_text or '',
        summary=summary,
        conclusion=job.conclusion or '',
        status=job.status,  # type: ignore[arg-type]
        createdAt=job.created_at,
    )
