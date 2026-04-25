"""
City grid — a simple NxN grid with charging stations and spawn zones.
"""

from __future__ import annotations
import random
from typing import List, Tuple


class CityGrid:
    def __init__(self, size: int = 20, num_charging_stations: int = 4, seed: int = 42):
        self.size = size
        random.seed(seed)
        self.charging_stations: List[Tuple[float, float]] = self._place_charging_stations(
            num_charging_stations
        )

    def _place_charging_stations(self, n: int) -> List[Tuple[float, float]]:
        """Spread charging stations roughly evenly across quadrants."""
        quadrant_size = self.size / 2
        stations = []
        for qx in range(2):
            for qy in range(2):
                x = qx * quadrant_size + random.uniform(2, quadrant_size - 2)
                y = qy * quadrant_size + random.uniform(2, quadrant_size - 2)
                stations.append((round(x, 1), round(y, 1)))
        return stations[:n]

    def nearest_charging_station(self, position: Tuple[float, float]) -> Tuple[float, float]:
        import math
        return min(
            self.charging_stations,
            key=lambda s: math.hypot(s[0] - position[0], s[1] - position[1]),
        )

    def random_position(self) -> Tuple[float, float]:
        return (
            round(random.uniform(0, self.size), 1),
            round(random.uniform(0, self.size), 1),
        )

    def random_spawn_position(self) -> Tuple[float, float]:
        """Bias spawns toward city-centre edges to simulate hailing."""
        edge = random.randint(0, 3)
        half = self.size / 2
        jitter = random.uniform(-half * 0.4, half * 0.4)
        if edge == 0:
            return (half + jitter, random.uniform(0, 2))
        elif edge == 1:
            return (half + jitter, random.uniform(self.size - 2, self.size))
        elif edge == 2:
            return (random.uniform(0, 2), half + jitter)
        else:
            return (random.uniform(self.size - 2, self.size), half + jitter)
