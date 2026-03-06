FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fontconfig \
    fonts-noto-cjk \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/output \
    && chown -R appuser:appuser /app /ms-playwright

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "run_daily.py"]
