"""
Fleet manager — orchestrates agents, dispatches riders, logs metrics.
"""

from __future__ import annotations
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Deque, Tuple, Optional

from simulation.agent import Agent, AgentState
from simulation.city_grid import CityGrid
from simulation.fault_injector import FaultInjector
from data.logger import SimLogger


@dataclass
class RideRequest:
    rider_id: str
    pickup: Tuple[float, float]
    dropoff: Tuple[float, float]
    requested_at: int


@dataclass
class FleetMetrics:
    tick: int
    available: int
    dispatched: int
    riding: int
    charging: int
    faulted: int
    offline: int
    active_riders: int
    fleet_utilization: float        # (dispatched + riding) / total
    avg_battery: float
    trips_completed: int
    total_distance: float


class FleetManager:
    RIDE_REQUEST_INTERVAL = 8       # ticks between new ride requests (base)
    FAULT_PROBABILITY = 0.003       # random fault chance per agent per tick
    SURGE_EXTRA_REQUESTS = 5

    def __init__(
        self,
        num_agents: int = 15,
        grid_size: int = 20,
        seed: int = 42,
    ):
        random.seed(seed)
        self.city = CityGrid(size=grid_size, seed=seed)
        self.tick = 0
        self.agents: List[Agent] = self._spawn_agents(num_agents)
        self.pending_requests: Deque[RideRequest] = deque()
        self.active_requests: Dict[str, RideRequest] = {}
        self.completed_trips = 0
        self.event_log: Deque[str] = deque(maxlen=200)
        self.metrics_history: List[FleetMetrics] = []
        self.fault_injector = FaultInjector()
        self.logger = SimLogger()
        self._rider_counter = 0
        self._next_request_tick = self.RIDE_REQUEST_INTERVAL

    def _spawn_agents(self, n: int) -> List[Agent]:
        agents = []
        for i in range(n):
            pos = self.city.random_position()
            battery = random.uniform(60, 100)
            agent = Agent(
                agent_id=f"AV-{i+1:03d}",
                position=pos,
                battery=battery,
            )
            agents.append(agent)
        return agents

    def step(self) -> List[str]:
        """Advance simulation one tick. Returns list of new events."""
        self.tick += 1
        events: List[str] = []

        # Generate ride requests
        if self.tick >= self._next_request_tick:
            req = self._generate_request()
            self.pending_requests.append(req)
            events.append(f"Tick {self.tick}: Ride request {req.rider_id} at {req.pickup}")
            self._next_request_tick = self.tick + random.randint(
                self.RIDE_REQUEST_INTERVAL - 2, self.RIDE_REQUEST_INTERVAL + 4
            )

        # Dispatch available agents to pending requests
        events.extend(self._dispatch_cycle())

        # Step each agent
        for agent in self.agents:
            evt = agent.step(self.tick)
            if evt:
                events.append(f"Tick {self.tick}: {evt}")
            # Handle state transition: dispatched → arrived at pickup → set dropoff
            if (
                agent.state == AgentState.RIDING
                and agent.rider_id in self.active_requests
                and agent.destination is None
            ):
                req = self.active_requests[agent.rider_id]
                agent.set_dropoff(req.dropoff)

            # Count completed trips
            if agent.state == AgentState.AVAILABLE and agent.rider_id is None:
                req_ids_done = [
                    rid for rid, r in self.active_requests.items()
                    if not any(a.rider_id == rid for a in self.agents)
                ]
                for rid in req_ids_done:
                    del self.active_requests[rid]
                    self.completed_trips += 1

            # Send low-battery agents to nearest charger
            if (
                agent.state == AgentState.RETURNING
                and agent.destination is None
            ):
                agent.destination = self.city.nearest_charging_station(agent.position)

            # Random ambient faults
            if random.random() < self.FAULT_PROBABILITY and agent.state == AgentState.AVAILABLE:
                agent._trigger_fault()
                events.append(f"Tick {self.tick}: AMBIENT FAULT — {agent.agent_id}")

        # Record metrics
        m = self._compute_metrics()
        self.metrics_history.append(m)
        self.logger.log_tick(m, events)

        self.event_log.extendleft(reversed(events))
        return events

    def _generate_request(self) -> RideRequest:
        self._rider_counter += 1
        pickup = self.city.random_spawn_position()
        dropoff = self.city.random_position()
        return RideRequest(
            rider_id=f"R-{self._rider_counter:04d}",
            pickup=pickup,
            dropoff=dropoff,
            requested_at=self.tick,
        )

    def _dispatch_cycle(self) -> List[str]:
        events = []
        available = [a for a in self.agents if a.state == AgentState.AVAILABLE]
        while self.pending_requests and available:
            req = self.pending_requests.popleft()
            best = min(
                available,
                key=lambda a: math.hypot(
                    a.position[0] - req.pickup[0], a.position[1] - req.pickup[1]
                ),
            )
            best.dispatch(req.pickup, req.dropoff, req.rider_id)
            self.active_requests[req.rider_id] = req
            available.remove(best)
            events.append(
                f"Tick {self.tick}: {best.agent_id} dispatched for {req.rider_id}"
            )
        return events

    def _compute_metrics(self) -> FleetMetrics:
        state_counts = {s: 0 for s in AgentState}
        for a in self.agents:
            state_counts[a.state] += 1
        total = len(self.agents)
        active = state_counts[AgentState.DISPATCHED] + state_counts[AgentState.RIDING]
        avg_bat = sum(a.battery for a in self.agents) / total if total else 0
        return FleetMetrics(
            tick=self.tick,
            available=state_counts[AgentState.AVAILABLE],
            dispatched=state_counts[AgentState.DISPATCHED],
            riding=state_counts[AgentState.RIDING],
            charging=state_counts[AgentState.CHARGING],
            faulted=state_counts[AgentState.FAULT],
            offline=state_counts[AgentState.OFFLINE],
            active_riders=len(self.active_requests),
            fleet_utilization=round(active / total, 3) if total else 0,
            avg_battery=round(avg_bat, 1),
            trips_completed=self.completed_trips,
            total_distance=round(sum(a.distance_travelled for a in self.agents), 1),
        )

    def inject_fault(self, scenario: str) -> List[str]:
        events = self.fault_injector.inject(scenario, self.agents, self.city)
        if scenario == "rider_surge":
            for _ in range(self.SURGE_EXTRA_REQUESTS):
                self.pending_requests.append(self._generate_request())
        self.event_log.extendleft(reversed(events))
        return events

    def bring_agents_online(self):
        """Recover all offline agents."""
        for a in self.agents:
            if a.state == AgentState.OFFLINE:
                a.state = AgentState.AVAILABLE

    @property
    def agent_data(self) -> List[dict]:
        return [a.to_dict() for a in self.agents]

    @property
    def recent_events(self) -> List[str]:
        return list(self.event_log)
