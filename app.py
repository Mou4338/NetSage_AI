"""
NetSage AI - Streamlit dashboard
Run with:  streamlit run app.py
"""
import os
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from netsage_core import (
    CATEGORIES, SEVERITIES, DEFAULT_SYSTEM_PROMPT,
    run_rule_checker, suggest_severity, suggest_category, build_user_prompt, extract_json,
)

from google import genai
from google.genai import types

CASE_LOG_PATH = "netsage_case_log.csv"
PROMPT_PATH = "diagnose_prompt.md"

SEV_COLOR = {"Sev1": "#E85D5D", "Sev2": "#F0A857", "Sev3": "#4FD1C5"}
CONF_COLOR = {"high": "#6EE7A8", "medium": "#F0A857", "low": "#E85D5D"}
FEEDBACK_COLOR = {"accepted": "#6EE7A8", "edited": "#F0A857", "rejected": "#E85D5D"}
LAYER_ORDER = ["L7", "L6", "L5", "L4", "L3", "L2", "L1"]
LAYER_NAMES = {"L7": "Application", "L6": "Presentation", "L5": "Session",
               "L4": "Transport", "L3": "Network", "L2": "Data Link", "L1": "Physical", "Other": "Other"}

st.set_page_config(page_title="NetSage AI", page_icon="🛰️", layout="wide")

# ---------- small CSS polish (works with the dark theme in .streamlit/config.toml) ----------
st.markdown("""
<style>
.badge { display:inline-block; padding:2px 10px; border-radius:4px; font-size:12px;
         font-family: monospace; font-weight:700; letter-spacing:.5px; margin-right:6px; }
.osi-row { display:flex; align-items:center; gap:8px; padding:6px 10px; border-radius:6px;
           border:1px solid #22314A; margin-bottom:4px; font-family: monospace; font-size:13px; }
.osi-row.active { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 15%, transparent); }
</style>
""", unsafe_allow_html=True)


def badge(text, color):
    return f'<span class="badge" style="color:{color};background:{color}22;border:1px solid {color}55;">{text}</span>'


def friendly_error_message(exc: Exception) -> str:
    """A calm, formal message for the dashboard — never the raw exception/traceback."""
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text or "quota" in text.lower():
        return ("AI diagnosis is temporarily unavailable — the daily request limit for this API key "
                "has been reached. You can fill in a diagnosis manually below and continue the workflow.")
    return ("AI diagnosis is temporarily unavailable right now. "
            "You can fill in a diagnosis manually below and continue the workflow.")


def blank_diagnosis(category_value: str) -> dict:
    return {
        "osi_layer": "Other", "confidence": "low", "category": category_value,
        "root_cause": "", "evidence": "", "next_command": "", "fix_steps": [],
    }


# ---------- persistence ----------
def load_cases():
    if os.path.exists(CASE_LOG_PATH):
        return pd.read_csv(CASE_LOG_PATH)
    return pd.DataFrame(columns=["timestamp", "symptom", "category", "severity", "osi_layer", "confidence", "root_cause", "feedback"])


def save_case(row: dict):
    df = load_cases()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CASE_LOG_PATH, index=False)
    return df


# make sure the prompt file always exists before anything tries to open() it
if not os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_SYSTEM_PROMPT)

