from __future__ import annotations

import streamlit as st

from services.import_service import ImportServiceError, collect_2gis, collect_facebook, collect_instagram, save_collected
from services.pipeline_service import analyze_pending
from services.supabase_service import DataServiceError
from utils.config import settings

GRATA_2GIS = "https://2gis.kz/almaty/firm/9429940000842633/tab/reviews"
GRATA_INSTAGRAM = "https://instagram.com/grata_international/"
GRATA_FACEBOOK = "https://www.facebook.com/gratanet/"


def _urls(value: str) -> list[str]:
    return [line.strip() for line in value.replace(",", "\n").splitlines() if line.strip()]


def render():
    st.title("Загрузка реальных отзывов")
    st.caption("GRATA International · данные сохраняются в Supabase и анализируются один раз")
    if not settings.supabase_configured:
        st.error("Добавьте SUPABASE_URL и SUPABASE_KEY в файл .env, затем перезапустите приложение.")
    if not settings.apify_token:
        st.warning("Для публичных данных нужен APIFY_TOKEN. Пароль от Instagram или Facebook не требуется.")
    ready = settings.supabase_configured and bool(settings.apify_token)
    c1, c2, c3 = st.columns(3)
    c1.metric("Supabase", "Подключён" if settings.supabase_configured else "Не подключён")
    c2.metric("Сбор данных", "Подключён" if settings.apify_token else "Нужен Apify")
    c3.metric("AI-анализ", "Готов" if settings.ai_configured else "Нужен ключ")
    st.info("Комментарии Instagram и Facebook не имеют звёзд. Для них будет показано «Без оценки», а тональность определит AI.")
    source = st.selectbox("Откуда загрузить", ["2GIS", "Instagram", "Facebook"])
    limit = st.slider("Сколько последних отзывов/комментариев", 5, 100, 30, 5)
    if source == "2GIS":
        value = st.text_input("Ссылка на карточку 2GIS", value=GRATA_2GIS)
        hint = "Можно использовать короткую или полную ссылку на карточку компании."
    elif source == "Instagram":
        value = st.text_area("Ссылки на публикации или Reels — по одной в строке", placeholder="https://www.instagram.com/p/.../")
        hint = f"Профиль: {GRATA_INSTAGRAM} Откройте нужные публикации и скопируйте их ссылки."
    else:
        value = st.text_area("Ссылки на публикации Facebook — по одной в строке", placeholder="https://www.facebook.com/gratanet/posts/...")
        hint = f"Страница: {GRATA_FACEBOOK} Нужны ссылки именно на публикации."
    st.caption(hint)
    if st.button("Получить и сохранить реальные данные", type="primary", disabled=not ready):
        links = _urls(value)
        if not links:
            st.error("Добавьте хотя бы одну ссылку.")
        else:
            try:
                with st.spinner("Получаем публичные данные. Это может занять несколько минут…"):
                    if source == "2GIS": rows = collect_2gis(links[0], limit)
                    elif source == "Instagram": rows = collect_instagram(links, limit)
                    else: rows = collect_facebook(links, limit)
                    saved = save_collected(rows)
                st.cache_data.clear()
                if saved: st.success(f"Получено и сохранено: {saved}. Запустите AI-анализ ниже.")
                else: st.warning("Новых текстовых отзывов не найдено. Проверьте ссылку в Apify Console.")
            except ImportServiceError as exc:
                st.error(str(exc))
    st.divider()
    st.subheader("AI-анализ новых данных")
    st.write("Gemini обрабатывает каждый новый отзыв один раз. Если он недоступен, используется Groq.")
    if st.button("Проанализировать новые отзывы", disabled=not settings.supabase_configured or not settings.ai_configured):
        bar = st.progress(0, text="Подготовка…")
        try:
            result = analyze_pending(limit=100, progress=lambda done, total: bar.progress(done / max(total, 1), text=f"Обработано {done} из {total}"))
            st.cache_data.clear()
            if result["total"] == 0: st.info("Новых отзывов для анализа нет.")
            elif result["failed"]: st.warning(f"Готово: {result['done']}. Ошибок: {result['failed']}.")
            else: st.success(f"Анализ завершён: {result['done']} отзывов.")
        except DataServiceError as exc:
            st.error(str(exc))
