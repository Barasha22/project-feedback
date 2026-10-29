# Project Feedback

A Django application for collecting weekly Start/Stop/Continue feedback and
running the retrospectives that follow.

## Local setup

Copy `.env.example` values into your shell, then install and run the project:

```shell
uv sync
uv run manage.py migrate
uv run manage.py runserver
```

Run the quality checks with:

```shell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Docker development environment

Build and start PostgreSQL, the Django web service, and the placeholder worker:

```shell
docker compose up --build
```

The application is available at <http://localhost:8000>. PostgreSQL data is
stored in the named `postgres_data` volume. The web and worker containers share
the named `scratch` volume at `/scratch` for the later media pipeline.

Run the test and quality checks in the built image:

```shell
docker compose run --rm web uv run pytest
docker compose run --rm web uv run ruff check .
docker compose run --rm web uv run ruff format --check .
```

Confirm the pinned runtime versions with:

```shell
docker compose run --rm web python --version
docker compose run --rm web ffmpeg -version
```

Stop the environment with `docker compose down`. Add `--volumes` only when you
intend to delete the development database and shared scratch data.