for key, default in {"findings": None, "diagnosis": None, "editing": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default

load_dotenv()

# ---------- sidebar: connection settings ----------
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    try:
        default_api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    except Exception:
        # no .streamlit/secrets.toml on this machine — fall back to .env / blank, don't crash the app
        default_api_key = os.environ.get("GOOGLE_API_KEY", "")

    api_key = st.text_input("Google AI Studio API key", value=default_api_key, type="password")
    model_name = st.text_input("Model", value=os.environ.get("NETSAGE_MODEL", "gemini-3.6-flash"),
                                help="Must match a model name your key can actually call.")

    client = None
    if api_key:
        client = genai.Client(api_key=api_key)

    with st.expander("List models available to this key"):
        if st.button("Fetch model list", disabled=not api_key):
            try:
                names = []
                for m in client.models.list():
                    if "generateContent" in (m.supported_actions or []):
                        names.append(m.name)
                st.session_state["model_list"] = names
            except Exception:
                st.warning("Couldn't reach the model list right now — check your API key and try again shortly.")
        if st.session_state.get("model_list"):
            for n in st.session_state["model_list"]:
                st.code(n, language=None)

    with st.expander("Edit diagnosis system prompt"):
        with open(PROMPT_PATH, "r", encoding="utf-8", errors="replace") as f:
            current_prompt = f.read()
        prompt_text = st.text_area("Diagnosis prompt", value=current_prompt, height=260)
        if st.button("Save prompt"):
            with open(PROMPT_PATH, "w", encoding="utf-8") as f:
                f.write(prompt_text)
            st.success("Saved.")

    st.caption("The API key is only kept in this session — it's not written to disk unless it's already in your .env file.")

st.markdown("## 🛰️ NetSage AI")
st.caption("Cisco Packet Tracer triage assistant — Python rule checker → Gemini diagnosis → human review")

tab_new, tab_dash = st.tabs(["🩺 New Case", "📊 Dashboard"])

# ================= NEW CASE TAB =================
with tab_new:
    left, right = st.columns([1, 1.1], gap="large")

    with left:
        symptom = st.text_area("Symptom", placeholder="e.g. Guest laptop gets an IP but can't reach the file server", height=80)
        topology = st.text_area("Topology note", placeholder="e.g. Access switch SW2 → trunk → core switch SW1 → server VLAN", height=70)
        evidence = st.text_area("Show-command evidence", height=200,
                                 placeholder="Paste 'show ip interface brief' / 'show vlan brief' / 'show interfaces trunk' / 'show running-config' output")

        c1, c2 = st.columns(2)
        with c1:
            suggested_category = suggest_category(symptom, evidence)
            category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(suggested_category))
            st.caption(f"Suggested from symptom/evidence: **{suggested_category}**")
        with c2:
            suggested_severity = suggest_severity(symptom)
            severity = st.selectbox("Severity", SEVERITIES, index=SEVERITIES.index(suggested_severity))
            st.caption(f"Suggested from symptom text: **{suggested_severity}**")

        b1, b2 = st.columns(2)
        run_checker = b1.button("🔍 Run rule checker", use_container_width=True)
        run_ai = b2.button("🤖 Get AI diagnosis", type="primary", use_container_width=True, disabled=not api_key)

        if run_checker:
            st.session_state["findings"] = run_rule_checker(evidence)
            st.session_state["diagnosis"] = None
            st.session_state["editing"] = False

        if run_ai:
            findings = st.session_state["findings"] or run_rule_checker(evidence)
            st.session_state["findings"] = findings
            with st.spinner("Calling Gemini..."):
                try:
                    with open(PROMPT_PATH, "r", encoding="utf-8", errors="replace") as f:
                        system_prompt = f.read()
                    user_prompt = build_user_prompt(symptom, topology, evidence, findings)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=f"{system_prompt}\n\n{user_prompt}",
                        config=types.GenerateContentConfig(max_output_tokens=2000, temperature=0.0),
                    )
                    st.session_state["diagnosis"] = extract_json(response.text)
                    st.session_state["editing"] = False
                except json.JSONDecodeError:
                    print("[NetSage AI] model returned non-JSON response — falling back to manual edit.")
                    st.session_state["diagnosis"] = blank_diagnosis(category)
                    st.session_state["editing"] = True
                    st.info("The AI's response couldn't be read as a diagnosis. Fill one in manually below and continue.")
                except Exception as e:
                    print(f"[NetSage AI] diagnosis error: {e}")
                    st.session_state["diagnosis"] = blank_diagnosis(category)
                    st.session_state["editing"] = True
                    st.warning(friendly_error_message(e))

        if st.session_state["findings"]:
            st.markdown("**Level-0 rule checker findings**")
            for f in st.session_state["findings"]:
                sev_color = {"error": "#E85D5D", "warning": "#F0A857", "info": "#4FD1C5"}[f["severity"]]
                st.markdown(f"{badge(f['layer'], sev_color)} {f['message']}", unsafe_allow_html=True)

    with right:
        diagnosis = st.session_state["diagnosis"]
        if not diagnosis:
            st.info("Run the rule checker, then request an AI diagnosis — results appear here.")
        else:
            osi_col, info_col = st.columns([1, 1.6])
            with osi_col:
                st.markdown("**OSI layer**")
                active = diagnosis.get("osi_layer", "Other")
                color = CONF_COLOR.get(diagnosis.get("confidence", "low"), "#4FD1C5")
                for l in LAYER_ORDER:
                    is_active = (l == active)
                    style = f"border-color:{color};background:{color}22;" if is_active else ""
                    st.markdown(
                        f'<div class="osi-row" style="{style}"><b>{l}</b> {LAYER_NAMES[l]}</div>',
                        unsafe_allow_html=True,
                    )

            with info_col:
                st.markdown(
                    badge(f"{diagnosis.get('confidence','?')} confidence", CONF_COLOR.get(diagnosis.get("confidence"), "#8CA0BE"))
                    + badge(diagnosis.get("category", category), "#4FD1C5"),
                    unsafe_allow_html=True,
                )

                if not st.session_state["editing"]:
                    st.markdown(f"**Root cause:** {diagnosis.get('root_cause','')}")
                    st.markdown(f"**Evidence:** {diagnosis.get('evidence','')}")
                    st.code(diagnosis.get("next_command", ""), language="bash")
                    st.markdown("**Fix steps:**")
                    for i, s in enumerate(diagnosis.get("fix_steps", []), 1):
                        st.markdown(f"{i}. {s}")
                else:
                    diagnosis["root_cause"] = st.text_area("Root cause", diagnosis.get("root_cause", ""), height=70)
                    diagnosis["evidence"] = st.text_area("Evidence", diagnosis.get("evidence", ""), height=60)
                    diagnosis["next_command"] = st.text_input("Next command", diagnosis.get("next_command", ""))
                    fix_text = st.text_area("Fix steps (one per line)", "\n".join(diagnosis.get("fix_steps", [])), height=90)
                    diagnosis["fix_steps"] = [s for s in fix_text.split("\n") if s.strip()]

                fb1, fb2, fb3 = st.columns(3)

                def log_and_reset(feedback):
                    row = {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "symptom": symptom, "category": category, "severity": severity,
                        "osi_layer": diagnosis.get("osi_layer"), "confidence": diagnosis.get("confidence"),
                        "root_cause": diagnosis.get("root_cause"), "feedback": feedback,
                    }
                    save_case(row)
                    st.session_state["findings"] = None
                    st.session_state["diagnosis"] = None
                    st.session_state["editing"] = False
                    st.rerun()

                if not st.session_state["editing"]:
                    if fb1.button("✅ Accept", use_container_width=True):
                        log_and_reset("accepted")
                    if fb2.button("✏️ Edit", use_container_width=True):
                        st.session_state["editing"] = True
                        st.rerun()
                    if fb3.button("❌ Reject", use_container_width=True):
                        log_and_reset("rejected")
                else:
                    if st.button("💾 Save edited diagnosis", type="primary", use_container_width=True):
                        log_and_reset("edited")

