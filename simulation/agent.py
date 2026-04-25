"""
Robotaxi agent state machine.

States: IDLE → AVAILABLE → DISPATCHED → RIDING → RETURNING → CHARGING → FAULT → OFFLINE
"""

from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple


class AgentState(Enum):
    IDLE = auto()
    AVAILABLE = auto()
    DISPATCHED = auto()
    RIDING = auto()
    RETURNING = auto()
    CHARGING = auto()
    FAULT = auto()
    OFFLINE = auto()


FAULT_TYPES = ["battery_failure", "sensor_fault", "network_loss", "route_conflict", "mechanical"]


@dataclass
class Agent:
    agent_id: str
    position: Tuple[float, float]
    battery: float = 100.0          # percent
    state: AgentState = AgentState.AVAILABLE
    destination: Optional[Tuple[float, float]] = None
    rider_id: Optional[str] = None
    fault_type: Optional[str] = None
    trips_completed: int = 0
    distance_travelled: float = 0.0
    _speed: float = field(default=0.0, repr=False)

    SPEED = 0.8                    # grid units per tick
    BATTERY_DRAIN_MOVING = 0.15    # % per tick while moving
    BATTERY_DRAIN_IDLE = 0.02      # % per tick while idle
    BATTERY_CHARGE_RATE = 1.2      # % per tick while charging
    LOW_BATTERY_THRESHOLD = 20.0

    def step(self, tick: int) -> Optional[str]:
        """Advance agent one simulation tick. Returns an event string if notable."""
        event = None

        if self.state == AgentState.OFFLINE:
            return None

        if self.state == AgentState.FAULT:
            # Random recovery chance each tick
            if random.random() < 0.03:
                self.state = AgentState.AVAILABLE
                self.fault_type = None
                event = f"{self.agent_id} recovered from fault"
            return event

        if self.state == AgentState.CHARGING:
            self.battery = min(100.0, self.battery + self.BATTERY_CHARGE_RATE)
            if self.battery >= 95.0:
                self.state = AgentState.AVAILABLE
                self.destination = None
                event = f"{self.agent_id} fully charged"
            return event

        # Moving states
        if self.state in (AgentState.DISPATCHED, AgentState.RIDING, AgentState.RETURNING):
            if self.destination:
                moved = self._move_toward(self.destination)
                self.battery -= self.BATTERY_DRAIN_MOVING
                self.distance_travelled += moved

                if self._at_destination():
                    event = self._on_arrival(tick)
            else:
                self.state = AgentState.AVAILABLE
        elif self.state == AgentState.AVAILABLE:
            self.battery -= self.BATTERY_DRAIN_IDLE

        # Low battery → go charge
        if self.battery <= self.LOW_BATTERY_THRESHOLD and self.state == AgentState.AVAILABLE:
            self.state = AgentState.RETURNING
            event = f"{self.agent_id} low battery, returning to charge"

        self.battery = max(0.0, self.battery)
        if self.battery == 0.0 and self.state not in (AgentState.FAULT, AgentState.OFFLINE):
            self._trigger_fault("battery_failure")
            event = f"{self.agent_id} battery depleted — fault triggered"

        return event

    def _move_toward(self, target: Tuple[float, float]) -> float:
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        dist = math.hypot(dx, dy)
        if dist < self.SPEED:
            self.position = target
            return dist
        ratio = self.SPEED / dist
        self.position = (self.position[0] + dx * ratio, self.position[1] + dy * ratio)
        return self.SPEED

    def _at_destination(self) -> bool:
        return self.destination is not None and math.hypot(
            self.destination[0] - self.position[0],
            self.destination[1] - self.position[1],
        ) < 0.1

    def _on_arrival(self, tick: int) -> Optional[str]:
        event = None
        if self.state == AgentState.DISPATCHED:
            self.state = AgentState.RIDING
            event = f"{self.agent_id} picked up rider {self.rider_id}"
        elif self.state == AgentState.RIDING:
            self.state = AgentState.AVAILABLE
            self.trips_completed += 1
            self.destination = None
            rider = self.rider_id
            self.rider_id = None
            event = f"{self.agent_id} completed trip for {rider}"
        elif self.state == AgentState.RETURNING:
            self.state = AgentState.CHARGING
            self.destination = None
            event = f"{self.agent_id} started charging"
        return event

    def _trigger_fault(self, fault_type: Optional[str] = None):
        self.state = AgentState.FAULT
        self.fault_type = fault_type or random.choice(FAULT_TYPES)
        self.destination = None
        self.rider_id = None

    def dispatch(self, pickup: Tuple[float, float], dropoff: Tuple[float, float], rider_id: str):
        self.state = AgentState.DISPATCHED
        self.destination = pickup
        self.rider_id = rider_id
        self._dropoff = dropoff

    def set_dropoff(self, dropoff: Tuple[float, float]):
        """Called by fleet manager when agent reaches pickup to set dropoff."""
        self._dropoff = dropoff
        self.destination = dropoff

    @property
    def status_color(self) -> str:
        return {
            AgentState.AVAILABLE: "#2ecc71",
            AgentState.DISPATCHED: "#f39c12",
            AgentState.RIDING: "#3498db",
            AgentState.RETURNING: "#9b59b6",
            AgentState.CHARGING: "#1abc9c",
            AgentState.FAULT: "#e74c3c",
            AgentState.OFFLINE: "#7f8c8d",
            AgentState.IDLE: "#bdc3c7",
        }.get(self.state, "#ffffff")

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "x": round(self.position[0], 2),
            "y": round(self.position[1], 2),
            "battery": round(self.battery, 1),
            "state": self.state.name,
            "rider_id": self.rider_id or "",
            "fault_type": self.fault_type or "",
            "trips_completed": self.trips_completed,
            "distance_travelled": round(self.distance_travelled, 2),
        }
