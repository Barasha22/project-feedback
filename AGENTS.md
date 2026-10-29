Django app for weekly Start/Stop/Continue cycles and the retrospectives that
follow. 

Documents

- `_docs/process.md` - how work is organized

Commands

- `uv sync` - install dependencies
- `uv run manage.py runserver` - dev server
- `uv run manage.py migrate` - apply migrations
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file
- `uv run ruff check . && uv run ruff format --check .` - lint and format check,
  run it before committing

Rules

- Postgres is the only infrastructure. 
- Configuration comes from the environment. A new setting means a new env var
  plus an entry in `.env.example`, never a hardcoded value or a checked-in secret.
- Tests live in `tests/`, named after what they cover. `config/settings_test.py`
  supplies the test environment — production settings stay strict.
- Dependencies are pinned exactly in `pyproject.toml`. Do not add a dependency without asking.
- Commit regularly.