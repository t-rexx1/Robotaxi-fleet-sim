"""
Robotaxi Fleet Simulation — Dashboard
Run with:  streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

from simulation.fleet_manager import FleetManager
from simulation.fault_injector import SCENARIOS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Robotaxi Fleet Sim",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared plot style (academic / Zohdi-lab aesthetic) ────────────────────────
PLOT_STYLE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial, sans-serif", color="#1a1a2e", size=12),
    margin=dict(l=50, r=20, t=45, b=40),
)
GRID_STYLE = dict(showgrid=True, gridcolor="#e0e0e0", gridwidth=1,
                  zeroline=True, zerolinecolor="#cccccc",
                  linecolor="#999999", linewidth=1, showline=True)

# Matplotlib tab10-style palette — familiar from academic plots
STATE_COLORS = {
    "AVAILABLE": "#2ca02c",   # green
    "DISPATCHED": "#ff7f0e",  # orange
    "RIDING":     "#1f77b4",  # blue
    "RETURNING":  "#9467bd",  # purple
    "CHARGING":   "#17becf",  # cyan
    "FAULT":      "#d62728",  # red
    "OFFLINE":    "#7f7f7f",  # gray
    "IDLE":       "#bcbd22",
}
STATE_SYMBOLS = {
    "AVAILABLE": "circle",
    "DISPATCHED": "triangle-up",
    "RIDING":    "diamond",
    "RETURNING": "triangle-down",
    "CHARGING":  "square",
    "FAULT":     "x",
    "OFFLINE":   "circle-open",
    "IDLE":      "circle-open",
}

# ── Session state ─────────────────────────────────────────────────────────────
APP_VERSION = "3"
if st.session_state.get("_version") != APP_VERSION:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state["_version"] = APP_VERSION

if "fleet"      not in st.session_state:
    st.session_state.fleet = FleetManager(num_agents=15, grid_size=20)
if "running"    not in st.session_state:
    st.session_state.running = False
if "tick_speed" not in st.session_state:
    st.session_state.tick_speed = 0.3

fleet: FleetManager = st.session_state.fleet

# ── Sidebar (static — never blinks) ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### Fleet Control")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶  Start", use_container_width=True, type="primary"):
            st.session_state.running = True
    with c2:
        if st.button("⏸  Pause", use_container_width=True):
            st.session_state.running = False

    if st.button("↺  Reset", use_container_width=True):
        fleet.logger.clear()
        st.session_state.fleet = FleetManager(num_agents=15, grid_size=20)
        st.session_state.running = False
        st.rerun()

    st.divider()
    st.markdown("### ⚡ Fault Injection")
    st.caption("Inject adversarial scenarios mid-run to test fleet resilience.")
    scenario = st.selectbox(
        "Scenario", options=list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k],
    )
    if st.button("Inject Fault", use_container_width=True, type="secondary"):
        fleet.inject_fault(scenario)
        st.toast(f"Injected: {scenario}", icon="⚡")
    if st.button("Bring All Online", use_container_width=True):
        fleet.bring_agents_online()

    st.divider()
    st.markdown("### ⚙ Settings")
    num_agents = st.slider("Fleet size", 5, 30, 15)
    tick_speed  = st.slider("Simulation speed (s/tick)", 0.05, 1.5, 0.3, step=0.05)
    st.session_state.tick_speed = tick_speed

    if st.button("Apply fleet size", use_container_width=True):
        fleet.logger.clear()
        st.session_state.fleet = FleetManager(num_agents=num_agents, grid_size=20)
        st.session_state.running = False
        st.rerun()

# ── Static page header ────────────────────────────────────────────────────────
st.markdown("## Robotaxi Fleet Simulation")
st.caption(
    "Multi-agent autonomous vehicle fleet on a 20 × 20 city grid. "
    "A **Genetic Algorithm** optimises every dispatch cycle, replacing naive nearest-neighbour assignment. "
    "Use Fault Injection in the sidebar to stress-test fleet resilience."
)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# LIVE FRAGMENT — only this section rerenders each tick (no full-page blink)
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment
def live_dashboard():
    fleet: FleetManager = st.session_state.fleet

    # Advance simulation one tick
    if st.session_state.running:
        fleet.step()

    m   = fleet.metrics_history[-1] if fleet.metrics_history else None
    ga  = fleet.ga_stats

    # ── 1. GA Hero Panel ─────────────────────────────────────────────────────
    st.markdown("### Genetic Algorithm Dispatch Optimiser")
    st.caption(
        "At each tick, all pending ride requests are assigned to available agents via a GA "
        "(population 80, 40 generations, Order Crossover, swap mutation, tournament selection k=3, elitism top-2). "
        "Fitness = −(total pickup distance + battery penalty + coverage penalty). "
        "Compared against a greedy nearest-neighbour baseline every cycle."
    )

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("GA Dispatch Cycles",        ga["total_dispatches"])
    g2.metric("Last Improvement vs Greedy", f"{ga['improvement_pct']} %",
              help="% reduction in total pickup distance vs greedy nearest-neighbour")
    g3.metric("Cumulative Distance Saved",  f"{ga['cumulative_saving']:.1f} units",
              help="Total distance saved across all GA dispatch cycles")
    g4.metric("Simulation Tick",            fleet.tick)

    if ga["convergence"]:
        conv_df = pd.DataFrame({
            "Generation": range(len(ga["convergence"])),
            "Total Pickup Cost (grid units)": ga["convergence"],
        })
        fig_conv = px.line(
            conv_df, x="Generation", y="Total Pickup Cost (grid units)",
            title="GA Convergence — Most Recent Dispatch Cycle",
            labels={"Total Pickup Cost (grid units)": "Cost (lower = better)"},
            color_discrete_sequence=["#d62728"],
        )
        fig_conv.add_hline(
            y=ga["last_greedy_cost"], line_dash="dash", line_color="#7f7f7f",
            annotation_text=f"Greedy baseline  {ga['last_greedy_cost']:.2f}",
            annotation_position="top right",
        )
        fig_conv.update_layout(
            **PLOT_STYLE, height=260,
            xaxis={**GRID_STYLE, "title": "Generation"},
            yaxis={**GRID_STYLE, "title": "Total Pickup Cost (grid units)"},
        )
        st.plotly_chart(fig_conv, use_container_width=True)
    else:
        st.info("GA convergence curve appears here after first multi-request dispatch cycle.")

    st.divider()

    # ── 2. Fleet KPIs ─────────────────────────────────────────────────────────
    st.markdown("### Fleet Status")
    st.caption("Real-time snapshot of all agent states and fleet-level health metrics.")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Available",   m.available if m else 0)
    k2.metric("In Service",  (m.dispatched + m.riding) if m else 0)
    k3.metric("Charging",    m.charging if m else 0)
    k4.metric("Faulted",     m.faulted if m else 0)
    k5.metric("Trips Done",  m.trips_completed if m else 0)
    k6.metric("Avg Battery", f"{m.avg_battery:.0f}%" if m else "—")

    st.divider()

    # ── 3. Fleet Map + State Breakdown + Event Log ────────────────────────────
    st.markdown("### Agent Positions & State")
    st.caption(
        "Each marker is one autonomous vehicle. Shape = state. "
        "Dashed lines show current routes (agent → destination). "
        "Teal squares = charging stations."
    )

    map_col, right_col = st.columns([2, 1])

    with map_col:
        fig_map = go.Figure()

        # Charging stations
        for cs in fleet.city.charging_stations:
            fig_map.add_trace(go.Scatter(
                x=[cs[0]], y=[cs[1]],
                mode="markers",
                marker=dict(symbol="square", size=20, color="#17becf",
                            opacity=0.5, line=dict(width=2, color="#0d6e7a")),
                name="Charging Station",
                showlegend=True,
                hovertemplate=f"Charging Station<br>({cs[0]}, {cs[1]})<extra></extra>",
            ))

        # Route lines (agent → destination)
        for agent in fleet.agents:
            if agent.destination:
                fig_map.add_trace(go.Scatter(
                    x=[agent.position[0], agent.destination[0]],
                    y=[agent.position[1], agent.destination[1]],
                    mode="lines",
                    line=dict(color=STATE_COLORS.get(agent.state.name, "#aaa"),
                              width=1, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

        # Agents by state
        agents_data = fleet.agent_data
        df = pd.DataFrame(agents_data)
        for state in df["state"].unique():
            sub = df[df["state"] == state]
            fig_map.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"],
                mode="markers+text",
                marker=dict(
                    symbol=STATE_SYMBOLS.get(state, "circle"),
                    size=13,
                    color=STATE_COLORS.get(state, "#999"),
                    line=dict(width=1.5, color="#333"),
                ),
                text=sub["agent_id"],
                textposition="top center",
                textfont=dict(size=8, color="#333"),
                name=state.capitalize(),
                customdata=sub[["battery", "rider_id", "trips_completed"]].values,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "State: " + state + "<br>"
                    "Battery: %{customdata[0]:.0f}%<br>"
                    "Rider: %{customdata[1]}<br>"
                    "Trips done: %{customdata[2]}<extra></extra>"
                ),
            ))

        grid_size = fleet.city.size
        fig_map.update_layout(
            **PLOT_STYLE,
            height=500,
            margin=dict(l=40, r=10, t=10, b=40),
            xaxis={**GRID_STYLE, "range": [-0.5, grid_size + 0.5],
                   "title": "X — East (grid units)", "dtick": 5},
            yaxis={**GRID_STYLE, "range": [-0.5, grid_size + 0.5],
                   "title": "Y — North (grid units)", "dtick": 5,
                   "scaleanchor": "x", "scaleratio": 1},
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="left", x=0, bgcolor="rgba(255,255,255,0.8)",
                        bordercolor="#ccc", borderwidth=1),
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with right_col:
        # State breakdown bar
        if m:
            state_df = pd.DataFrame({
                "State":   ["Available", "Dispatched", "Riding", "Charging", "Faulted", "Offline"],
                "Count":   [m.available, m.dispatched, m.riding, m.charging, m.faulted, m.offline],
            })
            color_map = {
                "Available": "#2ca02c", "Dispatched": "#ff7f0e", "Riding": "#1f77b4",
                "Charging":  "#17becf", "Faulted":    "#d62728", "Offline": "#7f7f7f",
            }
            fig_bar = px.bar(
                state_df, x="Count", y="State", orientation="h",
                color="State", color_discrete_map=color_map,
                title="Agent State Breakdown",
            )
            fig_bar.update_layout(
                **PLOT_STYLE, showlegend=False, height=230,
                margin=dict(l=10, r=10, t=45, b=30),
                xaxis={**GRID_STYLE, "title": "# Agents"},
                yaxis=dict(title=""),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Utilisation gauge
        util_pct = (m.fleet_utilization * 100) if m else 0
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(util_pct, 1),
            title={"text": "Fleet Utilisation (%)", "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#555"},
                "bar":  {"color": "#1f77b4"},
                "steps": [
                    {"range": [0,  40], "color": "#fde8e8"},
                    {"range": [40, 70], "color": "#fff3cd"},
                    {"range": [70, 100], "color": "#d4edda"},
                ],
                "threshold": {"line": {"color": "#d62728", "width": 3},
                              "thickness": 0.75, "value": 80},
            },
            number={"suffix": "%"},
        ))
        fig_gauge.update_layout(
            **PLOT_STYLE, height=200,
            margin=dict(l=20, r=20, t=30, b=10),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        # Event log
        st.markdown("**Event Log**")
        events_list = fleet.recent_events[:25]
        event_html = (
            "<div style='height:200px;overflow-y:auto;font-size:10.5px;"
            "font-family:\"Courier New\",monospace;background:#fafafa;"
            "border:1px solid #ddd;border-radius:4px;padding:6px;'>"
        )
        for e in events_list:
            if any(w in e for w in ("FAULT", "OUTAGE", "CASCADE")):
                color = "#d62728"
            elif any(w in e for w in ("DRAIN", "battery", "low battery")):
                color = "#ff7f0e"
            elif any(w in e for w in ("GA dispatch", "improvement")):
                color = "#9467bd"
            elif any(w in e for w in ("completed", "charged", "recovered")):
                color = "#2ca02c"
            else:
                color = "#555555"
            event_html += f'<div style="color:{color};margin:1px 0;line-height:1.4">{e}</div>'
        event_html += "</div>"
        st.markdown(event_html, unsafe_allow_html=True)

    st.divider()

    # ── 4. Historical Time-Series ─────────────────────────────────────────────
    st.markdown("### Simulation History")
    st.caption(
        "Time-series of key fleet metrics. "
        "Spikes in faults or drops in utilisation indicate fault injection events."
    )

    if len(fleet.metrics_history) > 2:
        hist = fleet.metrics_history
        hist_df = pd.DataFrame({
            "Tick":              [x.tick for x in hist],
            "Utilisation (%)":   [x.fleet_utilization * 100 for x in hist],
            "Avg Battery (%)":   [x.avg_battery for x in hist],
            "Faulted Agents":    [x.faulted for x in hist],
            "Trips Completed":   [x.trips_completed for x in hist],
        })

        h1, h2 = st.columns(2)
        with h1:
            fig_u = px.line(
                hist_df, x="Tick", y="Utilisation (%)",
                title="Fleet Utilisation Over Time",
                color_discrete_sequence=["#1f77b4"],
            )
            fig_u.update_layout(**PLOT_STYLE, height=240,
                xaxis={**GRID_STYLE, "title": "Simulation Tick"},
                yaxis={**GRID_STYLE, "title": "Utilisation (%)", "range": [0, 100]})
            st.plotly_chart(fig_u, use_container_width=True)

        with h2:
            fig_b = go.Figure()
            fig_b.add_trace(go.Scatter(
                x=hist_df["Tick"], y=hist_df["Avg Battery (%)"],
                name="Avg Battery (%)", line=dict(color="#2ca02c", width=2),
            ))
            fig_b.add_trace(go.Scatter(
                x=hist_df["Tick"], y=hist_df["Faulted Agents"],
                name="Faulted Agents", line=dict(color="#d62728", width=2),
                yaxis="y2",
            ))
            fig_b.update_layout(
                **PLOT_STYLE, height=240,
                title="Battery Health & Fault Count",
                xaxis={**GRID_STYLE, "title": "Simulation Tick"},
                yaxis={**GRID_STYLE, "title": "Avg Battery (%)", "range": [0, 100]},
                yaxis2=dict(title="Faulted Agents", overlaying="y", side="right",
                            showgrid=False, range=[0, len(fleet.agents)],
                            color="#d62728"),
                legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="#ccc", borderwidth=1),
            )
            st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Historical charts appear after the simulation starts running.")

    # ── Auto-advance: rerun only this fragment, not the full page ─────────────
    if st.session_state.running:
        time.sleep(st.session_state.tick_speed)
        st.rerun(scope="fragment")


live_dashboard()
