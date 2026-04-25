"""
Fault injection scenarios for the fleet simulation.
"""

from __future__ import annotations
import random
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.agent import Agent, AgentState


SCENARIOS = {
    "random_fault": "Randomly fault one available agent",
    "mass_outage": "Take 30-50% of the fleet offline simultaneously",
    "battery_drain": "Drain battery of 3 random agents to critical levels",
    "cascading_fault": "Fault 1 agent, then fault neighbours within 3 grid units",
    "rider_surge": "Inject 5 simultaneous ride requests",
}


class FaultInjector:
    def __init__(self):
        self.event_log: List[str] = []

    def inject(self, scenario: str, agents: list, city_grid=None) -> List[str]:
        events = []
        fn = getattr(self, f"_scenario_{scenario}", None)
        if fn:
            events = fn(agents, city_grid)
        self.event_log.extend(events)
        return events

    def _scenario_random_fault(self, agents, _grid) -> List[str]:
        from simulation.agent import AgentState
        candidates = [a for a in agents if a.state == AgentState.AVAILABLE]
        if not candidates:
            return ["random_fault: no available agents to fault"]
        target = random.choice(candidates)
        target._trigger_fault()
        return [f"FAULT INJECTED — {target.agent_id}: {target.fault_type}"]

    def _scenario_mass_outage(self, agents, _grid) -> List[str]:
        from simulation.agent import AgentState
        count = max(1, int(len(agents) * random.uniform(0.3, 0.5)))
        targets = random.sample(agents, count)
        events = []
        for a in targets:
            if a.state != AgentState.OFFLINE:
                a.state = AgentState.OFFLINE
                a.destination = None
                a.rider_id = None
                events.append(f"MASS OUTAGE — {a.agent_id} taken offline")
        return events

    def _scenario_battery_drain(self, agents, _grid) -> List[str]:
        targets = random.sample(agents, min(3, len(agents)))
        events = []
        for a in targets:
            a.battery = random.uniform(5.0, 15.0)
            events.append(f"BATTERY DRAIN — {a.agent_id} battery at {a.battery:.1f}%")
        return events

    def _scenario_cascading_fault(self, agents, _grid) -> List[str]:
        import math
        from simulation.agent import AgentState
        if not agents:
            return []
        seed = random.choice(agents)
        seed._trigger_fault()
        events = [f"CASCADE SEED — {seed.agent_id} faulted ({seed.fault_type})"]
        for a in agents:
            if a is seed:
                continue
            dist = math.hypot(a.position[0] - seed.position[0], a.position[1] - seed.position[1])
            if dist < 3.0 and random.random() < 0.6:
                a._trigger_fault("cascading_fault")
                events.append(f"CASCADE — {a.agent_id} faulted (proximity to {seed.agent_id})")
        return events

    def _scenario_rider_surge(self, agents, grid) -> List[str]:
        # Just returns events; fleet manager picks these up as pending requests
        return [f"SURGE EVENT — 5 simultaneous ride requests injected"]
