from __future__ import annotations

import argparse
import time

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.engine import build_default_simulation

TICK_DURATION = 0.5


def balance_bar(balance: float) -> str:
    magnitude = min(int(abs(balance) * 2), 10)
    return "▓" * magnitude + "░" * (10 - magnitude)


def render_snapshot(snapshot) -> Group:
    table = Table(title=f"Decentralized Smart Grid | Tick {snapshot.tick:03d}")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Power")
    table.add_column("Clock")
    table.add_column("Status")

    for node in snapshot.nodes:
        status = str(node["status"])
        style = "white"
        if status == "CRASHED":
            style = "bold red"
        elif status == "REQUESTING":
            style = "yellow"
        elif status == "MUTEX":
            style = "bold orange3"
        elif status == "LEADER":
            style = "bold cyan"
        elif node["replicating"]:
            style = "blue"

        badge = " ★" if node["is_leader"] else ""
        table.add_row(
            str(node["node_id"]),
            str(node["node_type"]),
            f"{float(node['power_output']):>4.1f}kW",
            f"[{int(node['lamport_clock']):03d}]",
            Text(status + badge, style=style),
        )

    summary = Panel(
        Text(
            f"Balance: {snapshot.balance:>4.1f}kW  "
            f"Status: {snapshot.status}  "
            f"Convergence: {snapshot.convergence}  "
            f"Leader: {snapshot.leader or 'None'}\n"
            f"Bar: {balance_bar(snapshot.balance)}",
            style="bold green" if snapshot.status == "STABLE" else ("yellow" if snapshot.status == "STRESSED" else "bold red"),
        ),
        title="Grid State",
    )

    gossip_lines = [Text(entry["text"], style=message_style(entry["type"])) for entry in snapshot.messages[-8:]]
    event_lines = [Text(entry["text"], style=event_style(entry["type"])) for entry in snapshot.events[-8:]]
    gossip_panel = Panel(Group(*gossip_lines) if gossip_lines else Text("No messages yet"), title="Gossip Activity")
    event_panel = Panel(Group(*event_lines) if event_lines else Text("No events yet"), title="Event Log")
    return Group(table, summary, gossip_panel, event_panel)


def message_style(message_type: str) -> str:
    return {
        "GOSSIP": "cyan",
        "REQUEST": "yellow",
        "ELECTION": "orange3",
        "COORDINATOR": "green",
        "REPLICATE": "grey70",
    }.get(message_type, "white")


def event_style(event_type: str) -> str:
    return {
        "fault": "yellow",
        "mutex": "blue",
        "crash": "bold red",
        "election": "orange3",
        "recovery": "green",
        "replication": "grey70",
    }.get(event_type, "white")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fallback smart-grid terminal simulation")
    parser.add_argument("--ticks", type=int, default=0, help="Stop after N ticks")
    parser.add_argument("--tick-duration", type=float, default=TICK_DURATION)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    sim = build_default_simulation(tick_duration=args.tick_duration, seed=args.seed)
    sim.start()

    try:
        with Live(render_snapshot(sim.snapshot()), refresh_per_second=max(4, int(1 / args.tick_duration)), screen=True) as live:
            last_tick = -1
            while True:
                snapshot = sim.snapshot()
                if snapshot.tick != last_tick:
                    live.update(render_snapshot(snapshot))
                    last_tick = snapshot.tick
                if args.ticks and snapshot.tick >= args.ticks:
                    break
                time.sleep(min(args.tick_duration / 2, 0.1))
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
