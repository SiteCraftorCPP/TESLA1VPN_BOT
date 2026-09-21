"""Admin-issued Happ subscription URLs (manual handoff, no bot claim flow)."""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.crud.subscription import (
    create_paid_subscription,
    extend_subscription,
    get_subscription_by_user_and_tariff,
    get_subscription_by_user_id,
)
from app.database.crud.subscription_event import create_subscription_event
from app.database.crud.tariff import get_tariff_by_id
from app.database.crud.user import (
    _get_or_create_default_promo_group,
    create_unique_referral_code,
    create_user,
    get_user_by_email,
    get_user_by_telegram_id,
    get_user_by_username,
)
from app.database.models import Subscription, SubscriptionEvent, Tariff, User
from app.utils.happ_crypto_link import ensure_happ_crypto_link
from app.utils.validators import sanitize_telegram_name


logger = structlog.get_logger(__name__)

ADMIN_ISSUED_EVENT = 'admin_issued'
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_TELEGRAM_USERNAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$')

MAX_ISSUE_COUNT = 50


class IssueSubscriptionError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def build_share_links(subscription: Subscription) -> tuple[str | None, str | None]:
    """Return (https subscription URL, happ://crypt* link)."""
    url = subscription.subscription_url or None
    happ = ensure_happ_crypto_link(
        url,
        short_uuid=getattr(subscription, 'remnawave_short_uuid', None),
        existing_crypto_link=getattr(subscription, 'subscription_crypto_link', None),
    )
    return url, happ


def parse_telegram_contact(value: str | None) -> tuple[int | None, str | None]:
    """Parse admin-typed telegram contact into (telegram_id, username)."""
    if not value:
        return None, None
    raw = value.strip().lstrip('@')
    if not raw:
        return None, None
    if raw.isdigit():
        telegram_id = int(raw)
        if telegram_id <= 0:
            raise IssueSubscriptionError('telegram_id must be positive')
        return telegram_id, None
    if not _TELEGRAM_USERNAME_RE.match(raw):
        raise IssueSubscriptionError('Invalid Telegram username')
    return None, raw.lower()


async def resolve_or_create_user(
    db: AsyncSession,
    *,
    email: str | None = None,
    telegram: str | None = None,
    note: str | None = None,
) -> tuple[User, bool]:
    """Find an existing user or create a placeholder / telegram user.

    Returns (user, created).
    """
    email_norm = (email or '').strip().lower() or None
    if email_norm and not _EMAIL_RE.match(email_norm):
        raise IssueSubscriptionError('Invalid email')

    telegram_id, username = parse_telegram_contact(telegram)

    if email_norm:
        existing = await get_user_by_email(db, email_norm)
        if existing:
            return existing, False

    if telegram_id is not None:
        existing = await get_user_by_telegram_id(db, telegram_id)
        if existing:
            return existing, False
        display = sanitize_telegram_name(note) if note else None
        user = await create_user(
            db,
            telegram_id=telegram_id,
            username=username,
            first_name=display or f'Issued {telegram_id}',
        )
        return user, True

    if username:
        existing = await get_user_by_username(db, username)
        if existing:
            return existing, False

    return await _create_placeholder_user(db, note=note, email=email_norm, username=username)


async def _create_placeholder_user(
    db: AsyncSession,
    *,
    note: str | None,
    email: str | None,
    username: str | None,
) -> tuple[User, bool]:
    default_group = await _get_or_create_default_promo_group(db)
    display = sanitize_telegram_name(note) if note else None
    if username and not display:
        display = username

    for _ in range(5):
        referral_code = await create_unique_referral_code(db)
        user = User(
            telegram_id=None,
            auth_type='email',
            email=email,
            email_verified=False,
            password_hash=None,
            username=None,
            first_name=display or 'Issued',
            language='ru',
            referral_code=referral_code,
            balance_kopeks=0,
            has_had_paid_subscription=False,
            promo_group_id=default_group.id,
        )
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            user.promo_group = default_group
            logger.info(
                'Created placeholder user for admin-issued subscription',
                user_id=user.id,
            )
            return user, True
        except IntegrityError:
            await db.rollback()
            if email:
                existing = await get_user_by_email(db, email)
                if existing:
                    return existing, False
            continue

    raise IssueSubscriptionError('Failed to create placeholder user', status_code=500)


