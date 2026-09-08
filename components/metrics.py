import streamlit as st


def render_kpis(stats: dict) -> None:
    cols = st.columns(4)
    cards = [
        ("Здоровье бренда", f"{stats['health']} / 100", "Понятный сводный показатель"),
        ("Всего отзывов", f"{stats['total']:,}", "Проанализировано за период"),
        ("Негативные", f"{stats['negative']:,}", f"{stats['negative_pct']:.1f}% всех отзывов"),
        ("Критические", f"{stats['critical']:,}", "Требуют внимания руководителя"),
    ]
    for col, (label, value, note) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
                unsafe_allow_html=True,
            )
