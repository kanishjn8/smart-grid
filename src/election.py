from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node


def numeric_id(node_id: str) -> int:
    return int(node_id.removeprefix("N"))


def _higher_candidates(node: "Node", all_node_ids: list[str]) -> list[str]:
    return [
        candidate
        for candidate in all_node_ids
        if numeric_id(candidate) > numeric_id(node.node_id) and candidate != node.node_id
    ]


def start_election(node: "Node", all_node_ids: list[str], trigger: str) -> None:
    if not node.can_participate_in_election():
        return

    with node.state_lock:
        if node.election_in_progress:
            return
        node.election_in_progress = True
        node.received_higher_alive = False
        node.election_deadline = node.engine.current_tick + 2

    targets = _higher_candidates(node, all_node_ids)
    for candidate in targets:
        node.send_message(candidate, "ELECTION", {"trigger": trigger})

    target_label = ", ".join(targets) if targets else "no higher nodes"
    node.engine.log_event(
        "election",
        f"[Tick {node.engine.current_tick:02d}] {node.node_id} started election ({trigger}) -> {target_label}",
    )


def handle_election_msg(node: "Node", msg: dict[str, object], all_node_ids: list[str]) -> None:
    if not node.can_participate_in_election():
        return

    sender = str(msg["sender"])
    node.send_message(sender, "ALIVE", {"candidate": node.node_id})
    start_election(node, all_node_ids, f"forwarded from {sender}")


def handle_alive(node: "Node", _msg: dict[str, object]) -> None:
    with node.state_lock:
        node.received_higher_alive = True


def declare_coordinator(node: "Node") -> None:
    node.engine.set_leader(node.node_id)
    with node.state_lock:
        node.election_in_progress = False
        node.received_higher_alive = False
        node.election_deadline = None
        node.state.is_leader = True

    node.broadcast_message("COORDINATOR", {"leader": node.node_id})
    node.engine.log_event(
        "election",
        f"[Tick {node.engine.current_tick:02d}] {node.node_id} became COORDINATOR",
    )


def maybe_finalize_election(node: "Node", current_tick: int) -> None:
    with node.state_lock:
        if not node.election_in_progress or node.election_deadline is None:
            return
        if current_tick < node.election_deadline:
            return
        received_higher_alive = node.received_higher_alive
        node.election_in_progress = False
        node.election_deadline = None

    if received_higher_alive:
        return
    declare_coordinator(node)


def handle_coordinator(node: "Node", msg: dict[str, object]) -> None:
    leader = str(dict(msg.get("payload", {})).get("leader", msg["sender"]))
    node.engine.set_leader(leader)
    with node.state_lock:
        node.state.is_leader = node.node_id == leader
        node.election_in_progress = False
        node.received_higher_alive = False
        node.election_deadline = None


def handle_coordinator_done(node: "Node", _msg: dict[str, object]) -> None:
    node.engine.clear_leader()
    with node.state_lock:
        node.state.is_leader = False
        node.election_in_progress = False
        node.received_higher_alive = False
        node.election_deadline = None
