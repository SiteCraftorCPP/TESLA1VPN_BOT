from app.utils.happ_crypto_link import create_happ_crypto_link, create_happ_crypto_link_best


def test_create_happ_crypt4_link():
    link = create_happ_crypto_link('https://projecthub.su/api/sub/TEST123', 'v4', as_link=True)
    assert link is not None
    assert link.startswith('happ://crypt4/')


def test_create_happ_crypto_link_best():
    link = create_happ_crypto_link_best('https://projecthub.su/api/sub/AbCdEfGh')
    assert link is not None
    assert link.startswith('happ://crypt')
