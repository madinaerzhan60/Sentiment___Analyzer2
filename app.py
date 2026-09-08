from __future__ import annotations

import html
import json
import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.ai_service import AnalysisUnavailable, analyze_review
from services.analytics_service import CATEGORY_LABELS, brand_health_score
from services.import_service import ImportServiceError, collect_2gis, collect_facebook, collect_instagram, save_collected
from services.pipeline_service import analyze_pending
from services.supabase_service import DataServiceError, fetch_reviews, insert_reviews, normalize_reviews
from utils.config import settings

st.set_page_config(page_title="Sentiment Analyzer · GRATA International", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root{--navy:#070E36;--blue:#4E81EE;--blue-light:#4E81EE;--blue-soft:#EAF1FF;--ink:#070E36;--muted:#5B6478;--line:#E0E0E0;--critical:#D5473F;--warning:#D69A2D;--stable:#2E9E63}
html,body,[class*="css"],.stApp{font-family:'Plus Jakarta Sans',sans-serif}.stApp{background:#FFF;color:var(--ink)}[data-testid="stHeader"]{background:rgba(255,255,255,.94);border-bottom:1px solid #F0F1F4}
[data-testid="stSidebar"]{background:var(--navy);border-right:0}[data-testid="stSidebar"] *{color:#EDF1FF}[data-testid="stSidebar"] [data-baseweb="select"]>div,[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea{background:#111A4A;border:1px solid rgba(255,255,255,.16);border-radius:5px}[data-testid="stSidebar"] .stButton button{border-radius:999px!important;background:transparent!important;color:#FFF!important;border:1.5px solid rgba(255,255,255,.8)!important;box-shadow:none!important}[data-testid="stSidebar"] .stButton button:hover{background:#142052!important;border-color:#4E81EE!important;color:#FFF!important}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.25rem}[data-testid="stSidebar"] [role="radiogroup"] label{padding:.65rem .75rem;border-radius:7px;transition:.15s;background:transparent}[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#111A4A}[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#142052;color:#FFF}[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:#7EA4F5!important;font-weight:700}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:4rem}h1,h2,h3,p,label,.stMarkdown{color:var(--ink)}h1{letter-spacing:-.035em;font-size:2.45rem!important;font-weight:800!important;margin-bottom:.15rem!important;color:var(--navy)!important}
.brand{color:#FFF;font-size:1.18rem;font-weight:800;letter-spacing:-.02em;display:flex;align-items:center}.brand-mark{width:34px;height:34px;border:2px solid #FFF;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:#FFF;margin-right:.65rem;font-size:0}.brand-mark:after{content:'G';font-size:14px;font-weight:800}.brand-sub{color:#929AB8;font-size:.62rem;letter-spacing:.18em;margin:.15rem 0 1.6rem;padding-left:2.95rem}.company-line{color:var(--muted);font-size:.88rem;margin-bottom:1.35rem}.live-dot{width:7px;height:7px;display:inline-block;border-radius:50%;background:var(--stable);margin-right:7px}.fallback-dot{background:var(--warning)}
.metric-card{background:#FFF;border:1px solid var(--line);border-radius:9px;padding:1.25rem 1.4rem;min-height:138px;text-align:left;box-shadow:0 1px 2px rgba(7,14,54,.04);transition:border-color .18s ease}.metric-card:hover{border-color:#B9C9EA}.metric-card.alert{border-left:3px solid var(--critical)}.metric-card.good{border-left:3px solid var(--stable)}.metric-label{color:var(--muted);font-size:.7rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase}.metric-value{color:var(--navy);font-size:2.15rem;line-height:1.2;font-weight:800;margin:.5rem 0 .25rem}.metric-note{color:var(--muted);font-size:.78rem}.section-label{color:var(--blue);font-size:.7rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin:1.9rem 0 .65rem}
.overview-note{background:#F2FAF6;border:1px solid #CBE8D8;border-left:3px solid var(--stable);border-radius:8px;padding:.8rem 1rem;color:#226F49;font-size:.87rem;margin:.9rem 0 1.1rem}.overview-note.attention{background:#FFF9ED;border-color:#F0D9A6;border-left-color:var(--warning);color:#8A641B}.signal-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem;margin:.85rem 0 1.1rem}.signal-item{background:#FFF;border:1px solid var(--line);border-radius:8px;padding:.9rem 1rem;box-shadow:0 1px 2px rgba(7,14,54,.04)}.signal-number{color:var(--navy);font-size:1.35rem;font-weight:800}.signal-label{color:var(--muted);font-size:.75rem;margin-top:.15rem}.empty-panel{background:#F2FAF6;border:1px solid #CBE8D8;border-radius:8px;padding:1.15rem;color:#226F49;min-height:110px;display:flex;align-items:center}.registry-help{color:var(--muted);font-size:.82rem;margin-bottom:.75rem}
.chart-heading{color:var(--navy);font-size:.96rem;font-weight:700;margin:.2rem 0 .65rem}.chart-sub{color:var(--muted);font-size:.78rem;margin-top:-.5rem;margin-bottom:.35rem}
.page-kicker{color:var(--blue);font-size:.69rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase;margin-bottom:.35rem}.page-subtitle{color:var(--muted);font-size:.88rem;margin:.15rem 0 1.35rem}.source-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin:1rem 0}.source-card{background:#FFF;border:1px solid var(--line);border-radius:9px;padding:1.05rem;min-height:135px}.source-icon{width:34px;height:34px;border-radius:8px;background:#EAF1FF;color:var(--blue);display:flex;align-items:center;justify-content:center;font-weight:800;margin-bottom:.8rem}.source-name{color:var(--navy);font-weight:750;font-size:.91rem}.source-status{color:var(--stable);font-size:.75rem;margin:.25rem 0 .65rem}.source-status.off{color:var(--muted)}.source-count{color:var(--muted);font-size:.78rem}.connection-panel{background:var(--navy);border-radius:9px;padding:1.2rem 1.3rem;color:#FFF}.connection-panel strong{color:#FFF}.connection-panel p{color:#AEB6D2;font-size:.8rem;margin:.25rem 0}.insight-strip{background:#F5F8FF;border:1px solid #D9E4FA;border-left:3px solid var(--blue);border-radius:8px;padding:1rem 1.1rem;margin:1rem 0;color:#27314A}.insight-strip strong{color:var(--navy)}
.summary-card{background:#FFF;border:1px solid var(--line);border-radius:9px;padding:1.4rem 1.5rem;margin:1.15rem 0 1.5rem;box-shadow:0 1px 2px rgba(7,14,54,.04)}.summary-top{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem}.summary-title{color:var(--navy);font-size:1.12rem;font-weight:800}.summary-sub{color:var(--muted);font-size:.76rem;margin-top:.18rem}.summary-status{padding:.34rem .68rem;border-radius:999px;font-size:.67rem;font-weight:800;letter-spacing:.05em;white-space:nowrap}.summary-status.critical{color:var(--critical);background:#FBEAE9;border:1px solid #F3C9C6}.summary-status.medium{color:#9B6C13;background:#FBF1DE;border:1px solid #EED59F}.summary-status.stable{color:var(--stable);background:#E7F5EC;border:1px solid #C6E7D2}.audit-zone{background:#FAFBFD;border:1px solid var(--line);border-radius:8px;padding:1rem 1.05rem;margin-top:.8rem}.audit-zone-title{color:var(--blue);font-size:.69rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.55rem}.audit-text,.audit-list{color:#394259;font-size:.87rem;line-height:1.7}.audit-text strong,.audit-list strong{color:var(--navy)}.audit-list{margin:.15rem 0 0;padding-left:1.08rem}.priority-zone{border-left:3px solid var(--blue);background:#F5F8FF}
.task-card{background:#FFF;border:1px solid var(--line);border-left:4px solid var(--stable);border-radius:9px;margin:.8rem 0;padding:1.2rem 1.35rem;box-shadow:0 1px 2px rgba(7,14,54,.04)}.task-card.critical{border-left-color:var(--critical);background:#FFFBFB}.task-card.medium{border-left-color:var(--warning)}.task-card.stable{border-left-color:var(--stable)}.task-top{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}.task-title{color:var(--navy);font-weight:750;font-size:1.03rem}.task-meta{color:var(--muted);font-size:.78rem;margin-top:.22rem}.risk-badge{border-radius:999px;padding:.3rem .62rem;font-size:.66rem;font-weight:800;letter-spacing:.05em;white-space:nowrap}.critical .risk-badge{color:var(--critical);background:#FBEAE9}.medium .risk-badge{color:#9B6C13;background:#FBF1DE}.stable .risk-badge{color:var(--stable);background:#E7F5EC}.problem{color:#202942;font-size:.92rem;font-weight:650;margin:1rem 0 .55rem}.quote{color:var(--muted);background:#F7F9FC;border-left:2px solid #C7CDDA;padding:.7rem .9rem;font-style:italic;border-radius:0 5px 5px 0}.resolution{color:#27314A;background:#F5F8FF;border:1px solid #D9E4FA;border-left:3px solid var(--blue);padding:.9rem 1rem;margin-top:.9rem;border-radius:0 6px 6px 0}.resolution-title{color:var(--blue);font-size:.72rem;font-weight:800;letter-spacing:.06em;margin-bottom:.32rem}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:1.3rem;border-bottom:1px solid var(--line)}[data-testid="stTabs"] button{color:var(--muted);font-weight:600;padding-left:.15rem;padding-right:.15rem}[data-testid="stTabs"] button[aria-selected="true"]{color:var(--navy)}[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background-color:var(--blue)}[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:8px;overflow:hidden}div[data-testid="stPlotlyChart"]{background:#FFF;border:1px solid var(--line);border-radius:9px;padding:.35rem;box-shadow:0 1px 2px rgba(7,14,54,.04)}
[data-testid="stAppViewContainer"] .stButton button{min-height:2.6rem;border-radius:999px!important;font-weight:700!important;background:#FFF!important;color:var(--navy)!important;border:1.5px solid var(--navy)!important;box-shadow:none!important}[data-testid="stAppViewContainer"] .stButton button:hover{border-color:var(--blue)!important;color:var(--blue)!important;background:#FFF!important}[data-testid="stAppViewContainer"] .stButton button[kind="primary"]{background:#FFF!important;color:var(--navy)!important;border-color:var(--navy)!important}[data-testid="stAppViewContainer"] .stButton button[kind="primary"]:hover{background:var(--blue)!important;color:#FFF!important;border-color:var(--blue)!important}[data-testid="stAppViewContainer"] input,[data-testid="stAppViewContainer"] [data-baseweb="select"]>div{border-radius:5px!important;border-color:var(--line)!important;background:#FFF!important}
@media(max-width:800px){.block-container{padding:1.2rem .8rem 3rem}h1{font-size:2rem!important}.metric-card{min-height:112px;margin-bottom:.6rem}.task-top{display:block}.risk-badge{display:inline-block;margin-top:.45rem}[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:.35rem;overflow-x:auto}[data-testid="stTabs"] button{font-size:.79rem;white-space:nowrap}}
@media(max-width:800px){.source-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.signal-summary,.source-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)


def _clean_json_text(raw: str) -> str:
    cleaned = re.sub(r"```(?:json)?|```", "", raw, flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    return match.group(0) if match else cleaned


def _local_regex_analysis(text: str, rating: int, source: str) -> dict[str, Any]:
    lowered = text.lower()
    rules = {
        "response_time": r"не отвеч|жауап берм|перезвон|ответ",
        "waiting_time": r"очеред|ждал|ждала|күттім|ожидани",
        "staff_behavior": r"груб|хам|перебивал|дөрекі|сотрудник|персонал",
        "pricing": r"цен|дорог|баға|комисси",
        "product_quality": r"сломан|брак|сынып|качество товара|тауар",
        "communication": r"не объяс|ақпарат|информац|общени",
    }
    category = next((name for name, pattern in rules.items() if re.search(pattern, lowered)), "other")
    critical = bool(re.search(r"опасн|мошенн|дважды|угроз|дискрим|үш күн|третий день", lowered))
    negative = bool(re.search(r"ужас|плохо|нашар|не реш|не отвеч|груб|слом|күттім|дорог", lowered))
    if critical or rating == 1:
        sentiment, severity, risk = "negative", "critical", 88
    elif negative or rating == 2:
        sentiment, severity, risk = "negative", "high", 72
    elif rating >= 4:
        sentiment, severity, risk = "positive", "low", 12
    else:
        sentiment, severity, risk = "neutral", "medium", 42
    return {"sentiment": sentiment, "category": category, "severity": severity, "risk_score": risk,
            "summary": "Автоматически обнаружен сигнал, требующий проверки исходного текста человеком.",
            "recommendation": "Назначить ответственного, проверить факты и связаться с автором до публикации ответа.",
            "suggested_response": "Спасибо за обратную связь. Мы проверяем ситуацию и свяжемся с вами после уточнения деталей.",
            "analysis_provider": "local_regex"}


def ask_ai_with_backup(review_text: str, rating: int, source: str) -> dict[str, Any]:
    """Gemini → Groq is handled by the AI service; conservative regex is the last resort."""
    try:
        result, provider = analyze_review(review_text, rating, source)
        result["analysis_provider"] = provider
        return result
    except (AnalysisUnavailable, json.JSONDecodeError, ValueError):
        return _local_regex_analysis(_clean_json_text(review_text), rating, source)


def _fallback_reviews() -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC")
    rows = [
        {"id":"reserve-1","source":"2GIS","author":"Айдана","rating":1,"review_text":"Екі сағат күттім, менеджер өтінішімді таба алмады. Никто не объяснил, что делать дальше.","published_at":now-pd.Timedelta(hours=2),"sentiment":"negative","category":"waiting_time","severity":"critical","risk_score":94,"summary":"Клиент ждал два часа, а обращение было потеряно.","recommendation":"Сегодня назначить ответственного, найти обращение и лично связаться с клиентом.","suggested_response":"Айдана, приносим извинения. Напишите номер обращения в личные сообщения — руководитель проверит ситуацию.","analysis_status":"done","action_status":"pending_review","created_at":now},
        {"id":"reserve-2","source":"Instagram","author":"almaty_client","rating":0,"review_text":"В директ жауап жоқ уже второй день. Нужен документ срочно.","published_at":now-pd.Timedelta(hours=7),"sentiment":"negative","category":"response_time","severity":"high","risk_score":79,"summary":"Клиент второй день не получает ответ по срочному документу.","recommendation":"Ответить клиенту сегодня и проверить очередь необработанных сообщений.","suggested_response":"Приносим извинения за задержку. Отправьте контакт в личные сообщения — срочно уточним статус.","analysis_status":"done","action_status":"pending_review","created_at":now},
        {"id":"reserve-3","source":"Facebook","author":"Сергей","rating":3,"review_text":"Консультация нормальная, бірақ итоговая стоимость оказалась выше первоначальной.","published_at":now-pd.Timedelta(days=2),"sentiment":"neutral","category":"pricing","severity":"medium","risk_score":48,"summary":"Итоговая стоимость отличалась от первоначально озвученной.","recommendation":"Проверить прозрачность расчёта и заранее согласовывать дополнительные расходы.","suggested_response":"Спасибо за замечание. Проверим расчёт и улучшим предварительное информирование о стоимости.","analysis_status":"done","action_status":"pending_review","created_at":now},
        {"id":"reserve-4","source":"2GIS","author":"Мадина","rating":5,"review_text":"Очень грамотная команда, бәрін түсінікті объяснили и помогли быстро.","published_at":now-pd.Timedelta(days=4),"sentiment":"positive","category":"service_quality","severity":"low","risk_score":7,"summary":"Клиент отмечает профессиональную и понятную консультацию.","recommendation":"Передать благодарность команде и поддерживать текущий стандарт.","suggested_response":"Спасибо за доверие! Рады, что смогли быстро и понятно помочь.","analysis_status":"done","action_status":"resolved","created_at":now},
    ]
    return normalize_reviews(pd.DataFrame(rows))


@st.cache_data(ttl=60, show_spinner=False)
def load_data() -> tuple[pd.DataFrame, bool, str]:
    try:
        if not settings.supabase_configured:
            return _fallback_reviews(), True, "Supabase не подключён"
        data = fetch_reviews()
        if not data.empty and settings.grata_2gis_firm_id:
            is_2gis = data["source"].eq("2GIS")
            verified_2gis = data["source_url"].fillna("").str.contains(settings.grata_2gis_firm_id, regex=False)
            data = data[~is_2gis | verified_2gis].copy()
        return data, False, "Данные из Supabase" if not data.empty else "База подключена, отзывов пока нет"
    except Exception as exc:
        return _fallback_reviews(), True, f"Резервный режим: {type(exc).__name__}"


def _risk_level(row: pd.Series) -> tuple[str, str, int]:
    if str(row.get("severity")) == "critical" or float(row.get("risk_score", 0)) >= 85:
        return "critical", "КРИТИЧЕСКИЙ РИСК", 0
    if str(row.get("severity")) in {"high", "medium"} or str(row.get("sentiment")) == "negative" or float(row.get("risk_score", 0)) >= 40:
        return "medium", "ТРЕБУЕТ ВНИМАНИЯ", 1
    return "stable", "СТАБИЛЬНО", 2


def _relative_time(value: Any) -> str:
    stamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(stamp): return "дата не указана"
    delta = pd.Timestamp.now(tz="UTC") - stamp
    if delta < pd.Timedelta(hours=1): return "свежий инцидент — менее часа назад"
    if delta < pd.Timedelta(days=1): return f"свежий инцидент — {max(1, int(delta.total_seconds() // 3600))} ч. назад"
    return f"{max(1, delta.days)} дн. назад"


def _safe(value: Any, fallback: str = "Требуется ручная проверка") -> str:
    return fallback if value is None or pd.isna(value) or not str(value).strip() else html.escape(str(value).strip())


def _is_short_reaction(row: pd.Series) -> bool:
    """Keep lightweight social reactions in the registry without treating them as reviews."""
    text = str(row.get("review_text", "")).strip()
    if int(row.get("rating", 0) or 0) > 0:
        return False
    complaint_markers = re.compile(
        r"не\s|нет\s|ужас|плох|хам|груб|жалоб|проблем|ждал|ждала|күт|жауап|дорог|обман|ошиб|задерж|отказ",
        re.IGNORECASE,
    )
    if complaint_markers.search(text):
        return False
    words = re.findall(r"[A-Za-zА-Яа-яӘәҒғҚқҢңӨөҰұҮүІі]+", text)
    return len(words) <= 3 and len(text) <= 45


def _meaningful_reviews(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    lightweight = data.apply(_is_short_reaction, axis=1)
    return data.loc[~lightweight].copy()


def _refresh_sources() -> None:
    if not (settings.supabase_configured and settings.apify_token):
        st.error("Для проверки нужны подключения Supabase и Apify. Их можно настроить в боковой панели.")
        return
    before = len(fetch_reviews())
    errors: list[str] = []
    progress = st.progress(0, text="Проверяем 2ГИС…")
    jobs = [
        ("2ГИС", lambda: collect_2gis("https://2gis.kz/almaty/firm/9429940000842633/tab/reviews", 50)),
        ("Instagram", lambda: collect_instagram(["https://www.instagram.com/grata_international/"], 100, 12)),
        ("Facebook", lambda: collect_facebook(["https://www.facebook.com/gratanet/"], 100, 20)),
    ]
    for index, (source_name, collect) in enumerate(jobs, start=1):
        progress.progress((index - 1) / len(jobs), text=f"Проверяем {source_name}…")
        try:
            save_collected(collect())
        except ImportServiceError as exc:
            errors.append(f"{source_name}: {exc}")
        progress.progress(index / len(jobs), text=f"{source_name}: проверено")
    after = len(fetch_reviews())
    analysis = analyze_pending(500) if after > before and settings.ai_configured else {"done": 0, "failed": 0}
    st.session_state["last_checked_at"] = pd.Timestamp.now(tz="Asia/Almaty").strftime("%d.%m.%Y, %H:%M")
    st.cache_data.clear()
    progress.empty()
    new_count = max(0, after - before)
    if new_count:
        st.success(f"Новых записей: {new_count}. Проанализировано: {analysis['done']}.")
    else:
        st.info("Новых отзывов и комментариев не найдено.")
    if errors:
        with st.expander("Некоторые источники временно не ответили"):
            for error in errors:
                st.caption(error)


def _sidebar() -> str:
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark">◆</span>Sentiment Analyzer</div><div class="brand-sub">GRATA INTERNATIONAL</div>', unsafe_allow_html=True)
        navigation = {
            "▦  Обзор": "dashboard",
            "◉  Отзывы": "reviews",
            "⌁  Аналитика": "analytics",
            "✦  AI-выводы": "insights",
            "▤  Источники": "sources",
            "⚙  Настройки": "settings",
        }
        selected_label = st.radio("Навигация", list(navigation), label_visibility="collapsed")
        st.divider()
        if st.button("🔄 Проверить новые отзывы", disabled=not(settings.supabase_configured and settings.apify_token), width="stretch", type="primary"):
            _refresh_sources()
        st.caption("НАСТРОЙКИ")
        period = st.selectbox("Показывать отзывы", ["Последние 7 дней","Последние 30 дней","Последние 90 дней","Всё время"], index=3)
        st.session_state["period_days"] = {"Последние 7 дней":7,"Последние 30 дней":30,"Последние 90 дней":90,"Всё время":None}[period]
        st.divider()
        with st.expander("Добавить новые отзывы"):
            st.caption("Здесь можно загрузить отзывы из подключённых источников.")
            st.write(f"Supabase: {'подключён' if settings.supabase_configured else 'не подключён'}")
            st.write(f"Анализ текста: {'готов' if settings.ai_configured else 'нужен ключ'}")
            st.write(f"Apify: {'подключён' if settings.apify_token else 'нужен токен'}")
            source = st.selectbox("Источник", ["2GIS","Instagram","Facebook"])
            default_link = {"2GIS":"https://2gis.kz/almaty/firm/9429940000842633/tab/reviews", "Instagram":"https://www.instagram.com/grata_international/", "Facebook":"https://www.facebook.com/gratanet/"}[source]
            links_text = st.text_area("Ссылка на страницу или публикацию", value=default_link, key=f"links-{source}", help="Можно вставить страницу целиком. Публичные публикации и комментарии будут пройдены автоматически.")
            if source == "2GIS":
                limit = st.number_input("Максимум отзывов", 5, 500, 100, 5)
                max_posts = 0
            else:
                max_posts = st.number_input("Максимум публикаций (0 = все доступные)", 0, 500, 12, 1, key=f"posts-{source}")
                limit = st.number_input("Максимум комментариев на публикацию", 10, 2000, 100, 10, key=f"comments-{source}")
                st.caption("Чем больше публикаций и комментариев, тем выше расход Apify. Загружаются только публично доступные данные.")
            if st.button("Загрузить отзывы", disabled=not(settings.supabase_configured and settings.apify_token), width="stretch"):
                links = [x.strip() for x in links_text.splitlines() if x.strip()]
                if not links: st.error("Добавьте ссылку.")
                else:
                    try:
                        with st.spinner("Получаем данные…"):
                            rows = collect_2gis(links[0], int(limit)) if source == "2GIS" else collect_instagram(links, int(limit), int(max_posts or 500)) if source == "Instagram" else collect_facebook(links, int(limit), int(max_posts))
                            count = save_collected(rows)
                        st.cache_data.clear(); st.success(f"Сохранено: {count}")
                    except ImportServiceError as exc: st.error(str(exc))
            if st.button("Проанализировать новые отзывы", disabled=not(settings.supabase_configured and settings.ai_configured), width="stretch"):
                try:
                    with st.spinner("Анализируем новые записи…"): result = analyze_pending(100)
                    st.cache_data.clear(); st.success(f"Готово: {result['done']}; ошибок: {result['failed']}")
                except DataServiceError as exc: st.error(str(exc))
    return navigation[selected_label]


def _filter_period(data: pd.DataFrame) -> pd.DataFrame:
    days = st.session_state.get("period_days", 90)
    return data.copy() if days is None or data.empty else data[data["published_at"] >= pd.Timestamp.now(tz="UTC")-pd.Timedelta(days=days)].copy()


def _metrics(data: pd.DataFrame, raw_total: int) -> None:
    analyzed = data[data["analysis_status"].eq("done")]
    critical = int(((analyzed["severity"] == "critical") | (analyzed["risk_score"] >= 85)).sum())
    health = brand_health_score(analyzed)
    values = [
        ("Записей в базе", f"{raw_total:,}", f"Содержательных: {len(data):,}", ""),
        ("Серьёзные сигналы", f"{critical:,}", "Требуют внимания руководства" if critical else "Критических проблем нет", "alert" if critical else "good"),
        ("Индекс репутации", f"{health} / 100", "По содержательным отзывам", "good" if health >= 75 else "alert"),
    ]
    for column, (label, value, note, css) in zip(st.columns(3), values):
        with column:
            st.markdown(f'<div class="metric-card {css}"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)


def _trend(data: pd.DataFrame) -> go.Figure:
    analyzed = data[data["analysis_status"].eq("done")].dropna(subset=["published_at"]).copy()
    if analyzed.empty: return go.Figure()
    analyzed["day"] = analyzed["published_at"].dt.floor("D")
    daily = analyzed.groupby("day").agg(total=("id","size"),negative=("sentiment",lambda x:x.eq("negative").sum())).reset_index()
    fig = go.Figure([go.Scatter(name="Все содержательные отзывы",x=daily.day,y=daily.total,mode="lines",line=dict(color="#4E81EE",width=3),fill="tozeroy",fillcolor="rgba(78,129,238,.12)",hovertemplate="%{x|%d.%m}<br>Всего: %{y}<extra></extra>"),go.Scatter(name="Негативные",x=daily.day,y=daily.negative,mode="lines+markers",line=dict(color="#D5473F",width=2),marker=dict(size=5),hovertemplate="%{x|%d.%m}<br>Негатив: %{y}<extra></extra>")])
    fig.update_layout(height=330,margin=dict(l=18,r=18,t=25,b=40),showlegend=True,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",hovermode="x unified",font=dict(color="#B1BDCC"),legend=dict(orientation="h",y=-.18,x=.5,xanchor="center"))
    fig.update_xaxes(showgrid=False,showline=False,title=None,tickformat="%d.%m"); fig.update_yaxes(showgrid=True,gridcolor="rgba(148,163,184,.1)",zeroline=False,title=None,showticklabels=False)
    return fig


def _sentiment_chart(data: pd.DataFrame) -> go.Figure:
    analyzed = data[data["analysis_status"].eq("done")]
    labels = {"positive": "Позитив", "neutral": "Нейтрально", "negative": "Негатив"}
    colors = {"positive": "#2E9E63", "neutral": "#D69A2D", "negative": "#D5473F"}
    counts = analyzed["sentiment"].value_counts().reindex(labels, fill_value=0)
    fig = go.Figure(go.Pie(
        labels=[labels[key] for key in counts.index], values=counts.values, hole=.68,
        marker=dict(colors=[colors[key] for key in counts.index], line=dict(color="#FFFFFF", width=3)),
        textinfo="percent", textfont=dict(size=12, color="#FFFFFF"),
        hovertemplate="%{label}: %{value} отзывов<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{int(counts.sum())}</b><br><span style='font-size:11px'>отзывов</span>", showarrow=False, font=dict(size=22, color="#070E36"))
    fig.update_layout(height=310, margin=dict(l=8, r=8, t=12, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-.05, x=.5, xanchor="center", font=dict(color="#5B6478")))
    return fig


def _issues_chart(data: pd.DataFrame) -> go.Figure:
    analyzed = data[data["analysis_status"].eq("done")]
    complaints = analyzed[analyzed["sentiment"].eq("negative")]
    counts = complaints["category"].map(CATEGORY_LABELS).fillna("Другое").value_counts().head(6).sort_values()
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h", marker=dict(color="#4E81EE", cornerradius=4),
        text=counts.values, textposition="inside", textfont=dict(color="#FFFFFF", size=12),
        hovertemplate="%{y}: %{x} жалоб<extra></extra>",
    ))
    fig.update_layout(height=310, margin=dict(l=8, r=18, t=12, b=18), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#5B6478"))
    fig.update_xaxes(visible=False, rangemode="tozero")
    fig.update_yaxes(showgrid=False, title=None, tickfont=dict(size=12, color="#394259"))
    return fig


def _general_recommendations(data: pd.DataFrame) -> None:
    analyzed = data[data["analysis_status"].eq("done")].copy()
    if analyzed.empty:
        return
    complaints = analyzed[analyzed["sentiment"].eq("negative")].copy()
    total, negative_total = len(analyzed), len(complaints)
    health = brand_health_score(analyzed)
    if health < 50:
        status, status_css = "🔴 КРИТИЧЕСКИЙ РИСК", "critical"
    elif health < 75 or negative_total:
        status, status_css = "🟡 СРЕДНИЙ РИСК", "medium"
    else:
        status, status_css = "🟢 РЕПУТАЦИЯ СТАБИЛЬНА", "stable"

    platform, platform_count, platform_share = "—", 0, 0
    category, category_count, category_share = "Деструктивные сигналы не выявлены", 0, 0
    trend_text, dominant_key = "устойчивый негативный тренд не выявлен", "other"
    if negative_total:
        platform_counts = complaints["source"].value_counts()
        platform, platform_count = str(platform_counts.index[0]), int(platform_counts.iloc[0])
        platform_share = round(platform_count / negative_total * 100)
        category_counts = complaints["category"].value_counts()
        dominant_key, category_count = str(category_counts.index[0]), int(category_counts.iloc[0])
        category = CATEGORY_LABELS.get(dominant_key, "Другое")
        category_share = round(category_count / total * 100)
        category_rows = complaints[complaints["category"].eq(dominant_key)]
        recent_count = int(category_rows["published_at"].ge(pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)).sum())
        if recent_count == category_count and category_count > 1:
            trend_text = "все сигналы свежие — наблюдается ускоренное накопление за последние 30 дней"
        elif recent_count:
            trend_text = f"{recent_count} из {category_count} сигналов поступили за последние 30 дней"
        else:
            trend_text = "жалобы старше 30 дней — признак затяжной, а не новой проблемы"

    impact_notes = {
        "2GIS": "определяет доверие первичного локального трафика в Казахстане и конверсию из карт и поиска",
        "Instagram": "формирует публичное восприятие бренда и риск вирусного распространения негатива",
        "Facebook": "влияет на профессиональную аудиторию, рекомендации и международный публичный имидж",
    }
    platform_lines = []
    for source, source_rows in analyzed.groupby("source"):
        source_negative = int(source_rows["sentiment"].eq("negative").sum())
        source_pct = round(source_negative / len(source_rows) * 100) if len(source_rows) else 0
        impact = impact_notes.get(str(source), "влияет на доверие аудитории и цифровую репутацию")
        platform_lines.append(
            f'<li><strong>{html.escape(str(source))}</strong>: <strong>{source_negative} из {len(source_rows)}</strong> негативных сигналов '
            f'(<strong>{source_pct}%</strong>); площадка {impact}.</li>'
        )
    platforms_html = "".join(platform_lines)
    action_map = {
        "response_time": "утвердить единый SLA первого ответа, назначить владельца очереди и включить ежедневный контроль просрочек",
        "staff_behavior": "инициировать внеплановый комплаенс-аудит коммуникаций сотрудников, утвердить стандарт деловой речи и ввести выборочную проверку диалогов",
        "service_quality": "провести аудит клиентского пути по проблемным обращениям, закрепить контрольные точки качества и персональную ответственность владельца кейса",
        "communication": "внедрить единый скрипт информирования клиента о статусе дела, сроках и следующем действии с обязательной фиксацией в CRM",
        "waiting_time": "ввести норматив времени ожидания, автоматическую эскалацию просроченных обращений и ежедневный отчёт руководителю",
        "pricing": "провести аудит коммерческих предложений и обязать сотрудников письменно согласовывать стоимость и дополнительные расходы до начала работ",
        "product_quality": "инициировать проверку качества результата по негативным кейсам и внедрить обязательный контроль перед передачей клиенту",
        "other": "провести ручную классификацию негативных кейсов и закрепить владельца процесса с недельным контролем повторяемости",
    }
    priority = action_map.get(dominant_key, action_map["other"])
    positives = analyzed[analyzed["sentiment"].eq("positive")]
    positive_count = len(positives)
    if positive_count:
        positive_key = str(positives["category"].value_counts().index[0])
        positive_category = CATEGORY_LABELS.get(positive_key, "Качество обслуживания")
        positive_category_count = int(positives["category"].eq(positive_key).sum())
        continue_text = (
            f'Сильная сторона — <strong>{html.escape(positive_category)}</strong>: '
            f'<strong>{positive_category_count}</strong> позитивных подтверждений. Следует закрепить данный стандарт как '
            f'корпоративный эталон, формализовать успешные практики и масштабировать их на все клиентские точки контакта.'
        )
    else:
        continue_text = (
            'Статистически подтверждённая сильная сторона в текущем массиве не сформирована. Следует сохранять '
            'нейтрально оценённые элементы клиентского опыта и подтвердить их устойчивость дополнительными данными.'
        )
    st.markdown(
        f'<div class="summary-card"><div class="summary-top"><div><div class="summary-title">✦ Главные выводы и рекомендации</div>'
        f'<div class="summary-sub">Что отзывы говорят о репутации компании</div></div>'
        f'<span class="summary-status {status_css}">{status}</span></div>'
        f'<div class="audit-zone"><div class="audit-zone-title">1 · 🛡️ Общая оценка</div><div class="audit-text">'
        f'Состояние репутации — <strong>{health}/100</strong>. Негативных отзывов — <strong>{negative_total} из {total}</strong> (<strong>{round(negative_total / total * 100) if total else 0}%</strong>). '
        f'Негатив может снижать доверие, количество повторных обращений и число клиентов, которые находят компанию через поиск и карты.</div>'
        f'<ul class="audit-list">{platforms_html}</ul></div>'
        f'<div class="audit-zone"><div class="audit-zone-title">2 · 📊 Что важно сейчас</div><ul class="audit-list">'
        f'<li>Больше всего негатива на площадке <strong>{html.escape(platform)}</strong>: <strong>{platform_count}</strong> жалоб, или <strong>{platform_share}%</strong> всего негатива.</li>'
        f'<li>Самая частая проблема — <strong>{html.escape(category)}</strong>: <strong>{category_count}</strong> случаев, или <strong>{category_share}%</strong> всех отзывов.</li>'
        f'<li>По времени: <strong>{html.escape(trend_text)}</strong>. Комментарии на русском и казахском учитываются при анализе.</li></ul></div>'
        f'<div class="audit-zone priority-zone"><div class="audit-zone-title">3 · ⚖️ Что нужно улучшить</div>'
        f'<div class="audit-text">{html.escape(priority).capitalize()}. Руководству необходимо контролировать результат, пока похожие жалобы не перестанут повторяться.</div></div>'
        f'<div class="audit-zone"><div class="audit-zone-title">Что уже хорошо и важно сохранить</div>'
        f'<div class="audit-text">{continue_text}</div></div></div>',
        unsafe_allow_html=True,
    )


def _task(row: pd.Series, fallback: bool) -> None:
    css,badge,_ = _risk_level(row); category=CATEGORY_LABELS.get(str(row.get("category","other")),"Другое")
    st.markdown(f'<div class="task-card {css}"><div class="task-top"><div><div class="task-title">{category}</div><div class="task-meta">{_safe(row.get("source"))} · 🕒 {_relative_time(row.get("published_at"))}</div></div><span class="risk-badge">{badge}</span></div><div class="problem">{_safe(row.get("summary"))}</div><div class="quote">«{_safe(row.get("review_text"))}»</div><div class="resolution"><div class="resolution-title">🎯 РЕКОМЕНДАЦИЯ</div>{_safe(row.get("recommendation"))}</div></div>', unsafe_allow_html=True)


def _platform_chart(data: pd.DataFrame) -> go.Figure:
    analyzed = data[data["analysis_status"].eq("done")]
    if analyzed.empty:
        return go.Figure()
    order = ["positive", "neutral", "negative"]
    labels = {"positive": "Позитив", "neutral": "Нейтрально", "negative": "Негатив"}
    colors = {"positive": "#2E9E63", "neutral": "#D69A2D", "negative": "#D5473F"}
    matrix = pd.crosstab(analyzed["source"], analyzed["sentiment"], normalize="index").mul(100)
    fig = go.Figure()
    for sentiment in order:
        values = matrix[sentiment] if sentiment in matrix else pd.Series(0, index=matrix.index)
        fig.add_bar(name=labels[sentiment], x=matrix.index, y=values, marker_color=colors[sentiment], hovertemplate="%{x}: %{y:.0f}%<extra></extra>")
    fig.update_layout(barmode="stack", height=340, margin=dict(l=20,r=20,t=25,b=25), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#5B6478"), legend=dict(orientation="h", y=-.2, x=.5, xanchor="center"))
    fig.update_yaxes(range=[0,100], ticksuffix="%", gridcolor="#EEF0F4", title=None)
    fig.update_xaxes(title=None)
    return fig


def _page_header(title: str, subtitle: str, kicker: str = "SENTIMENT ANALYZER") -> None:
    st.markdown(f'<div class="page-kicker">{html.escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="page-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def _registry(data: pd.DataFrame) -> None:
    if data.empty:
        st.info("Документы ещё не загружены.")
        return
    st.markdown('<div class="registry-help">Все данные сохранены: полноценные отзывы, комментарии и короткие реакции.</div>', unsafe_allow_html=True)
    filter_left, filter_mid, filter_right = st.columns([1.4, 1, 1])
    with filter_left: query = st.text_input("Поиск", placeholder="Автор, ключевое слово или текст")
    with filter_mid: sources = st.multiselect("Площадка", sorted(data["source"].dropna().astype(str).unique()))
    with filter_right: tones = st.multiselect("Настроение", ["Позитив", "Нейтрально", "Негатив", "Не обработано"])
    registry=data.sort_values("published_at",ascending=False).copy(); registry["Дата"]=registry.published_at.dt.strftime("%d.%m.%Y %H:%M"); registry["Источник"]=registry.source; registry["Автор"]=registry.author; registry["Оценка"]=registry.rating.map(lambda x:f"{int(x)}/5" if int(x)>0 else "Без оценки"); registry["Настроение"]=registry.sentiment.map({"positive":"Позитив","neutral":"Нейтрально","negative":"Негатив"}).fillna("Не обработано"); registry["Риск"]=registry.apply(lambda row: str(int(row["risk_score"])) if row["sentiment"] == "negative" else "Нет риска", axis=1); registry["Текст"]=registry.review_text
    if sources: registry = registry[registry["Источник"].isin(sources)]
    if tones: registry = registry[registry["Настроение"].isin(tones)]
    if query.strip():
        needle=query.strip().lower(); registry=registry[registry["Автор"].fillna("").str.lower().str.contains(needle,regex=False)|registry["Текст"].fillna("").str.lower().str.contains(needle,regex=False)]
    st.caption(f"Показано: {len(registry)} из {len(data)}")
    st.dataframe(registry[["Дата","Источник","Автор","Оценка","Настроение","Риск","Текст"]],hide_index=True,width="stretch",height=620)


view = _sidebar()
raw_data, fallback_mode, data_note = load_data(); raw_data = _filter_period(raw_data)
data = _meaningful_reviews(raw_data)
checked_at = st.session_state.get("last_checked_at")
latest = raw_data["created_at"].max() if not raw_data.empty else pd.NaT
freshness = f"Последняя проверка: {checked_at}" if checked_at else (f"Последняя запись: {latest.tz_convert('Asia/Almaty').strftime('%d.%m.%Y, %H:%M')}" if pd.notna(latest) else "Данных пока нет")

if view == "dashboard":
    _page_header("Обзор", "Что клиенты говорят о GRATA International прямо сейчас")
    head_left, head_right = st.columns([1.8, 1], vertical_alignment="center")
    with head_left: st.markdown(f'<div class="company-line"><span class="live-dot {"fallback-dot" if fallback_mode else ""}"></span>{html.escape(freshness)}</div>', unsafe_allow_html=True)
    with head_right:
        if st.button("Проверить новые отзывы", disabled=not(settings.supabase_configured and settings.apify_token), width="stretch", type="primary"):
            _refresh_sources()
    _metrics(data, len(raw_data))
    if data.empty:
        st.info("Содержательных отзывов за выбранный период нет. Короткие реакции сохранены в разделе «Все отзывы».")
    else:
        serious = int((((data["severity"] == "critical") | (data["risk_score"] >= 85)) & data["analysis_status"].eq("done")).sum())
        attention = int(((data["sentiment"] == "negative") & data["analysis_status"].eq("done")).sum())
        if serious:
            st.markdown(f'<div class="overview-note attention"><strong>Требуется внимание:</strong> обнаружено серьёзных сигналов — {serious}. Они показаны первыми в разделе «AI-выводы».</div>', unsafe_allow_html=True)
        elif attention:
            st.markdown(f'<div class="overview-note attention"><strong>Критических угроз нет.</strong> При этом {attention} отзывов требуют проверки и показаны в разделе «AI-выводы».</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="overview-note"><strong>Критических изменений не обнаружено.</strong> Репутационная ситуация стабильна по содержательным отзывам выбранного периода.</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Картина репутации</div>', unsafe_allow_html=True)
        left, right = st.columns([.9, 1.35], gap="large")
        with left:
            st.markdown('<div class="chart-heading">Распределение настроений</div><div class="chart-sub">Как клиенты оценивают опыт взаимодействия</div>', unsafe_allow_html=True)
            st.plotly_chart(_sentiment_chart(data), width="stretch", config={"displayModeBar": False})
        with right:
            st.markdown('<div class="chart-heading">Основные причины недовольства</div><div class="chart-sub">Какие проблемы встречаются чаще всего</div>', unsafe_allow_html=True)
            complaints = data[(data["analysis_status"] == "done") & (data["sentiment"] == "negative")]
            if complaints.empty:
                st.markdown('<div class="empty-panel">✓ Системных причин недовольства за выбранный период не обнаружено.</div>', unsafe_allow_html=True)
            else:
                st.plotly_chart(_issues_chart(data), width="stretch", config={"displayModeBar": False})
        negative = data[(data["analysis_status"] == "done") & (data["sentiment"] == "negative")]
        insight = "Негативных сигналов не обнаружено — сохраняйте текущий стандарт коммуникации."
        if not negative.empty:
            top_issue = CATEGORY_LABELS.get(str(negative["category"].value_counts().index[0]), "Другое")
            insight = f"Главный фокус: {top_issue.lower()}. Откройте AI-выводы для подробной управленческой резолюции."
        st.markdown(f'<div class="insight-strip"><strong>Ключевой вывод.</strong> {html.escape(insight)}</div>', unsafe_allow_html=True)

elif view == "reviews":
    _page_header("Все отзывы", "Поиск и проверка обратной связи из всех подключённых источников")
    _registry(raw_data)

elif view == "analytics":
    _page_header("Аналитика", "Динамика настроений, проблемные темы и сравнение площадок")
    trend_tab, topics_tab, platforms_tab = st.tabs(["Динамика", "Темы", "Площадки"])
    with trend_tab: st.plotly_chart(_trend(data), width="stretch", config={"displayModeBar":False})
    with topics_tab:
        if data[data["sentiment"].eq("negative")].empty: st.info("Негативных тем за выбранный период нет.")
        else: st.plotly_chart(_issues_chart(data), width="stretch", config={"displayModeBar":False})
    with platforms_tab: st.plotly_chart(_platform_chart(data), width="stretch", config={"displayModeBar":False})

elif view == "insights":
    _page_header("AI-выводы", "Риски, сильные стороны и рекомендации для руководства")
    if fallback_mode: st.warning("Показаны резервные демонстрационные записи. Подключите Supabase для реальных решений.")
    analyzed=data[data["analysis_status"].eq("done")].copy()
    lightweight_count = max(0, len(raw_data) - len(data))
    if analyzed.empty: st.info("Проанализированных отзывов пока нет. Добавьте отзывы через боковую панель и запустите анализ.")
    else:
        analyzed["_priority"]=[_risk_level(row)[2] for _,row in analyzed.iterrows()]; analyzed=analyzed.sort_values(["_priority","published_at"],ascending=[True,False])
        priority = analyzed[analyzed["_priority"] < 2]
        stable = analyzed[analyzed["_priority"] == 2]
        st.markdown(f'<div class="signal-summary"><div class="signal-item"><div class="signal-number">{len(priority)}</div><div class="signal-label">требуют внимания</div></div><div class="signal-item"><div class="signal-number">{len(stable)}</div><div class="signal-label">содержательных стабильных</div></div><div class="signal-item"><div class="signal-number">{lightweight_count}</div><div class="signal-label">коротких реакций сохранено</div></div></div>', unsafe_allow_html=True)
        if priority.empty:
            st.success("Активных репутационных рисков не обнаружено. Все исходные записи доступны в полном реестре.")
        else:
            st.caption("Сначала показаны самые серьёзные и свежие сигналы")
            for _,row in priority.iterrows(): _task(row,fallback_mode)
        if not stable.empty:
            with st.expander(f"Показать стабильные содержательные отзывы ({len(stable)})"):
                for _, row in stable.iterrows(): _task(row, fallback_mode)
        _general_recommendations(data)

elif view == "sources":
    _page_header("Источники", "Подключённые площадки и загрузка новых данных")
    counts = raw_data["source"].value_counts().to_dict() if not raw_data.empty else {}
    cards=[]
    for icon,name,data_key,ready in [("2","2ГИС","2GIS",bool(settings.apify_token)),("◎","Instagram","Instagram",bool(settings.apify_token)),("f","Facebook","Facebook",bool(settings.apify_token)),("G","Google","Google",False),("in","LinkedIn","LinkedIn",False),("CSV","CSV-файлы","CSV",settings.supabase_configured)]:
        count=int(counts.get(data_key,0)); status="Подключено" if ready else "Не подключено"; css="" if ready else " off"
        cards.append(f'<div class="source-card"><div class="source-icon">{icon}</div><div class="source-name">{name}</div><div class="source-status{css}">● {status}</div><div class="source-count">{count} записей в текущем периоде</div></div>')
    st.markdown('<div class="source-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    st.markdown("### Импорт CSV")
    uploaded = st.file_uploader("Выберите CSV-файл", type=["csv"], help="Колонки: source, author, rating, review_text, published_at")
    if uploaded is not None:
        try:
            preview = pd.read_csv(uploaded)
            required={"source","author","rating","review_text","published_at"}
            missing=required-set(preview.columns)
            if missing: st.error("Не хватает колонок: "+", ".join(sorted(missing)))
            else:
                st.dataframe(preview.head(10),hide_index=True,width="stretch")
                if st.button("Импортировать в Supabase",disabled=not settings.supabase_configured):
                    rows=preview[list(required)].copy(); rows["published_at"]=pd.to_datetime(rows["published_at"],errors="coerce",utc=True).astype(str); rows["analysis_status"]="pending"; rows["action_status"]="pending_review"
                    count=insert_reviews(rows.to_dict("records")); st.cache_data.clear(); st.success(f"Импортировано записей: {count}")
        except Exception as exc: st.error(f"Не удалось прочитать CSV: {exc}")

elif view == "settings":
    _page_header("Настройки", "Состояние подключений и параметры анализа")
    left,right=st.columns([1.25,1])
    with left:
        st.markdown("### Подключения")
        st.write(f"Supabase: **{'подключён' if settings.supabase_configured else 'не подключён'}**")
        st.write(f"Gemini или Groq: **{'готов' if settings.ai_configured else 'не настроен'}**")
        st.write(f"Apify: **{'подключён' if settings.apify_token else 'не подключён'}**")
        st.caption("Секретные ключи задаются в .env локально или в Streamlit Secrets после deployment.")
    with right:
        st.markdown('<div class="connection-panel"><strong>GRATA INTERNATIONAL</strong><p>Sentiment Analyzer</p><p>Единый центр мониторинга клиентской обратной связи.</p></div>',unsafe_allow_html=True)
