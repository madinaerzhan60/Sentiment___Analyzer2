import streamlit as st

from components.charts import issues_chart, platform_chart, sentiment_chart, trend_chart
from services.analytics_service import issue_platform_matrix, key_findings, platform_stats


def render(df):
    st.title("Подробная аналитика")
    st.caption("Как меняются отзывы, где больше негатива и на что жалуются клиенты.")
    if df.empty:
        st.info("По выбранным фильтрам отзывов нет.")
        return
    st.subheader("Динамика отзывов")
    st.plotly_chart(trend_chart(df), width="stretch")
    left, right = st.columns(2)
    with left:
        st.subheader("Количество по площадкам")
        st.plotly_chart(platform_chart(df), width="stretch")
        stats = platform_stats(df).copy()
        if not stats.empty:
            stats["negative_pct"] = stats["negative_pct"].map(lambda x: f"{x:.1f}%")
            st.dataframe(stats.rename(columns={"source": "Platform", "reviews": "Reviews", "negative_pct": "Negative"}), hide_index=True, width="stretch")
    with right:
        st.subheader("Тональность")
        st.plotly_chart(sentiment_chart(df), width="stretch")
    st.subheader("Главные проблемы клиентов")
    st.plotly_chart(issues_chart(df), width="stretch")
    st.subheader("Какие проблемы встречаются на каждой площадке")
    matrix = issue_platform_matrix(df)
    if matrix.empty:
        st.info("За этот период нет негативных отзывов для анализа.")
    else:
        st.dataframe(matrix.style.background_gradient(cmap="YlOrBr", axis=None), width="stretch")
    st.subheader("Главные выводы")
    for finding in key_findings(df):
        st.markdown(f"- {finding}")
