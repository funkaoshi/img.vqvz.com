# Multi-arch without emulation: dependencies are resolved and installed on the
# build machine's native platform, using uv's --python-platform to pick the
# target architecture's wheels. The final stage only copies files, so it has
# no RUN steps that would need QEMU. (uv segfaults under BuildKit's emulator.)
#
#   docker buildx build --platform linux/amd64,linux/arm64 -t funkaoshi/img-vqvz:latest --push .

ARG PYTHON_IMAGE=python:3.12-slim

# Pinned to the build platform: a plain COPY --from=<image> would fetch the
# target architecture's uv binary, which can't run in the native build stage.
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:0.9.8 AS uv

FROM --platform=$BUILDPLATFORM ${PYTHON_IMAGE} AS build
ARG TARGETARCH

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN case "$TARGETARCH" in \
      amd64) echo x86_64-unknown-linux-gnu ;; \
      arm64) echo aarch64-unknown-linux-gnu ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac > /tmp/platform \
 && uv sync --frozen --extra prod --no-dev --no-install-project \
      --python-platform "$(cat /tmp/platform)"

COPY README.md wsgi.py sets.yml ./
COPY vqvz ./vqvz
RUN uv sync --frozen --extra prod --no-dev --python-platform "$(cat /tmp/platform)"


FROM ${PYTHON_IMAGE}

WORKDIR /app
COPY --from=build /app /app

# Non-root. HOME must be writable: gunicorn puts its control socket there.
USER 65532:65532
ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp \
    PYTHONUNBUFFERED=1 \
    VQVZ_SITE=img

EXPOSE 8003

# Settings (FLICKR_API_KEY at minimum) come from the environment at run time.
# The same image serves gv.vqvz.com with -e VQVZ_SITE=gv.
CMD ["gunicorn", "-b", "0.0.0.0:8003", "-w", "1", "--threads", "4", "wsgi:app"]
