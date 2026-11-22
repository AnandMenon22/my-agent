"""QA Test Status Agent for Stakeholders.

Converts raw test execution metrics and QA notes into an executive status report for stakeholders.
"""
import os

import pandas as pd
import streamlit as st

from agent import run, to_markdown
from demo import SECTIONS
from prompts import SYSTEM_PROMPT

st.set_page_config(page_title="QA Test Status Agent for Stakeholders", page_icon="🧪", layout="wide")


def setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets first, then from the environment."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default)).strip()


API_KEY = setting("AI_API_KEY")
BASE_URL = setting("AI_BASE_URL", "https://api.openai.com/v1")
MODEL = setting("AI_MODEL", "gpt-4o-mini")

STATUS_COLOUR = {"Green": "#16a34a", "Amber": "#d97706", "Red": "#dc2626"}
SECTION_ICON = {"Passed": "✅", "Failed": "❌", "Blocked": "⛔", "Risks": "⚠️", "Next Sprint": "📅"}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.8rem; max-width: 1150px;}
      .hero {background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); color: #fff; padding: 22px 26px;
             border-radius: 14px; margin-bottom: 20px;}
      .hero h1 {font-size: 1.75rem; margin: 0 0 6px 0; color: #fff; font-weight: 700;}
      .hero p {margin: 0; opacity: .9; font-size: 1rem;}
      .card {background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;
             box-shadow: 0 1px 3px rgba(0,0,0,.04);}
      .card h4 {margin: 0 0 8px 0; font-size: 1.05rem; font-weight: 600;}
      .item {padding: 7px 0; border-top: 1px dashed #e2e8f0; font-size: .95rem;}
      .item:first-of-type {border-top: none;}
      .tag {display: inline-block; font-size: .75rem; padding: 2px 8px; border-radius: 999px; background: #eef2ff; color: #3730a3;
            margin-left: 6px; font-weight: 500;}
      .status-badge {display: inline-block; color: #fff; font-weight: 700; padding: 6px 16px; border-radius: 999px; font-size: 1rem;}
      .step {color: #0f172a; padding: 8px 12px; border-left: 4px solid #16a34a; background: #f8fafc; margin-bottom: 8px; border-radius: 6px;}
      .step.bad {border-left-color: #d97706;}
      .footer {text-align: center; color: #64748b; font-size: .85rem; margin-top: 36px; padding: 12px 0; border-top: 1px solid #e2e8f0;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Header: Clear title and one-line explainer
st.markdown(
    '<div class="hero">'
    "<h1>🧪 QA Test Status Agent for Stakeholders</h1>"
    "<p>Turn raw test execution numbers and sprint notes into a clear, one-minute executive status report.</p>"
    "</div>",
    unsafe_allow_html=True,
)

if API_KEY:
    st.success(f"Using AI Model ({MODEL}).")
else:
    st.info("Demo mode: simple rule-based sorting active. Add an AI API key in secrets to switch to full AI model.")

SAMPLES = {
    "Sample 1: Standard Sprint (Phoenix CRM)": "samples/sample1.txt",
    "Sample 2: Perfect Sprint (Orion HR Portal)": "samples/sample2.txt",
    "Sample 3: Messy & Typos (Retail App)": "samples/sample3.txt",
    "Sample 4: Short & Minimal (Blaze Analytics)": "samples/sample4.txt",
    "Sample 5: Missing Information (Sprint 5)": "samples/sample5.txt",
}


def read(p: str) -> str:
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


if "updates" not in st.session_state:
    st.session_state.updates = ""

left, right = st.columns([1, 1.3], gap="large")

with left:
    st.subheader("Input QA Notes")
    pick = st.selectbox("Choose a sample input", list(SAMPLES), label_visibility="collapsed")
    col_btn1, col_btn2 = st.columns([1, 1])
    if col_btn1.button("📋 Load sample", use_container_width=True):
        st.session_state.updates = read(SAMPLES[pick])

    up = col_btn2.file_uploader("Upload .txt file", type=["txt", "md"], label_visibility="collapsed")
    if up is not None and st.session_state.get("_uploaded") != up.name:
        st.session_state.updates = up.read().decode("utf-8", errors="ignore")
        st.session_state._uploaded = up.name

    updates = st.text_area(
        "Paste test execution counts and sprint notes",
        key="updates",
        height=320,
        placeholder="e.g.\nTotal test cases planned: 180\nNumber of test cases executed: 180\nPassed: 174\nFailed: 6\n...",
    )
    go = st.button("Generate Stakeholder Report", type="primary", use_container_width=True)

with right:
    st.subheader("Stakeholder Report")

    if go:
        if not updates.strip():
            st.warning("Please paste some test notes first or click 'Load sample'.")
        else:
            with st.spinner("Analyzing test metrics and compiling stakeholder report..."):
                try:
                    result, steps = run(updates, SYSTEM_PROMPT, API_KEY, BASE_URL, MODEL)
                except Exception as err:
                    st.error(f"Could not generate report: {err}")
                    st.stop()
            st.session_state.result, st.session_state.steps = result, steps

    result = st.session_state.get("result")
    steps = st.session_state.get("steps", [])

    if not result:
        st.markdown(
            '<div class="card">'
            "<h4>How to Use</h4>"
            '<div class="item">1. Click <b>Load sample</b> or paste your own QA execution notes.</div>'
            '<div class="item">2. Click <b>Generate Stakeholder Report</b>.</div>'
            '<div class="item">3. Review the status, defect register, sponsor email, and questions.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        items = result.get("items", [])
        count = lambda s: len([i for i in items if i.get("section") == s])
        colour = STATUS_COLOUR.get(result.get("status", ""), "#6b7280")

        # 1. Overall Status Card
        st.markdown(
            f'<div class="card" style="border-left: 6px solid {colour};">'
            f'<span class="status-badge" style="background:{colour};">Status: {result.get("status", "Unknown")}</span>'
            f'&nbsp;&nbsp;<strong>{result.get("status_reason", "")}</strong>'
            "</div>",
            unsafe_allow_html=True,
        )

        # 2. What Matters Most (Headline & Summary)
        if result.get("headline"):
            st.markdown(
                f'<div class="card">'
                f"<h4>What Matters Most</h4>"
                f'<div style="font-size:1.05rem; margin-bottom:8px;">{result["headline"]}</div>'
                f'<div style="color:#475569;"><b>Summary:</b> {result.get("summary", "")}</div>'
                "</div>",
                unsafe_allow_html=True,
            )

        # 3. High-level metric counts
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("✅ Passed", count("Passed"))
        k2.metric("❌ Failed", count("Failed"))
        k3.metric("⛔ Blocked", count("Blocked"))
        k4.metric("❓ Questions", len(result.get("questions", [])))

        # 4. Separated Section Tabs
        tab_report, tab_register, tab_actions, tab_email, tab_questions, tab_steps = st.tabs(
            ["Report", "Defects & Blockers", "Actions & Decisions", "Sponsor Email", "Questions", "Agent Steps"]
        )

        with tab_report:
            for s in SECTIONS:
                rows = [i for i in items if i.get("section") == s]
                body = "".join(
                    f'<div class="item">{i.get("text", "")}'
                    + (f'<span class="tag">👤 {i["owner"]}</span>' if i.get("owner") else "")
                    + (f'<span class="tag">📅 {i["due"]}</span>' if i.get("due") else "")
                    + "</div>"
                    for i in rows
                ) or '<div class="item" style="color:#94a3b8;">Nothing to report.</div>'
                st.markdown(f'<div class="card"><h4>{SECTION_ICON[s]} {s}</h4>{body}</div>', unsafe_allow_html=True)

        with tab_register:
            reg = [i for i in items if i.get("section") in ("Failed", "Blocked", "Risks")]
            if reg:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Type": i["section"],
                            "Impact": i.get("impact") or "Not specified",
                            "Owner": i.get("owner") or "Not assigned",
                            "Due": i.get("due") or "Not specified",
                            "Details": i.get("text", ""),
                        }
                        for i in reg
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.write("No open failures, blockers, or risks reported.")

        with tab_actions:
            st.markdown("**Top Priority Actions**")
            for idx, a in enumerate(result.get("actions", []) or [], 1):
                st.markdown(
                    f'<div class="step"><b>{idx}. {a.get("action", "")}</b><br>'
                    f'<span style="color:#475569">Owner: {a.get("owner") or "Unassigned"} · Reason: {a.get("why", "")}</span></div>',
                    unsafe_allow_html=True,
                )
            if not result.get("actions"):
                st.write("No actions required.")

            st.markdown("**Decisions Required**")
            for dcs in result.get("decisions", []) or ["None this sprint."]:
                st.markdown(f"- {dcs}")

        with tab_email:
            st.text_area("Ready-to-send Sponsor Email", result.get("email", "") or "Not enough information.", height=200)

        with tab_questions:
            for q in result.get("questions", []) or ["No missing information — all items have owners and resolution dates."]:
                st.markdown(f"- {q}")

        with tab_steps:
            for idx, s in enumerate(steps, 1):
                st.markdown(
                    f'<div class="step {"" if s["ok"] else "bad"}"><b>{idx}. {s["name"]}</b> {"✓" if s["ok"] else "!"}<br>'
                    f'<span style="color:#475569">{s["detail"]}</span></div>',
                    unsafe_allow_html=True,
                )

        # Reminder and download button
        st.info("⚠️ Reminder: Please check and verify all test numbers in this report before using it.")
        st.download_button("Download QA Report (.md)", to_markdown(result), file_name="qa-stakeholder-report.md", use_container_width=True)

# Footer: exact requested text
st.markdown('<div class="footer">Built by ANAND at Zero to Live, Future Proof India</div>', unsafe_allow_html=True)
