"""
Simulation data logger — writes tick metrics and events to SQLite.
"""

from __future__ import annotations
import sqlite3
import json
import os
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.fleet_manager import FleetMetrics

DB_PATH = os.path.join(os.path.dirname(__file__), "simulation.db")


class SimLogger:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tick_metrics (
                    tick INTEGER PRIMARY KEY,
                    available INTEGER,
                    dispatched INTEGER,
                    riding INTEGER,
                    charging INTEGER,
                    faulted INTEGER,
                    offline INTEGER,
                    active_riders INTEGER,
                    fleet_utilization REAL,
                    avg_battery REAL,
                    trips_completed INTEGER,
                    total_distance REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER,
                    event TEXT
                )
            """)

    def log_tick(self, metrics, events: List[str]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tick_metrics VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    metrics.tick,
                    metrics.available,
                    metrics.dispatched,
                    metrics.riding,
                    metrics.charging,
                    metrics.faulted,
                    metrics.offline,
                    metrics.active_riders,
                    metrics.fleet_utilization,
                    metrics.avg_battery,
                    metrics.trips_completed,
                    metrics.total_distance,
                ),
            )
            for evt in events:
                conn.execute(
                    "INSERT INTO events (tick, event) VALUES (?,?)",
                    (metrics.tick, evt),
                )

    def load_metrics(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tick_metrics ORDER BY tick ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def load_events(self, last_n: int = 100) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT tick, event FROM events ORDER BY id DESC LIMIT ?", (last_n,)
            ).fetchall()
        return [dict(r) for r in rows]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tick_metrics")
            conn.execute("DELETE FROM events")
