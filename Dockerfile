# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14
ARG FFMPEG_VERSION=8.1.3

FROM python:${PYTHON_VERSION}-slim AS ffmpeg-builder

ARG FFMPEG_VERSION

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        libopus-dev \
        nasm \
        pkg-config \
        xz-utils \
        yasm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/ffmpeg

RUN curl --fail --location --show-error \
        "https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz" \
        --output ffmpeg.tar.xz \
    && tar --extract --file ffmpeg.tar.xz --strip-components=1 \
    && ./configure \
        --prefix=/opt/ffmpeg \
        --disable-debug \
        --disable-doc \
        --disable-ffplay \
        --disable-shared \
        --enable-libopus \
        --enable-static \
    && make --jobs="$(nproc)" \
    && make install

FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PATH="/opt/venv/bin:/opt/ffmpeg/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libopus0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir --parents /app /scratch \
    && chown --recursive app:app /app /scratch

COPY --from=ffmpeg-builder /opt/ffmpeg /opt/ffmpeg
COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY --chown=app:app pyproject.toml README.md ./
RUN uv sync --no-install-project

COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

