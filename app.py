from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from database.db import init_db
from repositories.history_repository import HistoryRepository
from services.reminder_service import ReminderService
from utils.ui import disclaimer, feature_card, load_css, metric_card


st.set_page_config(page_title="MediExplain AI", page_icon="+", layout="wide")
init_db()
load_css()

history = HistoryRepository().list()

st.markdown(
    """
    <section class="hero">
      <h1>MediExplain AI</h1>
      <p>AI-powered prescription, lab report, medicine, and medical terminology explanations for safer patient understanding.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

disclaimer()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Uploads", str(len(history)), "Offline history records")
with col2:
    metric_card("Medicines", str(sum(len(item.payload.get("medicines", [])) for item in history)), "Detected medicine entries")
with col3:
    metric_card("Reports", str(sum(1 for item in history if item.record_type == "Lab Report")), "Analyzed lab reports")
with col4:
    metric_card("AI Reviews", str(sum(1 for item in history if item.ai_summary)), "Generated explanations")

st.subheader("Clinical Workspace")
cards = st.columns(3)
features = [
    ("Scan Prescription", "Upload images or PDFs, run OCR, correct handwriting errors, and explain medicines.", "+"),
    ("Upload Lab Report", "Extract values, compare with general ranges, and prepare doctor questions.", "+"),
    ("Medicine Explainer", "Understand purpose, food timing, side effects, safety warnings, and missed dose guidance.", "+"),
    ("Medical Dictionary", "Translate difficult terms into plain English with examples and warning signs.", "+"),
    ("AI Health Chat", "Ask educational questions with visible safety boundaries and exportable chat history.", "+"),
    ("Previous Reports", "Search, filter, reopen, export, or delete locally stored analyses.", "+"),
]
for index, feature in enumerate(features):
    with cards[index % 3]:
        feature_card(*feature)

st.subheader("Usage Snapshot")
if history:
    df = pd.DataFrame([{"type": h.record_type, "date": h.created_at.date()} for h in history])
    fig = px.histogram(df, x="date", color="type", title="Recent activity")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No activity yet. Start with the Prescription Scanner or Lab Report Analyzer.")

st.subheader("Medicine Reminders")
with st.form("reminder_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    medicine = c1.text_input("Medicine")
    dosage = c2.text_input("Dosage")
    reminder_time = c3.time_input("Time")
    days = st.multiselect("Days", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=["Mon"])
    submitted = st.form_submit_button("Add reminder")
    if submitted and medicine and dosage:
        ReminderService().add(medicine, dosage, days, reminder_time.strftime("%H:%M"))
        st.success("Reminder saved locally.")

for reminder in ReminderService().upcoming()[:5]:
    st.caption(f"{reminder.reminder_time} - {reminder.medicine_name} ({reminder.dosage}) on {reminder.days}")
