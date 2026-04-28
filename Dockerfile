FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.5.14
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --no-dev --frozen

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 1000 app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ARG COMMIT_SHA=unknown
ENV FILES_TO_AGENT_COMMIT_SHA=${COMMIT_SHA}
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz', timeout=2)" || exit 1
CMD ["python", "-m", "files_to_agent"]
