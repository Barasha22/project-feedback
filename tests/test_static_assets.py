from django.core.management import call_command
from django.test import override_settings


def test_collectstatic_includes_compiled_assets(tmp_path):
    static_root = tmp_path / "collected-static"

    with override_settings(STATIC_ROOT=static_root):
        call_command("collectstatic", interactive=False, verbosity=0)

    assert (static_root / "css" / "app.css").is_file()
    assert (static_root / "js" / "vendor" / "htmx.min.js").is_file()
    assert (static_root / "js" / "vendor" / "alpine.min.js").is_file()
