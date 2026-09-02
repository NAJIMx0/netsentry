from __future__ import annotations

import os
from typing import Any

import psutil

ALLOWED_LISTEN_PORTS: set[int] = {
    int(p) for p in os.getenv("NETSENTRY_ALLOWED_PORTS", "8000,8080,443,22").split(",") if p.strip()
}
HIGH_CONN_THRESHOLD: int = int(os.getenv("NETSENTRY_HIGH_CONN_THRESHOLD", "200"))


def get_system_stats() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total_bytes": vm.total,
            "available_bytes": vm.available,
            "used_bytes": vm.used,
            "percent": vm.percent,
        },
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent": disk.percent,
        },
    }


def get_network_stats() -> dict[str, Any]:
    connections = psutil.net_connections(kind="inet")
    active = [c for c in connections if c.status == "ESTABLISHED"]
    listening = [c for c in connections if c.status == "LISTEN"]

    io = psutil.net_io_counters(pernic=True)
    interfaces: dict[str, dict[str, int]] = {}
    for name, counters in io.items():
        interfaces[name] = {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
            "errin": counters.errin,
            "errout": counters.errout,
        }

    open_ports = [
        {"port": c.laddr.port, "pid": c.pid}
        for c in listening
        if c.laddr
    ]

    return {
        "active_connections": len(active),
        "listening_ports": open_ports,
        "interfaces": interfaces,
    }


def get_alerts() -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    conns = psutil.net_connections(kind="inet")
    per_pid: dict[int, int] = {}
    for c in conns:
        if c.pid:
            per_pid[c.pid] = per_pid.get(c.pid, 0) + 1

    for pid, count in per_pid.items():
        if count >= HIGH_CONN_THRESHOLD:
            try:
                proc = psutil.Process(pid)
                name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name = "unknown"
            alerts.append({
                "type": "high_connection_count",
                "severity": "warning",
                "detail": f"Process {name} (pid={pid}) has {count} connections",
                "pid": pid,
                "count": count,
            })

    listening = [c for c in conns if c.status == "LISTEN" and c.laddr]
    unexpected = [
        c for c in listening
        if c.laddr.port not in ALLOWED_LISTEN_PORTS
    ]
    for c in unexpected:
        alerts.append({
            "type": "unexpected_listen_port",
            "severity": "info",
            "detail": f"Port {c.laddr.port} is listening but not in allowlist",
            "port": c.laddr.port,
            "pid": c.pid,
        })

    return alerts
