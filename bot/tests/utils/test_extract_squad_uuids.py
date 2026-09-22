from app.utils.subscription_utils import extract_squad_uuids


def test_extract_squad_uuids_from_dict_objects() -> None:
    squads = [
        {'uuid': '11111111-1111-1111-1111-111111111111', 'name': 'DE'},
        {'uuid': '22222222-2222-2222-2222-222222222222'},
    ]
    assert extract_squad_uuids(squads) == [
        '11111111-1111-1111-1111-111111111111',
        '22222222-2222-2222-2222-222222222222',
    ]


def test_extract_squad_uuids_safe_for_set() -> None:
    squads = [{'uuid': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'}]
    assert set(extract_squad_uuids(squads)) == {'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'}
