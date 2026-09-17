from pathlib import Path


LEGAL_DIR = Path(__file__).resolve().parents[3] / 'scripts' / 'legal_content'


def test_legal_files_have_no_template_disclaimer() -> None:
    for name in ('privacy_ru.txt', 'offer_ru.txt'):
        text = (LEGAL_DIR / name).read_text(encoding='utf-8')
        assert 'является шаблоном' not in text
        assert 'Перед публикацией' not in text
