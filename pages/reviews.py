import pandas as pd
import streamlit as st

from services.analytics_service import CATEGORY_LABELS


def _choices(df, column):
    return sorted(x for x in df[column].dropna().astype(str).unique() if x)


def render(df):
    st.title("Все отзывы")
    st.caption("Поиск по реальным отзывам и сохранённым результатам AI-анализа.")
    if df.empty:
        st.info("No reviews match the selected filters.")
        return
    query = st.text_input("Search reviews", placeholder="Search author, review, summary…")
    c1, c2, c3 = st.columns(3)
    sentiments = c1.multiselect("Sentiment", _choices(df, "sentiment"))
    categories = c2.multiselect("Category", _choices(df, "category"), format_func=lambda x: CATEGORY_LABELS.get(x, x))
    severities = c3.multiselect("Severity", _choices(df, "severity"))
    statuses = st.multiselect("Action status", _choices(df, "action_status"))
    view = df.copy()
    if query:
        haystack = view[["author", "review_text", "summary"]].fillna("").agg(" ".join, axis=1)
        view = view[haystack.str.contains(query, case=False, regex=False)]
    if sentiments: view = view[view["sentiment"].isin(sentiments)]
    if categories: view = view[view["category"].isin(categories)]
    if severities: view = view[view["severity"].isin(severities)]
    if statuses: view = view[view["action_status"].isin(statuses)]
    table = view.assign(
        Date=view["published_at"].dt.strftime("%Y-%m-%d"),
        Category=view["category"].map(CATEGORY_LABELS),
    )[["Date", "source", "rating", "sentiment", "Category", "risk_score", "severity", "action_status"]]
    table.columns = ["Date", "Source", "Rating", "Sentiment", "Category", "Risk Score", "Severity", "Status"]
    st.dataframe(table, hide_index=True, width="stretch", height=min(560, 38 + len(table) * 35))
    st.caption(f"{len(view)} reviews")
    for _, row in view.sort_values("published_at", ascending=False).iterrows():
        rating = f"{int(row.rating)}/5" if int(row.rating) > 0 else "Без оценки"
        title = f"{row.source} · {row.author} · {rating} · {row.published_at.strftime('%d.%m.%Y') if pd.notna(row.published_at) else 'Нет даты'}"
        with st.expander(title):
            st.markdown(f"**Original review**  \n{row.review_text}")
            if row.analysis_status == "done":
                st.markdown(f"**AI summary**  \n{row.summary}")
                st.markdown(f"**Recommendation**  \n{row.recommendation}")
                st.info(row.suggested_response)
            else:
                st.warning("AI analysis temporarily unavailable.")
