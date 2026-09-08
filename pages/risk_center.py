import streamlit as st

from components.review_card import render_risk_card


def render(df, writable: bool):
    st.title("Отзывы, требующие внимания")
    st.caption("AI предлагает действия, но окончательное решение всегда принимает человек.")
    risk = df[(df["sentiment"] == "negative") | (df["severity"].isin(["high", "critical"]))]
    risk = risk.sort_values(["risk_score", "published_at"], ascending=False)
    if risk.empty:
        st.success("Рискованных отзывов по выбранным фильтрам нет.")
        return
    if not writable:
        st.info("В демонстрационном режиме решения не сохраняются. Подключите Supabase.")
    severity = st.multiselect("Уровень риска", ["critical", "high", "medium", "low"], default=["critical", "high"])
    if severity:
        risk = risk[risk["severity"].isin(severity)]
    st.caption(f"Показано обращений: {len(risk)} · сначала самые рискованные")
    for _, row in risk.iterrows():
        render_risk_card(row, writable)
