from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node


def merge_known_state(
    local_state: dict[str, dict[str, object]],
    incoming_state: dict[str, dict[str, object]],
) -> bool:
    changed = False
    for node_id, candidate in incoming_state.items():
        local_entry = local_state.get(node_id)
        candidate_ts = int(candidate.get("lamport_ts", 0))
        if local_entry is None or candidate_ts > int(local_entry.get("lamport_ts", 0)):
            local_state[node_id] = deepcopy(candidate)
            changed = True
    return changed


def gossip_round(node: "Node", candidate_ids: list[str], rng) -> None:
    if not candidate_ids:
        return
    recipients = candidate_ids[:]
    rng.shuffle(recipients)
    for target_id in recipients[: min(2, len(recipients))]:
        node.send_message(
            target_id,
            "GOSSIP",
            {"known_state": deepcopy(node.export_known_state())},
        )
