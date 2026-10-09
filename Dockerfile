# ---------- Stage 1: "builder" — installs the packages ----------
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: "final" — the actual image we ship ----------
FROM python:3.12-slim

WORKDIR /app

# Copy ONLY the installed packages from the builder stage, nothing else
COPY --from=builder /install /usr/local

COPY . .

# Create a normal (non-root) user and give it ownership of /app
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
