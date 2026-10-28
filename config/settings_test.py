import os

os.environ.setdefault("DATABASE_URL", "postgresql://unused/unused")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ALLOWED_HOSTS", "testserver")

from .settings import *  # noqa: E402,F403

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

