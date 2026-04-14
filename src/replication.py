from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node


def replicate_to_backup(node: "Node", backup_id: str = "N8") -> None:
    if node.node_id == backup_id:
        return
    node.send_message(
        backup_id,
        "REPLICATE",
        {
            "snapshot": {
                "node_id": node.node_id,
                "state": node.snapshot(),
                "known_state": node.export_known_state(),
            }
        },
    )


def handle_replicate(node: "Node", msg: dict[str, object]) -> None:
    payload = dict(msg.get("payload", {}))
    if node.node_id == "N8":
        snapshot = payload.get("snapshot")
        if isinstance(snapshot, dict):
            node.engine.store_replica(str(snapshot["node_id"]), snapshot)
            node.replication_flash_until = node.engine.current_tick + 2
        return

    restore = payload.get("restore")
    if isinstance(restore, dict):
        known_state = restore.get("known_state")
        if isinstance(known_state, dict):
            with node.state_lock:
                for key, value in known_state.items():
                    if isinstance(value, dict):
                        node.state.known_state[key] = dict(value)
        node.engine.log_event(
            "recovery",
            f"[Tick {node.engine.current_tick:02d}] {node.node_id} restored replica state from N8",
        )


def restore_node_from_backup(node: "Node", target_id: str) -> None:
    snapshot = node.engine.get_replica(target_id)
    if not snapshot:
        return
    node.send_message(
        target_id,
        "REPLICATE",
        {"restore": snapshot},
    )
