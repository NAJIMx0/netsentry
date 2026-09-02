# netsentry

A headless network/security monitoring tool built with FastAPI and psutil. Provides system metrics, network stats, and basic security alerts over HTTP — designed to run in containers without root or elevated privileges.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn netsentry.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/system` | CPU, memory, disk usage snapshot |
| GET /network | Active connections, per-interface I/O, listening ports |
| GET | `/alerts` | Rule-based security findings |

## Configuration

Set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `NETSENTRY_ALLOWED_PORTS` | `8000,8080,443,22` | Comma-separated list of expected listening ports |
| `NETSENTRY_HIGH_CONN_THRESHOLD` | `200` | Connection count per process to trigger an alert |

## Project Structure

```
netsentry/
├── __init__.py
├── main.py          # FastAPI app and endpoints
├── monitor.py       # psutil logic for system/network/alerts
tests/
└── test_endpoints.py
requirements.txt
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- No root / no special capabilities required
