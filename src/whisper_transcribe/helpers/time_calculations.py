def milliseconds_to_seconds(milliseconds: int) -> float:
    return milliseconds / 1000


def seconds_to_milliseconds(seconds: float) -> float:
    return seconds * 1000


def minutes_to_milliseconds(minutes: float) -> float:
    return seconds_to_milliseconds(minutes * 60)
