import json
import logging
import re
from typing import Any

from ..config import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency in constrained runtime
    OpenAI = None


settings = get_settings()
logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self) -> None:
        self._client = None
        if settings.openai_api_key and OpenAI is not None:
            try:
                self._client = OpenAI(api_key=settings.openai_api_key)
            except Exception as exc:
                # Keep pipeline available with fallback behavior if SDK/env mismatch occurs.
                logger.exception('OpenAI client initialization failed. Falling back to local mode: %s', exc)
                self._client = None

    def translate_text(self, text: str, source_language: str, target_language: str) -> str:
        if not text.strip():
            return ''

        if source_language == target_language and source_language != 'auto':
            return text

        if not self._client:
            return f'[Translated to {target_language}]\n{text}'

        prompt = (
            'Translate the following document text into the target language. '
            'Preserve meaning and important entities. Return only translated text.\n\n'
            f'Source language: {source_language}\n'
            f'Target language: {target_language}\n\n'
            f'Text:\n{text}'
        )
        #print(prompt)

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {'role': 'system', 'content': 'You are a precise multilingual translator.'},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content or text
        except Exception:
            return f'[Translated to {target_language}]\n{text}'

    def summarize_and_conclude(self, text: str, target_language: str) -> tuple[list[str], str]:
        if not text.strip():
            return ['No extractable text found.'], 'Unable to generate a conclusion due to empty content.'

        if not self._client:
            return self._fallback_summary(text, target_language)

        prompt = (
            'Create a concise output for the following text in the target language. '
            'Return strict JSON object with keys: summary (array of 3 to 5 bullet strings), '
            'conclusion (single short paragraph).\n\n'
            f'Target language: {target_language}\n\n'
            f'Text:\n{text}'
        )

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                response_format={'type': 'json_object'},
                messages=[
                    {
                        'role': 'system',
                        'content': 'You summarize documents and provide concise actionable conclusions.',
                    },
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or '{}'
            payload: dict[str, Any] = json.loads(content)
            summary = payload.get('summary') or []
            conclusion = payload.get('conclusion') or ''

            cleaned_summary = [str(item).strip() for item in summary if str(item).strip()]
            cleaned_conclusion = str(conclusion).strip()

            if not cleaned_summary or not cleaned_conclusion:
                return self._fallback_summary(text, target_language)

            return cleaned_summary[:5], cleaned_conclusion
        except Exception:
            return self._fallback_summary(text, target_language)

    @staticmethod
    def _fallback_summary(text: str, target_language: str) -> tuple[list[str], str]:
        normalized = re.sub(r'\s+', ' ', text).strip()
        if not normalized:
            return ['No extractable text found.'], 'Unable to generate a conclusion due to empty content.'

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', normalized) if s.strip()]
        if not sentences:
            sentences = [normalized]

        summary = sentences[:3]
        conclusion = (
            f'This document has been processed for {target_language}. '
            'Review summary points for operational decisions and compliance actions.'
        )
        return summary, conclusion
