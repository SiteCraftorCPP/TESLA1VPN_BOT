#!/usr/bin/env python3
"""One-shot: normalize subscriptions.connected_squads JSON and backfill happ crypto links."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database.database import AsyncSessionLocal
from app.database.models import Subscription, SubscriptionStatus
from app.utils.happ_crypto_link import ensure_happ_crypto_link
from app.utils.subscription_utils import extract_squad_uuids, normalize_remnawave_subscription_url


async def main() -> None:
    fixed_squads = 0
    fixed_url = 0
    fixed_crypto = 0
    subs: list[Subscription] = []
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE.value)
        )
        subs = list(result.scalars().all())
        for sub in subs:
            raw = sub.connected_squads
            normalized = extract_squad_uuids(raw)
            if raw != normalized:
                sub.connected_squads = normalized
                fixed_squads += 1

            if sub.subscription_url:
                new_url = normalize_remnawave_subscription_url(
                    sub.subscription_url,
                    sub.remnawave_short_uuid,
                )
                if new_url and new_url != sub.subscription_url:
                    sub.subscription_url = new_url
                    fixed_url += 1

            if sub.subscription_url and not sub.subscription_crypto_link:
                crypto = ensure_happ_crypto_link(
                    sub.subscription_url,
                    short_uuid=sub.remnawave_short_uuid,
                )
                if crypto:
                    sub.subscription_crypto_link = crypto
                    fixed_crypto += 1

        await db.commit()

    print(
        f'normalize_done squads={fixed_squads} urls={fixed_url} crypto={fixed_crypto} active={len(subs)}'
    )


if __name__ == '__main__':
    asyncio.run(main())