async def grant_or_extend_subscription(
    db: AsyncSession,
    user: User,
    tariff: Tariff,
    days: int,
) -> tuple[Subscription, str]:
    """Create a paid sub or extend an existing one. Returns (sub, 'created'|'extended')."""
    is_multi = settings.is_multi_tariff_enabled()
    connected_squads = list(tariff.allowed_squads or [])

    existing: Subscription | None
    if is_multi:
        existing = await get_subscription_by_user_and_tariff(db, user.id, tariff.id)
    else:
        existing = await get_subscription_by_user_id(db, user.id)

    if existing:
        await extend_subscription(db, existing, days)
        await _mark_paid(db, user)
        return existing, 'extended'

    try:
        new_sub = await create_paid_subscription(
            db=db,
            user_id=user.id,
            duration_days=days,
            traffic_limit_gb=tariff.traffic_limit_gb,
            device_limit=tariff.device_limit,
            is_trial=False,
            tariff_id=tariff.id,
            connected_squads=connected_squads,
        )
    except IntegrityError:
        await db.rollback()
        existing = await get_subscription_by_user_and_tariff(db, user.id, tariff.id)
        if not existing:
            raise IssueSubscriptionError(
                'User already has an active subscription for this tariff. Extend it instead.',
                status_code=409,
            ) from None
        await extend_subscription(db, existing, days)
        await _mark_paid(db, user)
        return existing, 'extended'

    await _mark_paid(db, user)
    return new_sub, 'created'


async def _mark_paid(db: AsyncSession, user: User) -> None:
    if user.has_had_paid_subscription:
        return
    user.has_had_paid_subscription = True
    await db.commit()


async def record_issued_event(
    db: AsyncSession,
    *,
    admin_id: int,
    user_id: int,
    subscription_id: int,
    days: int,
    note: str | None,
    created_user: bool,
    action: str,
) -> None:
    try:
        await create_subscription_event(
            db,
            user_id=user_id,
            event_type=ADMIN_ISSUED_EVENT,
            subscription_id=subscription_id,
            message=note,
            extra={
                'admin_id': admin_id,
                'note': note,
                'days': days,
                'created_user': created_user,
                'action': action,
            },
        )
    except Exception:
        logger.warning(
            'Failed to record admin_issued subscription event',
            user_id=user_id,
            subscription_id=subscription_id,
            exc_info=True,
        )


async def list_issued_subscriptions(
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    filters = SubscriptionEvent.event_type == ADMIN_ISSUED_EVENT
    total = await db.scalar(select(func.count(SubscriptionEvent.id)).where(filters)) or 0

    result = await db.execute(
        select(SubscriptionEvent)
        .where(filters)
        .options(
            selectinload(SubscriptionEvent.user),
            selectinload(SubscriptionEvent.subscription).selectinload(Subscription.tariff),
        )
        .order_by(SubscriptionEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = list(result.scalars().all())

    items: list[dict[str, Any]] = []
    for event in events:
        sub = event.subscription
        url, happ = build_share_links(sub) if sub else (None, None)
        extra = event.extra or {}
        user = event.user
        tariff_name = None
        if sub is not None and getattr(sub, 'tariff', None) is not None:
            tariff_name = sub.tariff.name
        items.append(
            {
                'event_id': event.id,
                'user_id': event.user_id,
                'subscription_id': event.subscription_id,
                'note': extra.get('note') or event.message,
                'days': extra.get('days'),
                'created_user': bool(extra.get('created_user')),
                'action': extra.get('action'),
                'admin_id': extra.get('admin_id'),
                'subscription_url': url,
                'happ_link': happ,
                'expires_at': sub.end_date if sub else None,
                'status': sub.status if sub else None,
                'tariff_name': tariff_name,
                'user_label': user.full_name if user else f'User{event.user_id}',
                'issued_at': event.occurred_at,
            }
        )
    return items, int(total)


async def load_tariff_or_raise(db: AsyncSession, tariff_id: int) -> Tariff:
    tariff = await get_tariff_by_id(db, tariff_id)
    if tariff is None:
        raise IssueSubscriptionError('Tariff not found', status_code=404)
    return tariff


def validate_issue_batch(*, count: int, email: str | None, telegram: str | None) -> None:
    if count < 1 or count > MAX_ISSUE_COUNT:
        raise IssueSubscriptionError(f'count must be 1..{MAX_ISSUE_COUNT}')
    if count > 1 and (email or telegram):
        raise IssueSubscriptionError('count must be 1 when email or telegram is set')
