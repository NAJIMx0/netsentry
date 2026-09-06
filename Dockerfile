# ---- builder ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ---- runtime ----
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=builder /build/deps /usr/lib/python3.11/site-packages
COPY main.py monitor.py ./
EXPOSE 8000
# Use the non-root user provided by the distroless image
CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]