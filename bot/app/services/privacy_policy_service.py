import html
import re
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.crud.privacy_policy import (
    get_privacy_policy,
    set_privacy_policy_enabled,
    upsert_privacy_policy,
)
from app.database.models import PrivacyPolicy


logger = structlog.get_logger(__name__)


class PrivacyPolicyService:
    """Utility helpers around privacy policy storage and presentation."""

    MAX_PAGE_LENGTH = 3500

    @staticmethod
    def _normalize_language(language: str) -> str:
        base_language = language or settings.DEFAULT_LANGUAGE or 'ru'
        return base_language.split('-')[0].lower()

    @staticmethod
    def normalize_language(language: str) -> str:
        return PrivacyPolicyService._normalize_language(language)

    @classmethod
    async def get_policy(
        cls,
        db: AsyncSession,
        language: str,
        *,
        fallback: bool = False,
    ) -> PrivacyPolicy | None:
        lang = cls._normalize_language(language)
        policy = await get_privacy_policy(db, lang)

        if policy or not fallback:
            return policy

        default_lang = cls._normalize_language(settings.DEFAULT_LANGUAGE)
        if lang != default_lang:
            return await get_privacy_policy(db, default_lang)

        return policy

    @classmethod
    async def get_active_policy(
        cls,
        db: AsyncSession,
        language: str,
    ) -> PrivacyPolicy | None:
        lang = cls._normalize_language(language)
        policy = await get_privacy_policy(db, lang)

        if policy and policy.is_enabled and policy.content.strip():
            return policy

        default_lang = cls._normalize_language(settings.DEFAULT_LANGUAGE)
        if lang != default_lang:
            fallback_policy = await get_privacy_policy(db, default_lang)
            if fallback_policy and fallback_policy.is_enabled and fallback_policy.content.strip():
                return fallback_policy

        return None

    @classmethod
    async def is_policy_enabled(cls, db: AsyncSession, language: str) -> bool:
        policy = await cls.get_active_policy(db, language)
        return policy is not None

    @classmethod
    async def save_policy(
        cls,
        db: AsyncSession,
        language: str,
        content: str,
    ) -> PrivacyPolicy:
        lang = cls._normalize_language(language)
        enable_if_new = True
        policy = await upsert_privacy_policy(
            db,
            lang,
            content,
            enable_if_new=enable_if_new,
        )
        logger.info('✅ Политика конфиденциальности обновлена для языка', lang=lang)
        return policy

    @classmethod
    async def set_enabled(
        cls,
        db: AsyncSession,
        language: str,
        enabled: bool,
    ) -> PrivacyPolicy:
        lang = cls._normalize_language(language)
        return await set_privacy_policy_enabled(db, lang, enabled)

    @classmethod
    async def toggle_enabled(
        cls,
        db: AsyncSession,
        language: str,
    ) -> PrivacyPolicy:
        lang = cls._normalize_language(language)
        policy = await get_privacy_policy(db, lang)

        if policy:
            new_status = not policy.is_enabled
        else:
            new_status = True

        return await set_privacy_policy_enabled(db, lang, new_status)

    @staticmethod
    def split_content_into_pages(
        content: str,
        *,
        max_length: int = None,
    ) -> list[str]:
        if not content:
            return []

        normalized = content.replace('\r\n', '\n').strip()
        if not normalized:
            return []

        max_len = max_length or PrivacyPolicyService.MAX_PAGE_LENGTH

        if len(normalized) <= max_len:
            return [normalized]

        paragraphs = [paragraph.strip() for paragraph in normalized.split('\n\n') if paragraph.strip()]

        pages: list[str] = []
        current = ''

        def flush_current() -> None:
            nonlocal current
            if current:
                pages.append(current.strip())
                current = ''

        for paragraph in paragraphs:
            candidate = f'{current}\n\n{paragraph}'.strip() if current else paragraph
            if len(candidate) <= max_len:
                current = candidate
                continue

            flush_current()

            if len(paragraph) <= max_len:
                current = paragraph
                continue

            start_index = 0
            while start_index < len(paragraph):
                chunk = paragraph[start_index : start_index + max_len]
                pages.append(chunk.strip())
                start_index += max_len

            current = ''

        flush_current()

        if not pages:
            return [normalized[:max_len]]

        return pages

    @classmethod
    def _strip_html_for_telegram(cls, content: str) -> str:
        """Info-page HTML or legacy markup → plain text safe for Telegram HTML mode."""
        if not content:
            return ''
        text = re.sub(r'<\s*br\s*/?\s*>', '\n', content, flags=re.IGNORECASE)
        text = re.sub(r'</\s*p\s*>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*li\s*>', '• ', text, flags=re.IGNORECASE)
        text = re.sub(r'</\s*li\s*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()

    @classmethod
    def prepare_registration_telegram_text(cls, content: str, *, language: str = 'ru') -> str:
        """Fit privacy policy into a single Telegram message (4096 char limit)."""
        plain = cls._strip_html_for_telegram(content)
        if not plain:
            return ''

        cabinet_base = (settings.CABINET_URL or '').strip().rstrip('/')
        if cabinet_base and cabinet_base != settings._CABINET_URL_DEFAULT:
            full_link = f'{cabinet_base}/info?tab=privacy'
            footer_ru = f'\n\n📄 <a href="{full_link}">Полный текст в личном кабинете</a>'
            footer_en = f'\n\n📄 <a href="{full_link}">Full text in the cabinet</a>'
        else:
            footer_ru = '\n\n📄 Полный текст доступен в личном кабинете сервиса.'
            footer_en = '\n\n📄 Full text is available in the service cabinet.'
        footer = footer_en if language.startswith('en') else footer_ru

        truncated_note_ru = '\n\n<i>Показана начальная часть документа.</i>'
        truncated_note_en = '\n\n<i>Showing the beginning of the document.</i>'
        truncated_note = truncated_note_en if language.startswith('en') else truncated_note_ru

        # Reserve space for footer + accept/decline keyboard context (~200 chars buffer).
        max_body = 4096 - len(footer) - len(truncated_note) - 40
        pages = cls.split_content_into_pages(plain, max_length=max(500, max_body))
        body = pages[0]
        if len(pages) > 1:
            body += truncated_note
        return body + footer
