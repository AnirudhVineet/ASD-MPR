from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"


def test_templates_are_utf8():
    for path in TEMPLATES.rglob("*.html"):
        path.read_text(encoding="utf-8")
