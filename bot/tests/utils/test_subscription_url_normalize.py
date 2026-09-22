from app.utils.subscription_utils import (
    connected_squad_id_set,
    extract_squad_uuids,
    normalize_panel_subscription_url,
    normalize_remnawave_subscription_url,
)


def test_page_url_converted_to_api():
    assert (
        normalize_remnawave_subscription_url(
            'https://projecthub.su/U5_4cT_BCNWgcHtJ',
            'U5_4cT_BCNWgcHtJ',
        )
        == 'https://projecthub.su/api/sub/U5_4cT_BCNWgcHtJ'
    )


def test_api_url_unchanged():
    url = 'https://projecthub.su/api/sub/U5_4cT_BCNWgcHtJ'
    assert normalize_remnawave_subscription_url(url) == url


def test_derives_short_uuid_from_path():
    assert (
        normalize_remnawave_subscription_url('https://projecthub.su/zRRzhLe4hG6EJU4K')
        == 'https://projecthub.su/api/sub/zRRzhLe4hG6EJU4K'
    )


def test_panel_payload_normalization():
    panel = {
        'shortUuid': 'U5_4cT_BCNWgcHtJ',
        'subscriptionUrl': 'https://projecthub.su/U5_4cT_BCNWgcHtJ',
    }
    assert (
        normalize_panel_subscription_url(panel)
        == 'https://projecthub.su/api/sub/U5_4cT_BCNWgcHtJ'
    )


def test_empty_and_none_passthrough():
    assert normalize_remnawave_subscription_url(None) is None
    assert normalize_remnawave_subscription_url('') == ''


def test_extract_squad_uuids_from_dict_items():
    squads = [{'uuid': 'a'}, {'uuid': 'b'}, 'c']
    assert extract_squad_uuids(squads) == ['a', 'b', 'c']
    assert connected_squad_id_set(squads) == {'a', 'b', 'c'}
