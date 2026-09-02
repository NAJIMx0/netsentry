from fastapi import FastAPI

from monitor import get_alerts, get_network_stats, get_system_stats

app = FastAPI(title="netsentry", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/system")
def system() -> dict:
    return get_system_stats()


@app.get("/network")
def network() -> dict:
    return get_network_stats()


@app.get("/alerts")
def alerts() -> dict:
    return {"alerts": get_alerts()}
