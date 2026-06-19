import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import Base, engine
from .routers import auth, documents, pages


settings = get_settings()
logger = logging.getLogger('uvicorn.error')

app = FastAPI(title=settings.app_name, debug=settings.debug)
static_dir = Path(__file__).resolve().parents[1] / 'static'

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)


@app.get('/health')
def health_check():
    return {'status': 'ok'}


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    body_preview = '<unavailable>'
    try:
        body = await request.body()
        body_preview = body.decode('utf-8', errors='ignore')
    except RuntimeError as stream_error:
        body_preview = f'<unavailable: {stream_error}>'

    logger.error(
        '422 validation error on %s: errors=%s body=%s',
        request.url.path,
        exc.errors(),
        body_preview,
    )
    return JSONResponse(status_code=422, content={'detail': exc.errors()})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception('Unhandled error on %s', request.url.path)
    detail = str(exc) if settings.debug else 'Internal server error.'
    return JSONResponse(status_code=500, content={'detail': detail})


app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')
app.include_router(pages.router)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
