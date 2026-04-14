def on_send(clock: int) -> int:
    return clock + 1


def on_receive(clock: int, msg_ts: int) -> int:
    return max(clock, msg_ts) + 1
