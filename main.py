"""
Headless simulation runner — runs N ticks and prints a summary.
Useful for CI, profiling, or generating a dataset without the dashboard.

Usage:
    python main.py --ticks 200 --agents 15 --seed 42
"""

import argparse
import time
from simulation.fleet_manager import FleetManager


def run(ticks: int, agents: int, seed: int, verbose: bool):
    print(f"\nRobotaxi Fleet Simulation")
    print(f"  Agents : {agents}")
    print(f"  Ticks  : {ticks}")
    print(f"  Seed   : {seed}")
    print("-" * 50)

    fleet = FleetManager(num_agents=agents, grid_size=20, seed=seed)
    t0 = time.perf_counter()

    for tick in range(ticks):
        events = fleet.step()
        if verbose:
            for e in events:
                print(f"  {e}")
        elif tick % 25 == 0:
            m = fleet.metrics_history[-1]
            print(
                f"  Tick {m.tick:>4} | "
                f"Avail={m.available} Riding={m.riding} "
                f"Fault={m.faulted} Offline={m.offline} | "
                f"Trips={m.trips_completed} Util={m.fleet_utilization*100:.0f}% "
                f"Bat={m.avg_battery:.0f}%"
            )

    elapsed = time.perf_counter() - t0
    m = fleet.metrics_history[-1]
    print("-" * 50)
    print(f"Simulation complete in {elapsed:.2f}s")
    print(f"  Total trips completed : {m.trips_completed}")
    print(f"  Total distance        : {m.total_distance:.0f} units")
    print(f"  Final fleet utilization: {m.fleet_utilization*100:.1f}%")
    print(f"  Final avg battery     : {m.avg_battery:.1f}%")
    print(f"  Agents faulted        : {m.faulted}")
    print(f"  Agents offline        : {m.offline}")
    print(f"  Metrics saved to      : data/simulation.db")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robotaxi Fleet Headless Runner")
    parser.add_argument("--ticks", type=int, default=100, help="Number of simulation ticks")
    parser.add_argument("--agents", type=int, default=15, help="Number of agents in the fleet")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--verbose", action="store_true", help="Print all events")
    args = parser.parse_args()
    run(args.ticks, args.agents, args.seed, args.verbose)
