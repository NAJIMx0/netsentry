# ---- builder ----
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ---- runtime ----
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=builder /build/deps /app/deps
COPY main.py monitor.py ./
ENV PYTHONPATH=/app/deps
EXPOSE 8000
CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]