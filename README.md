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

