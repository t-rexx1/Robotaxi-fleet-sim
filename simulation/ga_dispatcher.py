"""
GA-based fleet dispatch optimiser.

Problem
-------
Given R pending ride requests and A available agents (R <= A), find the
assignment of agents to requests that minimises total pickup distance while
penalising low-battery agents for long trips.

Chromosome representation
-------------------------
A permutation of agent indices [0 .. A-1].
Gene i → agents[chromosome[i]] handles requests[i].
Only the first R genes are decoded; the rest are unused this cycle.

Genetic operators
-----------------
- Selection   : tournament (k=3)
- Crossover   : Order Crossover (OX) — always produces a valid permutation
- Mutation    : swap two randomly chosen genes
- Elitism     : top-N individuals carried over unchanged

Fitness (maximised, stored as negative cost)
--------------------------------------------
  cost = Σ pickup_distance(agent_i, request_i)
       + battery_penalty * max(0, LOW_BAT - agent.battery)   [for each pair]
       + coverage_penalty * stdev of remaining idle positions [fleet spread]

A lower cost → higher fitness.
"""

from __future__ import annotations
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class Individual:
    chromosome: List[int]
    fitness: float = field(default=0.0, compare=False)

    def clone(self) -> "Individual":
        return Individual(chromosome=self.chromosome[:], fitness=self.fitness)


# ── GA Dispatcher ─────────────────────────────────────────────────────────────

