from datetime import datetime


def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}" if u != "B" else f"{int(f)} {u}"
        f /= 1024
    return f"{n} B"


def human_age(then: datetime, now: datetime) -> str:
    delta = now - then
    days = delta.days
    if days >= 1:
        return f"{days}g fa"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h fa"
    mins = (delta.seconds % 3600) // 60
    return f"{mins}m fa"
