"""FDE Metrics Dashboard — password-protected pilot KPI tracking."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from utils.metrics import get_summary

ROOT = Path(__file__).parent.parent.parent
CORR_LOG = ROOT / "data" / "correction_log.csv"
PREP_LOG  = ROOT / "data" / "prep_time_log.csv"
TOTAL_MEETINGS   = 14
PREP_BASELINE_MIN = 120

# ── Auth gate ─────────────────────────────────────────────────────────────────

if "fde_authenticated" not in st.session_state:
    st.session_state.fde_authenticated = False

if not st.session_state.fde_authenticated:
    st.title("🔒 FDE Access")
    st.caption("This dashboard is for internal pilot tracking only.")
    pwd = st.text_input("Password", type="password", placeholder="Enter FDE password")
    if pwd:
        correct = os.environ.get("FDE_METRICS_PASSWORD", "")
        if pwd == correct:
            st.session_state.fde_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Authenticated view ────────────────────────────────────────────────────────

col_title, col_lock = st.columns([5, 1])
with col_title:
    st.title("FDE Metrics Dashboard")
    st.caption(
        "Tracks the three KPIs from the pilot proposal. "
        "Data sources: metrics.db · prep_time_log.csv · correction_log.csv"
    )
with col_lock:
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    if st.button("🔒 Lock", use_container_width=True):
        st.session_state.fde_authenticated = False
        st.rerun()

st.divider()

summary = get_summary()

# ── Compute KPIs ──────────────────────────────────────────────────────────────

adoption_count = summary.get("unique_meetings", 0)
adoption_rate  = round(adoption_count / TOTAL_MEETINGS * 100) if TOTAL_MEETINGS else 0

if PREP_LOG.exists():
    df_prep = pd.read_csv(PREP_LOG)
    sessions_logged = len(df_prep)
    avg_prep_min    = round(df_prep["prep_minutes"].mean(), 1) if sessions_logged else None
    time_saved_min  = round(PREP_BASELINE_MIN - avg_prep_min, 1) if avg_prep_min is not None else None
    pct_saved       = round(time_saved_min / PREP_BASELINE_MIN * 100) if time_saved_min is not None else None
else:
    df_prep = pd.DataFrame()
    sessions_logged = avg_prep_min = time_saved_min = pct_saved = None

if CORR_LOG.exists():
    df_corr = pd.read_csv(CORR_LOG)
    df_corr["flagged"] = df_corr["flagged"].astype(str).str.lower() == "true"
    flagged   = df_corr[df_corr["flagged"]]
    corr_rate = round(len(flagged) / len(df_corr) * 100, 1) if len(df_corr) else 0
else:
    df_corr   = pd.DataFrame()
    flagged   = pd.DataFrame()
    corr_rate = None

# ── 3 KPI headline tiles ──────────────────────────────────────────────────────

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown("**KPI 1 — Prep Time Saved**")
    st.caption(f"Baseline: {PREP_BASELINE_MIN} min manual prep · {sessions_logged or 0} sessions logged")
    if time_saved_min is not None:
        st.metric("Time saved per session", f"{time_saved_min} min", delta=f"{pct_saved}% reduction")
        st.caption(f"Avg with tool: {avg_prep_min} min")
    else:
        st.metric("Time saved per session", "—")
        st.caption("No sessions logged yet — click 'Ready for meeting' in Meeting Prep to record.")
with k2:
    st.markdown("**KPI 2 — Adoption Rate**")
    st.caption(f"Packets generated / total upcoming meetings ({TOTAL_MEETINGS})")
    st.metric("Adoption rate", f"{adoption_rate}%", delta=f"{adoption_count}/{TOTAL_MEETINGS} meetings")
with k3:
    st.markdown("**KPI 3 — AI Correction Rate**")
    st.caption("Fields flagged as incorrect by PM / total fields presented")
    if corr_rate is not None:
        st.metric("Correction rate", f"{corr_rate}%",
                  delta=f"{len(flagged)} of {len(df_corr)} fields flagged",
                  delta_color="inverse")
    else:
        st.metric("Correction rate", "—")
        st.caption("No corrections logged yet — use Field Corrections panel in Meeting Prep.")

st.divider()

# ── Detail tabs ───────────────────────────────────────────────────────────────

tab_prep, tab_adopt, tab_corr_detail = st.tabs([
    "Prep Time Detail", "Adoption Detail", "Correction Detail"
])

with tab_prep:
    if not df_prep.empty:
        st.markdown(f"**{sessions_logged} sessions logged**  ·  baseline {PREP_BASELINE_MIN} min")
        cols_show = [c for c in ["timestamp", "supplier_name", "prep_minutes", "advance_hours", "opened_24h_before", "interactions"] if c in df_prep.columns]
        st.dataframe(
            df_prep[cols_show].rename(columns={
                "timestamp": "Timestamp", "supplier_name": "Supplier",
                "prep_minutes": "Prep (min)", "advance_hours": "Hrs before meeting",
                "opened_24h_before": "24h+ advance", "interactions": "Interactions",
            }),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info(
            "No prep-time sessions logged yet.  \n"
            "Open a packet in Meeting Prep and click **✅ Ready for meeting** when done."
        )

with tab_adopt:
    st.markdown(f"**{adoption_count} of {TOTAL_MEETINGS} meetings** have a prep packet generated.")
    if summary["total_packets"]:
        st.caption(
            f"Unique suppliers queried: {summary['unique_suppliers']}  ·  "
            f"Avg generation time: {summary['avg_duration_sec']}s"
        )
        if summary["recent_events"]:
            df_ev = pd.DataFrame(summary["recent_events"])
            df_ev["timestamp"] = df_ev["timestamp"].str.replace("T", " ")
            st.markdown("**Last 10 generation events**")
            st.dataframe(df_ev, hide_index=True, use_container_width=True)
    else:
        st.info("No generation events in metrics.db yet.")

with tab_corr_detail:
    if not df_corr.empty:
        col_f, col_s = st.columns(2)
        with col_f:
            st.markdown("**By field — which AI extractions get flagged most**")
            if not flagged.empty:
                fc = flagged["field_label"].value_counts().reset_index()
                fc.columns = ["Field", "Times Flagged"]
                st.dataframe(fc, hide_index=True, use_container_width=True)
            else:
                st.caption("No flags yet.")
        with col_s:
            st.markdown("**By supplier — where extraction noise is highest**")
            if not flagged.empty:
                sc = flagged["supplier_name"].value_counts().reset_index()
                sc.columns = ["Supplier", "Times Flagged"]
                st.dataframe(sc, hide_index=True, use_container_width=True)
            else:
                st.caption("No flags yet.")
        if not flagged.empty:
            st.divider()
            st.markdown("**Full correction log**")
            df_show = flagged[["timestamp", "supplier_name", "field_label", "meeting_id"]].copy()
            df_show.columns = ["Timestamp", "Supplier", "Field Flagged", "Meeting #"]
            st.dataframe(df_show.sort_values("Timestamp", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.info(
            "No corrections logged yet.  \n"
            "Open a packet in Meeting Prep, flag any wrong fields in the **Field Corrections** panel, "
            "then click **Save corrections**."
        )