class GADispatcher:
    # Hyperparameters — tuned for speed vs quality on a 15-agent fleet
    POP_SIZE        = 80
    GENERATIONS     = 40
    CROSSOVER_RATE  = 0.88
    MUTATION_RATE   = 0.22
    TOURNAMENT_K    = 3
    ELITE_N         = 2

    # Fitness penalty weights
    LOW_BATTERY_THRESHOLD  = 35.0
    BATTERY_PENALTY_WEIGHT = 3.0    # extra cost per % below threshold
    COVERAGE_PENALTY_WEIGHT = 0.5   # penalise clustering idle agents

    def __init__(self):
        self.last_ga_cost: float      = 0.0
        self.last_greedy_cost: float  = 0.0
        self.improvement_pct: float   = 0.0
        self.convergence: List[float] = []   # best cost per generation
        self.total_dispatches: int    = 0
        self.cumulative_saving: float = 0.0  # total distance saved vs greedy

    # ── Public API ────────────────────────────────────────────────────────────

    def assign(self, agents: list, requests: list) -> List[Tuple]:
        """
        Return list of (agent, request) pairs — optimal assignment.

        Falls back to nearest-neighbour for 0 or 1 assignments (trivially
        optimal) so the GA overhead is only paid when it matters.
        """
        if not agents or not requests:
            return []

        n = min(len(agents), len(requests))
        reqs = list(requests[:n])

        if n == 1:
            best = min(agents, key=lambda a: self._dist(a.position, reqs[0].pickup))
            return [(best, reqs[0])]

        # Greedy baseline for comparison
        self.last_greedy_cost = self._greedy_cost(agents, reqs)

        # Run GA
        best_individual = self._run(agents, reqs)
        self.last_ga_cost = -best_individual.fitness

        if self.last_greedy_cost > 0:
            saving = self.last_greedy_cost - self.last_ga_cost
            self.improvement_pct = round(saving / self.last_greedy_cost * 100, 1)
            self.cumulative_saving += max(0.0, saving)
        self.total_dispatches += 1

        return self._decode(best_individual.chromosome, agents, reqs)

    # ── GA core ───────────────────────────────────────────────────────────────

    def _run(self, agents: list, reqs: list) -> Individual:
        n_agents = len(agents)
        population = self._init_population(n_agents)
        self.convergence = []

        for _ in range(self.GENERATIONS):
            # Evaluate
            for ind in population:
                ind.fitness = self._fitness(ind.chromosome, agents, reqs)

            population.sort(key=lambda x: x.fitness, reverse=True)
            self.convergence.append(-population[0].fitness)  # best cost this gen

            # Next generation — elites pass through unchanged
            next_gen: List[Individual] = [ind.clone() for ind in population[:self.ELITE_N]]

            while len(next_gen) < self.POP_SIZE:
                parent1 = self._tournament(population)
                parent2 = self._tournament(population)
                child = self._order_crossover(parent1, parent2)
                child = self._swap_mutate(child)
                next_gen.append(child)

            population = next_gen

        # Final evaluation pass
        for ind in population:
            ind.fitness = self._fitness(ind.chromosome, agents, reqs)

        return max(population, key=lambda x: x.fitness)

    def _init_population(self, n_agents: int) -> List[Individual]:
        base = list(range(n_agents))
        population = []
        for _ in range(self.POP_SIZE):
            chrom = base[:]
            random.shuffle(chrom)
            population.append(Individual(chromosome=chrom))
        return population

    def _fitness(self, chromosome: List[int], agents: list, reqs: list) -> float:
        """Higher is better (negative total cost)."""
        cost = 0.0
        idle_positions = []

        for i, req in enumerate(reqs):
            agent = agents[chromosome[i]]
            pickup_dist = self._dist(agent.position, req.pickup)
            cost += pickup_dist

            # Battery penalty — avoid sending low-battery agent on a long trip
            if agent.battery < self.LOW_BATTERY_THRESHOLD:
                deficit = self.LOW_BATTERY_THRESHOLD - agent.battery
                cost += self.BATTERY_PENALTY_WEIGHT * deficit

        # Coverage penalty — reward keeping remaining agents spread across the grid
        assigned_indices = set(chromosome[:len(reqs)])
        for idx, agent in enumerate(agents):
            if idx not in assigned_indices:
                idle_positions.append(agent.position)

        if len(idle_positions) >= 2:
            xs = [p[0] for p in idle_positions]
            ys = [p[1] for p in idle_positions]
            spread = statistics.stdev(xs) + statistics.stdev(ys)
            # Penalise *low* spread — we want idle agents distributed
            cost -= self.COVERAGE_PENALTY_WEIGHT * spread

        return -cost  # maximise

    # ── Genetic operators ─────────────────────────────────────────────────────

    def _tournament(self, population: List[Individual]) -> Individual:
        contestants = random.sample(population, min(self.TOURNAMENT_K, len(population)))
        return max(contestants, key=lambda x: x.fitness)

    def _order_crossover(self, p1: Individual, p2: Individual) -> Individual:
        """
        Order Crossover (OX):
        1. Copy a random slice from p1 into the child.
        2. Fill remaining positions in p2's order, skipping already-placed genes.
        Guarantees the child is always a valid permutation.
        """
        if random.random() > self.CROSSOVER_RATE:
            return p1.clone()

        n = len(p1.chromosome)
        a, b = sorted(random.sample(range(n), 2))

        child_chrom: List[Optional[int]] = [None] * n
        child_chrom[a : b + 1] = p1.chromosome[a : b + 1]

        segment_set = set(child_chrom[a : b + 1])
        fill = [g for g in p2.chromosome if g not in segment_set]

        fill_idx = 0
        for i in range(n):
            if child_chrom[i] is None:
                child_chrom[i] = fill[fill_idx]
                fill_idx += 1

        return Individual(chromosome=child_chrom)

    def _swap_mutate(self, ind: Individual) -> Individual:
        """Swap two randomly chosen genes — always produces a valid permutation."""
        chrom = ind.chromosome[:]
        if random.random() < self.MUTATION_RATE:
            i, j = random.sample(range(len(chrom)), 2)
            chrom[i], chrom[j] = chrom[j], chrom[i]
        return Individual(chromosome=chrom)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _decode(self, chromosome: List[int], agents: list, reqs: list) -> List[Tuple]:
        return [(agents[chromosome[i]], reqs[i]) for i in range(len(reqs))]

    def _greedy_cost(self, agents: list, reqs: list) -> float:
        """Nearest-neighbour greedy baseline — O(R*A)."""
        remaining = list(agents)
        cost = 0.0
        for req in reqs:
            if not remaining:
                break
            best = min(remaining, key=lambda a: self._dist(a.position, req.pickup))
            cost += self._dist(best.position, req.pickup)
            remaining.remove(best)
        return cost

    @staticmethod
    def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "total_dispatches": self.total_dispatches,
            "last_ga_cost": round(self.last_ga_cost, 2),
            "last_greedy_cost": round(self.last_greedy_cost, 2),
            "improvement_pct": self.improvement_pct,
            "cumulative_saving": round(self.cumulative_saving, 2),
            "convergence": self.convergence,
        }
