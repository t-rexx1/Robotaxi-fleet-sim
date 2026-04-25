"""
Robotaxi Fleet Simulation — Streamlit Dashboard

Run with:  streamlit run dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

from simulation.fleet_manager import FleetManager
from simulation.fault_injector import SCENARIOS

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Robotaxi Fleet Sim",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ─────────────────────────────────────────────
APP_VERSION = "2"  # bump this to force a session reset after major updates

if st.session_state.get("_version") != APP_VERSION:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["_version"] = APP_VERSION

if "fleet" not in st.session_state:
    st.session_state.fleet = FleetManager(num_agents=15, grid_size=20)
if "running" not in st.session_state:
    st.session_state.running = False
if "tick_speed" not in st.session_state:
    st.session_state.tick_speed = 0.3

fleet: FleetManager = st.session_state.fleet

# ── Sidebar controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚖 Fleet Control")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start", use_container_width=True, type="primary"):
            st.session_state.running = True
    with col2:
        if st.button("⏸ Pause", use_container_width=True):
            st.session_state.running = False

    if st.button("↺ Reset Simulation", use_container_width=True):
        fleet.logger.clear()
        st.session_state.fleet = FleetManager(num_agents=15, grid_size=20)
        st.session_state.running = False
        st.rerun()

    st.divider()
    st.subheader("⚡ Fault Injection")
    selected_scenario = st.selectbox(
        "Scenario",
        options=list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k],
    )
    if st.button("Inject Fault", use_container_width=True, type="secondary"):
        events = fleet.inject_fault(selected_scenario)
        st.toast(f"Injected: {selected_scenario}", icon="⚡")

    if st.button("Bring All Online", use_container_width=True):
        fleet.bring_agents_online()

    st.divider()
    st.subheader("⚙ Settings")
    num_agents = st.slider("Fleet size", 5, 30, 15)
    tick_speed = st.slider("Tick speed (s)", 0.05, 1.0, 0.3, step=0.05)
    st.session_state.tick_speed = tick_speed

    if st.button("Apply fleet size", use_container_width=True):
        fleet.logger.clear()
        st.session_state.fleet = FleetManager(num_agents=num_agents, grid_size=20)
        st.session_state.running = False
        st.rerun()

    st.divider()
    st.caption("Tick: " + str(fleet.tick))

# ── Main layout ───────────────────────────────────────────────────────────────
st.title("🚖 Robotaxi Fleet Simulation Dashboard")

# KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)
m = fleet.metrics_history[-1] if fleet.metrics_history else None
k1.metric("Available", m.available if m else 0)
k2.metric("Riding", (m.dispatched + m.riding) if m else 0)
k3.metric("Charging", m.charging if m else 0)
k4.metric("Faulted", m.faulted if m else 0, delta=None)
k5.metric("Trips Done", m.trips_completed if m else 0)
k6.metric("Avg Battery", f"{m.avg_battery:.0f}%" if m else "—")

st.divider()

left, right = st.columns([2, 1])

# ── City grid map ─────────────────────────────────────────────────────────────
with left:
    st.subheader("Fleet Map")
    agents_data = fleet.agent_data
    df_agents = pd.DataFrame(agents_data)

    fig = go.Figure()

    # Charging stations
    for cs in fleet.city.charging_stations:
        fig.add_trace(go.Scatter(
            x=[cs[0]], y=[cs[1]],
            mode="markers+text",
            marker=dict(symbol="square", size=18, color="#1abc9c", opacity=0.7),
            text=["⚡"], textposition="middle center",
            name="Charging Station",
            showlegend=False,
        ))

    # Agents by state
    STATE_SYMBOLS = {
        "AVAILABLE": "circle",
        "DISPATCHED": "triangle-up",
        "RIDING": "diamond",
        "RETURNING": "triangle-down",
        "CHARGING": "square",
        "FAULT": "x",
        "OFFLINE": "circle-open",
        "IDLE": "circle-open",
    }
    STATE_COLORS = {
        "AVAILABLE": "#2ecc71",
        "DISPATCHED": "#f39c12",
        "RIDING": "#3498db",
        "RETURNING": "#9b59b6",
        "CHARGING": "#1abc9c",
        "FAULT": "#e74c3c",
        "OFFLINE": "#7f8c8d",
        "IDLE": "#bdc3c7",
    }

    for state in df_agents["state"].unique():
        sub = df_agents[df_agents["state"] == state]
        fig.add_trace(go.Scatter(
            x=sub["x"], y=sub["y"],
            mode="markers+text",
            marker=dict(
                symbol=STATE_SYMBOLS.get(state, "circle"),
                size=14,
                color=STATE_COLORS.get(state, "#fff"),
                line=dict(width=1, color="#222"),
            ),
            text=sub["agent_id"],
            textposition="top center",
            textfont=dict(size=8),
            name=state,
            customdata=sub[["battery", "rider_id", "trips_completed"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Battery: %{customdata[0]:.0f}%<br>"
                "Rider: %{customdata[1]}<br>"
                "Trips: %{customdata[2]}<extra></extra>"
            ),
        ))

    fig.update_layout(
        xaxis=dict(range=[-0.5, fleet.city.size + 0.5], showgrid=True, gridcolor="#2a2a2a"),
        yaxis=dict(range=[-0.5, fleet.city.size + 0.5], showgrid=True, gridcolor="#2a2a2a"),
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        font=dict(color="#eeeeee"),
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Right panel: metrics + events ────────────────────────────────────────────
with right:
    st.subheader("Fleet State Breakdown")
    if m:
        state_df = pd.DataFrame({
            "State": ["Available", "Dispatched", "Riding", "Charging", "Faulted", "Offline"],
            "Count": [m.available, m.dispatched, m.riding, m.charging, m.faulted, m.offline],
            "Color": ["#2ecc71", "#f39c12", "#3498db", "#1abc9c", "#e74c3c", "#7f8c8d"],
        })
        fig_bar = px.bar(
            state_df, x="Count", y="State", orientation="h",
            color="State",
            color_discrete_map={row["State"]: row["Color"] for _, row in state_df.iterrows()},
        )
        fig_bar.update_layout(
            showlegend=False, height=220,
            plot_bgcolor="#111111", paper_bgcolor="#111111",
            font=dict(color="#eeeeee"),
            margin=dict(l=0, r=10, t=0, b=0),
            xaxis=dict(showgrid=True, gridcolor="#2a2a2a"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Event Log")
    events_list = fleet.recent_events[:30]
    event_html = "<div style='height:260px;overflow-y:auto;font-size:11px;font-family:monospace;'>"
    for e in events_list:
        color = "#e74c3c" if "FAULT" in e or "OUTAGE" in e or "CASCADE" in e else \
                "#f39c12" if "DRAIN" in e or "battery" in e.lower() else \
                "#2ecc71" if "completed" in e or "charged" in e else "#aaaaaa"
        event_html += f'<p style="color:{color};margin:2px 0">{e}</p>'
    event_html += "</div>"
    st.markdown(event_html, unsafe_allow_html=True)

# ── Historical metrics charts ─────────────────────────────────────────────────
st.divider()
st.subheader("Historical Metrics")

if len(fleet.metrics_history) > 2:
    hist_df = pd.DataFrame([
        {
            "tick": m.tick,
            "utilization": m.fleet_utilization * 100,
            "avg_battery": m.avg_battery,
            "faulted": m.faulted,
            "trips": m.trips_completed,
        }
        for m in fleet.metrics_history
    ])

    c1, c2 = st.columns(2)
    with c1:
        fig_util = px.line(
            hist_df, x="tick", y="utilization",
            title="Fleet Utilization (%)",
            color_discrete_sequence=["#3498db"],
        )
        fig_util.update_layout(
            plot_bgcolor="#111111", paper_bgcolor="#111111",
            font=dict(color="#eeeeee"), height=250,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_util, use_container_width=True)

    with c2:
        fig_bat = px.line(
            hist_df, x="tick",
            y=["avg_battery", "faulted"],
            title="Avg Battery & Faults Over Time",
            labels={"avg_battery": "Avg Battery (%)", "faulted": "Faulted Agents", "value": ""},
            color_discrete_sequence=["#2ecc71", "#e74c3c"],
        )
        fig_bat.update_layout(
            plot_bgcolor="#111111", paper_bgcolor="#111111",
            font=dict(color="#eeeeee"), height=250,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_bat, use_container_width=True)
else:
    st.info("Start the simulation to see historical metrics.")

# ── GA Optimiser Panel ────────────────────────────────────────────────────────
st.divider()
st.subheader("GA Dispatch Optimiser")
st.caption(
    "Each dispatch cycle with 2+ requests runs a Genetic Algorithm "
    "(OX crossover, swap mutation, tournament selection, elitism) to find "
    "the optimal agent→request assignment. Fitness = −(pickup distance + "
    "battery penalty + coverage penalty)."
)

ga = fleet.ga_stats
g1, g2, g3, g4 = st.columns(4)
g1.metric("Total GA Dispatches", ga["total_dispatches"])
g2.metric("Last Improvement vs Greedy", f"{ga['improvement_pct']}%")
g3.metric("Last GA Cost", f"{ga['last_ga_cost']:.2f}")
g4.metric("Cumulative Distance Saved", f"{ga['cumulative_saving']:.1f} units")

if ga["convergence"]:
    conv_df = pd.DataFrame({
        "Generation": list(range(len(ga["convergence"]))),
        "Best Cost": ga["convergence"],
    })
    fig_conv = px.line(
        conv_df, x="Generation", y="Best Cost",
        title="GA Convergence — Last Dispatch (cost falling = improving)",
        color_discrete_sequence=["#f39c12"],
    )
    fig_conv.update_layout(
        plot_bgcolor="#111111", paper_bgcolor="#111111",
        font=dict(color="#eeeeee"), height=220,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig_conv, use_container_width=True)
else:
    st.info("GA convergence curve appears here after first multi-request dispatch.")

# ── Auto-advance simulation ───────────────────────────────────────────────────
if st.session_state.running:
    fleet.step()
    time.sleep(st.session_state.tick_speed)
    st.rerun()
