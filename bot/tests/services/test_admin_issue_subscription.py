from types import SimpleNamespace

import pytest

from app.services.admin_issue_subscription import (
    IssueSubscriptionError,
    MAX_ISSUE_COUNT,
    build_share_links,
    parse_telegram_contact,
    validate_issue_batch,
)


def test_build_share_links_prefers_existing_crypto():
    sub = SimpleNamespace(
        subscription_url='https://projecthub.su/api/sub/AbCdEf',
        remnawave_short_uuid='AbCdEf',
        subscription_crypto_link='happ://crypt4/existing',
    )
    url, happ = build_share_links(sub)
    assert url == 'https://projecthub.su/api/sub/AbCdEf'
    assert happ == 'happ://crypt4/existing'


def test_build_share_links_generates_crypto_when_missing():
    sub = SimpleNamespace(
        subscription_url='https://projecthub.su/api/sub/AbCdEfGh',
        remnawave_short_uuid='AbCdEfGh',
        subscription_crypto_link=None,
    )
    url, happ = build_share_links(sub)
    assert url == 'https://projecthub.su/api/sub/AbCdEfGh'
    assert happ is not None
    assert happ.startswith('happ://crypt')


def test_parse_telegram_contact_id_and_username():
    assert parse_telegram_contact('123456789') == (123456789, None)
    assert parse_telegram_contact('@Test_User') == (None, 'test_user')
    assert parse_telegram_contact(None) == (None, None)
    assert parse_telegram_contact('  ') == (None, None)


def test_parse_telegram_contact_rejects_bad_username():
    with pytest.raises(IssueSubscriptionError):
        parse_telegram_contact('ab')
    with pytest.raises(IssueSubscriptionError):
        parse_telegram_contact('0')


def test_validate_issue_batch_contact_requires_count_one():
    validate_issue_batch(count=3, email=None, telegram=None)
    with pytest.raises(IssueSubscriptionError, match='count must be 1'):
        validate_issue_batch(count=2, email='a@b.c', telegram=None)
    with pytest.raises(IssueSubscriptionError, match=f'1..{MAX_ISSUE_COUNT}'):
        validate_issue_batch(count=0, email=None, telegram=None)
