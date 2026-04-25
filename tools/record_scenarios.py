"""
tools/record_scenarios.py

Generates GIF animations for each fleet scenario.
Run from project root:  python tools/record_scenarios.py

Outputs 6 GIFs to:  dashboard/assets/
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D

from simulation.fleet_manager import FleetManager
from simulation.agent import AgentState

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dashboard", "assets",
)
os.makedirs(ASSETS_DIR, exist_ok=True)

# ── Visual style (matches dashboard academic palette) ─────────────────────────
STATE_COLORS = {
    AgentState.AVAILABLE:  "#2ca02c",
    AgentState.DISPATCHED: "#ff7f0e",
    AgentState.RIDING:     "#1f77b4",
    AgentState.RETURNING:  "#9467bd",
    AgentState.CHARGING:   "#17becf",
    AgentState.FAULT:      "#d62728",
    AgentState.OFFLINE:    "#7f7f7f",
    AgentState.IDLE:       "#bcbd22",
}
STATE_MARKERS = {
    AgentState.AVAILABLE:  "o",
    AgentState.DISPATCHED: "^",
    AgentState.RIDING:     "D",
    AgentState.RETURNING:  "v",
    AgentState.CHARGING:   "s",
    AgentState.FAULT:      "X",
    AgentState.OFFLINE:    "o",
    AgentState.IDLE:       "o",
}
LEGEND_ELEMENTS = [
    Line2D([0],[0], marker="o", color="w", markerfacecolor="#2ca02c", markersize=7, label="Available"),
    Line2D([0],[0], marker="^", color="w", markerfacecolor="#ff7f0e", markersize=7, label="Dispatched"),
    Line2D([0],[0], marker="D", color="w", markerfacecolor="#1f77b4", markersize=7, label="Riding"),
    Line2D([0],[0], marker="v", color="w", markerfacecolor="#9467bd", markersize=7, label="Returning"),
    Line2D([0],[0], marker="s", color="w", markerfacecolor="#17becf", markersize=7, label="Charging"),
    Line2D([0],[0], marker="X", color="w", markerfacecolor="#d62728", markersize=7, label="Fault"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor="#7f7f7f", markersize=7, label="Offline"),
]


# ── Frame collection ──────────────────────────────────────────────────────────

def collect_frames(fm, ticks, inject_fn=None, frame_skip=2):
    frames = []
    for t in range(ticks):
        if inject_fn:
            inject_fn(fm, t)
        fm.step()
        if t % frame_skip == 0:
            m = fm.metrics_history[-1] if fm.metrics_history else None
            frames.append({
                "tick":     fm.tick,
                "agents":   [(a.position, a.state, a.agent_id, a.destination) for a in fm.agents],
                "stations": list(fm.city.charging_stations),
                "m":        m,
                "ga":       dict(fm.ga_stats),
            })
    return frames


# ── Single frame renderer ─────────────────────────────────────────────────────

def draw_frame(ax, frame, title_top, title_bottom="", show_ga=False):
    ax.clear()
    ax.set_facecolor("white")
    ax.grid(True, color="#e0e0e0", linewidth=0.7, zorder=0)
    ax.set_xlim(-0.5, 20.5)
    ax.set_ylim(-0.5, 20.5)
    ax.set_xlabel("X  (grid units)", fontsize=8, color="#444")
    ax.set_ylabel("Y  (grid units)", fontsize=8, color="#444")
    ax.set_aspect("equal")
    ax.tick_params(labelsize=7, colors="#666")
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")

    # Charging stations
    for cs in frame["stations"]:
        ax.scatter(cs[0], cs[1], marker="s", s=200, color="#17becf",
                   alpha=0.45, zorder=2, edgecolors="#0d7a86", linewidths=1.5)
        ax.text(cs[0], cs[1], "⚡", ha="center", va="center",
                fontsize=7, zorder=3, color="#0d7a86")

    # Route lines (agent → destination)
    for pos, state, _, dest in frame["agents"]:
        if dest:
            ax.plot([pos[0], dest[0]], [pos[1], dest[1]],
                    "--", color=STATE_COLORS.get(state, "#aaa"),
                    alpha=0.22, linewidth=0.9, zorder=1)

    # Agents
    for pos, state, aid, _ in frame["agents"]:
        c = STATE_COLORS.get(state, "#999")
        m_sym = STATE_MARKERS.get(state, "o")
        alpha = 0.35 if state == AgentState.OFFLINE else 1.0
        ax.scatter(pos[0], pos[1], c=c, marker=m_sym, s=95,
                   zorder=4, edgecolors="#222", linewidths=0.7, alpha=alpha)
        ax.annotate(aid.replace("AV-", ""), pos,
                    xytext=(2, 3), textcoords="offset points",
                    fontsize=5.5, color="#333", zorder=5)

    # Title block
    m = frame["m"]
    if m:
        stats = (f"Tick {frame['tick']}   "
                 f"Available {m.available}  |  "
                 f"In-service {m.dispatched + m.riding}  |  "
                 f"Faulted {m.faulted}  |  "
                 f"Trips {m.trips_completed}")
        ga = frame["ga"]
        if show_ga and ga["total_dispatches"] > 0:
            stats += (f"\nGA  ▲{ga['improvement_pct']}% vs greedy  "
                      f"| Saved {ga['cumulative_saving']:.1f} units total")
        ax.set_title(
            f"{title_top}\n{stats}",
            fontsize=8.5, fontweight="bold", pad=8,
            loc="left", color="#1a1a2e",
        )

    ax.legend(handles=LEGEND_ELEMENTS, loc="upper right",
              fontsize=6, framealpha=0.92, ncol=2,
              edgecolor="#ccc", borderpad=0.5)


# ── GIF saver ─────────────────────────────────────────────────────────────────

def save_gif(frames, title, filename, fps=7, show_ga=False):
    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=85)
    fig.patch.set_facecolor("white")
    plt.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.08)

    def update(i):
        draw_frame(ax, frames[i], title, show_ga=show_ga)

    anim = FuncAnimation(fig, update, frames=len(frames), interval=1000 // fps)
    path = os.path.join(ASSETS_DIR, filename)
    anim.save(path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    kb = os.path.getsize(path) // 1024
    print(f"  OK  {filename:<35}  {len(frames)} frames  {kb} KB")
    return path


# ── Scenarios ─────────────────────────────────────────────────────────────────

def scenario_normal():
    print("1/6  Normal fleet operation")
    fm = FleetManager(num_agents=15, grid_size=20, seed=42)
    frames = collect_frames(fm, ticks=160, frame_skip=2)
    save_gif(frames, "Normal Fleet Operation", "normal_operation.gif")


def scenario_ga():
    print("2/6  GA dispatch optimiser")
    fm = FleetManager(num_agents=15, grid_size=20, seed=7)

    def inject(fm, t):
        if t in (15, 55, 100):
            fm.inject_fault("rider_surge")

    frames = collect_frames(fm, ticks=140, inject_fn=inject, frame_skip=2)
    save_gif(frames, "GA Dispatch Optimiser — Rider Surge Events",
             "ga_dispatch.gif", show_ga=True)


def scenario_mass_outage():
    print("3/6  Mass outage & recovery")
    fm = FleetManager(num_agents=15, grid_size=20, seed=99)

    def inject(fm, t):
        if t == 40:
            fm.inject_fault("mass_outage")
        if t == 85:
            fm.bring_agents_online()

    frames = collect_frames(fm, ticks=160, inject_fn=inject, frame_skip=2)
    save_gif(frames, "Mass Outage & Fleet Recovery", "mass_outage.gif")


def scenario_cascade():
    print("4/6  Cascading fault")
    fm = FleetManager(num_agents=15, grid_size=20, seed=13)

    def inject(fm, t):
        if t == 35:
            fm.inject_fault("cascading_fault")

    frames = collect_frames(fm, ticks=140, inject_fn=inject, frame_skip=2)
    save_gif(frames, "Cascading Fault Propagation", "cascading_fault.gif")


def scenario_battery():
    print("5/6  Battery drain & recharge")
    fm = FleetManager(num_agents=15, grid_size=20, seed=55)

    def inject(fm, t):
        if t in (10, 55, 100):
            fm.inject_fault("battery_drain")

    frames = collect_frames(fm, ticks=150, inject_fn=inject, frame_skip=2)
    save_gif(frames, "Battery Drain & Recharge Cycle", "battery_drain.gif")


def scenario_surge():
    print("6/6  Rider surge — GA under load")
    fm = FleetManager(num_agents=15, grid_size=20, seed=21)

    def inject(fm, t):
        if t in (20, 55, 95):
            fm.inject_fault("rider_surge")
            fm.inject_fault("rider_surge")

    frames = collect_frames(fm, ticks=140, inject_fn=inject, frame_skip=2)
    save_gif(frames, "Rider Surge — GA Under Load",
             "rider_surge.gif", show_ga=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nGenerating scenario GIFs -> {ASSETS_DIR}\n")
    scenario_normal()
    scenario_ga()
    scenario_mass_outage()
    scenario_cascade()
    scenario_battery()
    scenario_surge()
    print("\nDone.")