# ================= DASHBOARD TAB =================
with tab_dash:
    cases = load_cases()
    if cases.empty:
        st.info("No cases logged yet — resolve a case in the New Case tab first.")
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total cases", len(cases))

        reviewed = cases[cases["feedback"].isin(["accepted", "edited", "rejected"])]
        agreement_rate = round((reviewed["feedback"] == "accepted").mean() * 100) if not reviewed.empty else 0
        m2.metric("AI–Human Agreement", f"{agreement_rate}%")
        m3.metric("Accepted", int((cases["feedback"] == "accepted").sum()))
        m4.metric("Edited", int((cases["feedback"] == "edited").sum()))
        m5.metric("Rejected", int((cases["feedback"] == "rejected").sum()))

        c1, c2, c3 = st.columns(3)
        with c1:
            sev_counts = cases["severity"].value_counts().reindex(SEVERITIES).fillna(0).reset_index()
            sev_counts.columns = ["severity", "count"]
            fig = px.bar(sev_counts, x="severity", y="count", color="severity",
                         color_discrete_map=SEV_COLOR, title="Cases by severity")
            fig.update_layout(showlegend=False, height=320)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            cat_counts = cases["category"].value_counts().reset_index()
            cat_counts.columns = ["category", "count"]
            fig = px.bar(cat_counts, x="count", y="category", orientation="h", title="Cases by category")
            fig.update_traces(marker_color="#4FD1C5")
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)

        with c3:
            fb_counts = cases["feedback"].value_counts().reset_index()
            fb_counts.columns = ["feedback", "count"]
            fig = px.pie(fb_counts, names="feedback", values="count", hole=0.5,
                         color="feedback", color_discrete_map=FEEDBACK_COLOR, title="Feedback breakdown")
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Recent cases**")
        st.dataframe(cases.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)

        st.download_button("⬇️ Download case log (CSV)", cases.to_csv(index=False), file_name="netsage_case_log.csv")
