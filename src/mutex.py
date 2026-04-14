from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node


def _priority_tuple(lamport_ts: int, node_id: str) -> tuple[int, str]:
    return lamport_ts, node_id


def request_cs(node: "Node", live_node_ids: list[str], reason: str) -> None:
    with node.state_lock:
        if node.state.requesting_mutex or node.state.in_critical_section or not node.state.alive:
            return
        node.state.requesting_mutex = True
        node.request_reason = reason
        node.request_ts = node.bump_clock_locked()
        node.mutex_waiting_for = set(live_node_ids)

    for peer_id in live_node_ids:
        node.send_message(
            peer_id,
            "REQUEST",
            {"request_ts": node.request_ts, "reason": reason},
        )
    node.engine.log_event(
        "mutex",
        f"[Tick {node.engine.current_tick:02d}] {node.node_id} requested MUTEX for {reason}",
    )


def handle_request(node: "Node", msg: dict[str, object]) -> None:
    sender = str(msg["sender"])
    payload = dict(msg.get("payload", {}))
    incoming_ts = int(payload.get("request_ts", msg["lamport_ts"]))

    should_defer = False
    with node.state_lock:
        own_requesting = node.state.requesting_mutex or node.state.in_critical_section
        own_priority = _priority_tuple(node.request_ts or node.state.lamport_clock, node.node_id)
        incoming_priority = _priority_tuple(incoming_ts, sender)
        if own_requesting and own_priority < incoming_priority:
            should_defer = True
            if sender not in node.state.deferred_replies:
                node.state.deferred_replies.append(sender)

    if should_defer:
        return

    node.send_message(sender, "REPLY", {"request_ts": incoming_ts})


def release_cs(node: "Node") -> None:
    deferred: list[str]
    with node.state_lock:
        deferred = list(node.state.deferred_replies)
        node.state.deferred_replies.clear()
        node.state.requesting_mutex = False
        node.state.in_critical_section = False
        node.mutex_waiting_for.clear()
        reason = node.request_reason
        node.request_reason = ""
        node.request_ts = None
        node.critical_section_until = None

    for peer_id in deferred:
        node.send_message(peer_id, "REPLY", {"deferred": True})

    node.engine.log_event(
        "mutex",
        f"[Tick {node.engine.current_tick:02d}] {node.node_id} released MUTEX after {reason}",
    )
