"""
Robotaxi Fleet Simulation — Scenario Gallery
Run with:  streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

st.set_page_config(
    page_title="Robotaxi Fleet Sim",
    page_icon="🚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Minimal CSS — clean academic look ─────────────────────────────────────────
st.markdown("""
<style>
  .scenario-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px 16px 12px;
    background: #fafafa;
    height: 100%;
  }
  .scenario-title {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 4px;
  }
  .scenario-desc {
    font-size: 12.5px;
    color: #444;
    line-height: 1.5;
    margin-top: 6px;
  }
  .section-header {
    font-size: 20px;
    font-weight: 700;
    color: #1a1a2e;
    border-left: 4px solid #1f77b4;
    padding-left: 10px;
    margin: 24px 0 4px;
  }
  .ga-box {
    background: #f0f4ff;
    border: 1px solid #b8c8f0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 8px;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# Robotaxi Fleet Simulation")
st.markdown(
    "Multi-agent autonomous vehicle fleet on a **20 × 20 city grid**. "
    "Each agent runs a full state machine: `AVAILABLE → DISPATCHED → RIDING → RETURNING → CHARGING → FAULT → OFFLINE`. "
    "A **Genetic Algorithm** optimises every dispatch cycle. "
    "Six adversarial fault scenarios test fleet resilience."
)
st.divider()

# ── GA Hero Section ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Genetic Algorithm Dispatch Optimiser</div>', unsafe_allow_html=True)

st.markdown("""
<div class="ga-box">
<b>Problem:</b> When multiple ride requests arrive simultaneously, naive nearest-neighbour dispatch is suboptimal —
it greedily assigns the closest agent to request 1, then closest remaining to request 2, etc.
With N requests and M agents, the optimal assignment requires searching a combinatorial space.<br><br>
<b>GA solution:</b> Each chromosome is a permutation of agent indices.
Gene <i>i</i> maps request <i>i</i> → agent <code>chromosome[i]</code>.
The fitness function minimises <b>total pickup distance + battery penalty + coverage penalty</b>
(idle agents spread across the grid score better, keeping coverage high).<br><br>
<b>Operators:</b> Order Crossover (OX) preserving permutation validity &nbsp;|&nbsp;
Swap mutation &nbsp;|&nbsp; Tournament selection k=3 &nbsp;|&nbsp; Elitism top-2<br>
<b>Parameters:</b> Population 80, Generations 40 — benchmarks <b>30–40% cost reduction</b> vs greedy.
</div>
""", unsafe_allow_html=True)

# GA GIFs side by side
g1, g2 = st.columns(2)
with g1:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "ga_dispatch.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">GA Dispatch Under Rider Surge</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'Three rider surge events are injected mid-run. Each surge forces the GA to optimally assign '
        '5+ simultaneous requests. Watch the GA improvement % and cumulative distance saved update '
        'in the title as the algorithm finds better assignments than greedy nearest-neighbour.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with g2:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "rider_surge.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">Heavy Surge — GA Under Maximum Load</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'Double surge injections at ticks 20, 55, and 95 flood the queue with 10 simultaneous requests. '
        'The GA must partition available agents across competing pickups, '
        'balancing distance minimisation against battery levels and spatial coverage.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ── Normal Operation ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Baseline Fleet Operation</div>', unsafe_allow_html=True)

n1, n2 = st.columns(2)
with n1:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "normal_operation.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">Normal Fleet Operation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'Baseline run with no fault injection. Agents cycle through the full state machine: '
        'dispatched to a pickup, riding to the dropoff, then returning to a charging station '
        'when battery drops below 20%. Dotted lines show current routes.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with n2:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "battery_drain.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">Battery Drain & Recharge Cycle</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'Battery drain injections hit three random agents at ticks 10, 55, and 100, '
        'dropping them to critical levels. Affected agents immediately break off and route '
        'to the nearest charging station (teal squares), reducing available fleet capacity '
        'until they recover to 95%.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ── Fault Scenarios ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Adversarial Fault Scenarios</div>', unsafe_allow_html=True)

f1, f2 = st.columns(2)
with f1:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "mass_outage.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">Mass Outage & Fleet Recovery</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'At tick 40, a mass outage takes 30–50% of the fleet offline simultaneously — '
        'simulating a coordinated infrastructure failure or software rollback. '
        'At tick 85, the fleet management system brings all agents back online and '
        'the GA immediately re-optimises dispatch assignments.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with f2:
    st.markdown('<div class="scenario-card">', unsafe_allow_html=True)
    st.image(os.path.join(ASSETS, "cascading_fault.gif"), use_container_width=True)
    st.markdown('<div class="scenario-title">Cascading Fault Propagation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="scenario-desc">'
        'A single agent faults at tick 35. Any agent within 3 grid units has a 60% '
        'chance of cascade failure — modelling real-world scenarios like a shared '
        'sensor firmware bug or a localised infrastructure fault. '
        'Agents recover probabilistically (3% chance per tick) without intervention.'
        '</div>', unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px; padding: 16px 0;'>"
    "Built with Python · Simulation core: FSM agent state machines · "
    "Optimiser: Genetic Algorithm (OX crossover, swap mutation, tournament selection) · "
    "Data pipeline: SQLite · Visualisation: Matplotlib + Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
