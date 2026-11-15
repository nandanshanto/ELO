
"""ELO System Guardian — safe, read-only system monitoring."""

from datetime import datetime
import psutil


# Alert thresholds. These values do not trigger system changes.
CPU_WARNING_PERCENT = 90
RAM_WARNING_PERCENT = 90
DISK_WARNING_PERCENT = 10
DISK_CRITICAL_FREE_GB = 5

GIB = 1024 ** 3


def _get_disk_info(drive):
    """Return disk usage details, or None when the drive is unavailable."""
    try:
        usage = psutil.disk_usage(drive)
        free_gb = usage.free / GIB
        free_percent = 100 - usage.percent

        return {
            "drive": drive,
            "total_gb": round(usage.total / GIB, 2),
            "free_gb": round(free_gb, 2),
            "free_percent": round(free_percent, 1),
            "used_percent": usage.percent,
        }
    except (OSError, ValueError):
        return None


def get_snapshot():
    """Collect a read-only snapshot of the current system."""
    cpu_percent = psutil.cpu_percent(interval=0)
    ram = psutil.virtual_memory()

    disks = []
    for drive in ("C:\\", "D:\\"):
        info = _get_disk_info(drive)
        if info is not None:
            disks.append(info)

    try:
        uptime_seconds = max(
            0, int(datetime.now().timestamp() - psutil.boot_time())
        )
    except (OSError, ValueError):
        uptime_seconds = None

    battery_info = None
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            battery_info = {
                "percent": round(battery.percent),
                "plugged_in": battery.power_plugged,
            }
    except (AttributeError, OSError):
        pass

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "cpu_percent": round(cpu_percent, 1),
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / GIB, 2),
        "ram_total_gb": round(ram.total / GIB, 2),
        "disks": disks,
        "uptime_seconds": uptime_seconds,
        "battery": battery_info,
    }


def get_alerts(snapshot=None):
    """Return warnings for a snapshot; never changes system state."""
    if snapshot is None:
        snapshot = get_snapshot()

    alerts = []

    cpu = snapshot["cpu_percent"]
    if cpu >= CPU_WARNING_PERCENT:
        alerts.append(
            f"CPU usage is high: {cpu}% "
            f"(warning threshold: {CPU_WARNING_PERCENT}%)."
        )

    ram = snapshot["ram_percent"]
    if ram >= RAM_WARNING_PERCENT:
        alerts.append(
            f"RAM usage is high: {ram}% "
            f"(warning threshold: {RAM_WARNING_PERCENT}%)."
        )

    for disk in snapshot["disks"]:
        if (
            disk["free_gb"] <= DISK_CRITICAL_FREE_GB
            or disk["free_percent"] <= DISK_WARNING_PERCENT
        ):
            alerts.append(
                f"{disk['drive']} drive is running low on space: "
                f"{disk['free_gb']} GB free "
                f"({disk['free_percent']}% free)."
            )

    return alerts


def format_report(snapshot=None):
    """Create a readable Guardian report."""
    if snapshot is None:
        snapshot = get_snapshot()

    lines = [
        "ELO SYSTEM GUARDIAN",
        "=" * 28,
        f"Checked at: {snapshot['timestamp']}",
        "",
        f"CPU Usage: {snapshot['cpu_percent']}%",
        f"RAM Usage: {snapshot['ram_percent']}%",
        (
            f"RAM Used: {snapshot['ram_used_gb']} GB / "
            f"{snapshot['ram_total_gb']} GB"
        ),
    ]

    uptime = snapshot["uptime_seconds"]
    if uptime is not None:
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        lines.append(
            f"System Uptime: {days}d {hours}h {minutes}m"
        )

    lines.append("")
    lines.append("DRIVE STATUS")

    if snapshot["disks"]:
        for disk in snapshot["disks"]:
            lines.append(
                f"{disk['drive']}  "
                f"Used: {disk['used_percent']}%  |  "
                f"Free: {disk['free_gb']} GB / "
                f"{disk['total_gb']} GB"
            )
    else:
        lines.append("No drive information available.")

    battery = snapshot["battery"]
    if battery is not None:
        charging = (
            "Plugged in" if battery["plugged_in"] else "On battery"
        )
        lines.extend([
            "",
            f"Battery: {battery['percent']}% ({charging})",
        ])

    alerts = get_alerts(snapshot)
    lines.extend(["", "GUARDIAN STATUS"])

    if alerts:
        lines.append(f"{len(alerts)} warning(s) detected:")
        lines.extend(f"- {alert}" for alert in alerts)
    else:
        lines.append("No threshold warnings detected.")

    lines.extend([
        "",
        "Safety: Monitoring only. No system changes were made.",
    ])

    return "\n".join(lines)


def guardian_status():
    """Return a complete system report."""
    return format_report(get_snapshot())
