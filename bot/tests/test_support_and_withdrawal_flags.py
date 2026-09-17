def test_support_contact_url_points_to_user_chat(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, 'SUPPORT_USERNAME', '@i_saidru')
    assert settings.get_support_contact_url() == 'https://t.me/i_saidru'
    assert settings.get_support_contact_display() == '@i_saidru'


def test_referral_withdrawal_off_hides_feature(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, 'REFERRAL_WITHDRAWAL_ENABLED', False)
    monkeypatch.setattr(settings, 'REFERRAL_PROGRAM_ENABLED', True)
    assert settings.is_referral_withdrawal_enabled() is False
