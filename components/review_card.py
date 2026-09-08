from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from services.analytics_service import CATEGORY_LABELS, risk_factors
from services.supabase_service import DataServiceError, update_action_status


def _value(value, fallback="AI analysis temporarily unavailable.") -> str:
    return fallback if pd.isna(value) or str(value).strip() == "" else str(value)


def render_risk_card(row: pd.Series, writable: bool) -> None:
    severity = str(row.get("severity", "high")).upper()
    date = row["published_at"].strftime("%d.%m.%Y, %H:%M") if pd.notna(row["published_at"]) else "Дата неизвестна"
    rating = f"Оценка {int(row.rating)}/5" if int(row.rating) > 0 else "Без оценки"
    category = CATEGORY_LABELS.get(row.get("category"), "Other")
    st.markdown(
        f'<div class="risk-head"><span class="severity {severity.lower()}">{severity} RISK</span>'
        f'<span>{html.escape(str(row.source))} · {date} · {rating}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"> {_value(row.review_text, 'Original review unavailable.')}")
    left, right = st.columns([1, 2])
    with left:
        st.metric("Risk Score", f"{int(row.risk_score)} / 100")
        st.caption("Triage indicator — not a scientifically validated probability.")
        st.write(f"**Category:** {category}")
        st.write(f"**Factors:** {', '.join(risk_factors(row))}")
    with right:
        st.write("**AI Summary**")
        st.write(_value(row.get("summary")))
        st.write("**Recommended Action**")
        st.write(_value(row.get("recommendation")))
        st.write("**Suggested Public Response**")
        st.info(_value(row.get("suggested_response")))
    status = str(row.get("action_status", "pending_review"))
    st.caption(f"Human decision: **{status.replace('_', ' ').title()}**")
    cols = st.columns([1, 1, 1, 4])
    actions = [("Approve", "approved"), ("Reject", "rejected"), ("Mark Resolved", "resolved")]
    for col, (label, new_status) in zip(cols, actions):
        if col.button(label, key=f"{new_status}-{row.id}", disabled=not writable or status == new_status):
            try:
                update_action_status(str(row.id), new_status)
                st.cache_data.clear()
                st.rerun()
            except DataServiceError as exc:
                st.error(str(exc))
    st.divider()
