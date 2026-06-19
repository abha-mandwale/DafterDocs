import base64
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..dependencies import get_current_user
from ..db import get_db
from ..models import DocumentJob, User
from ..schemas import ExportResponse, ProcessDocumentResponse, ProcessingStatusResponse
from ..services.exporters import build_docx_bytes, build_pdf_bytes, build_txt_bytes
from ..services.pipeline import job_to_result, run_document_pipeline


router = APIRouter(prefix='/documents', tags=['documents'])
settings = get_settings()

ALLOWED_SUFFIXES = {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.txt'}


def save_upload(file: UploadFile) -> tuple[str, str]:
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Unsupported file type. Allowed: PDF, DOCX, PNG, JPG, TXT.',
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = file.filename or f'document{suffix}'
    stored_name = f'{uuid4()}-{file_name}'
    destination = settings.upload_dir / stored_name

    content = file.file.read()
    destination.write_bytes(content)

    return file_name, str(destination)


@router.post('/process', response_model=ProcessDocumentResponse)
def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: Optional[str] = Form(None),
    target_language: Optional[str] = Form(None),
    sourceLanguage: Optional[str] = Form(None),
    targetLanguage: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_source_language = (source_language or sourceLanguage or '').strip()
    resolved_target_language = (target_language or targetLanguage or '').strip()

    if not resolved_source_language or not resolved_target_language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Missing language fields. Send source_language and target_language.',
        )

    file_name, file_path = save_upload(file)

    job = DocumentJob(
        user_id=current_user.id,
        file_name=file_name,
        file_path=file_path,
        source_language=resolved_source_language,
        target_language=resolved_target_language,
        status='uploading',
        progress=5,
        message='Queued for processing.',
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_document_pipeline, job.id)

    return ProcessDocumentResponse(jobId=job.id, status='uploading')


@router.get('/{job_id}', response_model=ProcessingStatusResponse)
def get_processing_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(DocumentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found.')

    result = job_to_result(job) if job.status == 'completed' else None
    debug_error = job.error if settings.debug and job.status == 'failed' else None

    return ProcessingStatusResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=debug_error,
        result=result,
    )


@router.get('/{document_id}/export', response_model=ExportResponse)
def export_document(
    document_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    export_format = format.lower()
    if export_format not in {'pdf', 'docx', 'txt'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid export format.')

    job = db.get(DocumentJob, document_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found.')

    if job.status != 'completed':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Document processing is not completed yet.',
        )

    result = job_to_result(job)

    if export_format == 'pdf':
        output_bytes = build_pdf_bytes(result)
    elif export_format == 'docx':
        output_bytes = build_docx_bytes(result)
    else:
        output_bytes = build_txt_bytes(result)

    file_name = f'{document_id}-output.{export_format}'
    base64_payload = base64.b64encode(output_bytes).decode('utf-8')

    return ExportResponse(base64=base64_payload, fileName=file_name)
