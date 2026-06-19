from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import DocumentJob, User
from ..routers.documents import save_upload
from ..services.pipeline import job_to_result, run_document_pipeline


router = APIRouter(tags=['pages'])
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / 'templates'))
asset_version = int((Path(__file__).resolve().parents[2] / 'static' / 'js' / 'app.js').stat().st_mtime)

LANGUAGE_OPTIONS = [
    {'code': 'auto', 'label': 'Auto Detect'},
    {'code': 'en', 'label': 'English'},
    {'code': 'hi', 'label': 'Hindi'},
    {'code': 'ar', 'label': 'Arabic'},
    {'code': 'bn', 'label': 'Bengali'},
    {'code': 'ta', 'label': 'Tamil'},
    {'code': 'te', 'label': 'Telugu'},
    {'code': 'mr', 'label': 'Marathi'},
    {'code': 'gu', 'label': 'Gujarati'},
    {'code': 'ur', 'label': 'Urdu'},
    {'code': 'fr', 'label': 'French'},
    {'code': 'de', 'label': 'German'},
    {'code': 'es', 'label': 'Spanish'},
    {'code': 'pt', 'label': 'Portuguese'},
    {'code': 'zh', 'label': 'Chinese'},
    {'code': 'ja', 'label': 'Japanese'},
    {'code': 'ko', 'label': 'Korean'},
]

STAGE_ORDER = ['uploading', 'ocr', 'translating', 'summarizing', 'concluding']
STAGE_LABELS = {
    'uploading': 'Upload accepted',
    'ocr': 'OCR extraction',
    'translating': 'Translation',
    'summarizing': 'Summary generation',
    'concluding': 'Conclusion drafting',
    'completed': 'Completed',
    'failed': 'Failed',
}


def build_job_context(job: DocumentJob, request: Request) -> dict:
    result = job_to_result(job) if job.status == 'completed' else None
    current_stage_index = STAGE_ORDER.index(job.status) if job.status in STAGE_ORDER else len(STAGE_ORDER)
    return {
        'request': request,
        'job': job,
        'result': result,
        'stage_order': STAGE_ORDER,
        'stage_labels': STAGE_LABELS,
        'current_stage_index': current_stage_index,
    }


@router.get('/', response_class=HTMLResponse)
def auth_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='auth.html',
        context={'app_name': settings.app_name, 'page_name': 'auth', 'asset_version': asset_version},
    )


@router.get('/workspace', response_class=HTMLResponse)
def workspace_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='workspace.html',
        context={
            'app_name': settings.app_name,
            'page_name': 'workspace',
            'language_options': LANGUAGE_OPTIONS,
            'asset_version': asset_version,
        },
    )


@router.post('/ui/process', response_class=HTMLResponse)
def process_document_form(
    request: Request,
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
    return templates.TemplateResponse(
        request=request,
        name='partials/job_status.html',
        context=build_job_context(job, request),
    )


@router.get('/ui/jobs/{job_id}', response_class=HTMLResponse)
def document_job_partial(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(DocumentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found.')

    return templates.TemplateResponse(
        request=request,
        name='partials/job_status.html',
        context=build_job_context(job, request),
    )
