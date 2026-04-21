import io
import csv
import json
import streamlit as st
from streamlit_local_storage import LocalStorage

import collector_instagram as instagram
import collector_tiktok as tiktok

st.set_page_config(page_title="Social Stats", page_icon="📊", layout="centered")

local_storage = LocalStorage()

st.title("📊 Social Media Stats")
st.caption("Собирает посты Instagram и видео TikTok: лайки, просмотры, комментарии."
           "\n\nInstagram: [HikerAPI](https://hikerapi.com) · TikTok: [EnsembleData](https://ensembledata.com)")

# ── Загружаем сохранённые данные формы ───────────────────────────────────────
if "form_loaded" not in st.session_state:
    raw = local_storage.getItem("form_data")
    data = json.loads(raw) if raw else {}
    st.session_state["ig_token"]      = data.get("ig_token", "")
    st.session_state["ig_usernames"]  = data.get("ig_usernames", "")
    st.session_state["ig_max_posts"]  = data.get("ig_max_posts", 20)
    st.session_state["ig_max_reels"]  = data.get("ig_max_reels", 20)
    st.session_state["tt_token"]      = data.get("tt_token", "")
    st.session_state["tt_usernames"]  = data.get("tt_usernames", "")
    st.session_state["tt_max_videos"] = data.get("tt_max_videos", 20)
    st.session_state["form_loaded"]   = True

# ── Форма ─────────────────────────────────────────────────────────────────────
with st.form("params"):

    # Instagram
    st.subheader("📸 Instagram (HikerAPI)")
    ig_token = st.text_input(
        "🔑 HikerAPI Token",
        value=st.session_state.get("ig_token", ""),
        type="password",
        help="Получить: https://hikerapi.com",
    )
    ig_usernames = st.text_input(
        "👤 Аккаунты (через запятую)",
        value=st.session_state.get("ig_usernames", ""),
        placeholder="например: instagram, nasa, natgeo",
    )
    col1, col2 = st.columns(2)
    ig_max_posts = col1.number_input("📷 Постов на аккаунт", min_value=1, max_value=100,
                                     value=st.session_state.get("ig_max_posts", 20))
    ig_max_reels = col2.number_input("🎬 Reels на аккаунт",  min_value=1, max_value=100,
                                     value=st.session_state.get("ig_max_reels", 20))

    st.divider()

    # TikTok
    st.subheader("🎵 TikTok (EnsembleData)")
    tt_token = st.text_input(
        "🔑 EnsembleData Token",
        value=st.session_state.get("tt_token", ""),
        type="password",
        help="Получить (7 дней бесплатно): https://ensembledata.com",
    )
    tt_usernames = st.text_input(
        "👤 Аккаунты (через запятую)",
        value=st.session_state.get("tt_usernames", ""),
        placeholder="например: tiktok, khaby.lame",
    )
    tt_max_videos = st.number_input("🎬 Видео на аккаунт", min_value=1, max_value=100,
                                    value=st.session_state.get("tt_max_videos", 20))

    submitted = st.form_submit_button("🚀 Собрать данные", width="stretch")


# ── Утилиты ───────────────────────────────────────────────────────────────────
def parse_usernames(raw: str) -> list[str]:
    """Разбивает строку аккаунтов по запятой, чистит @ и пробелы."""
    return [u.strip().lstrip("@") for u in raw.split(",") if u.strip()]


def rows_to_csv(rows: list) -> str:
    buf = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ── Обработка формы ───────────────────────────────────────────────────────────
if submitted:
    # Сохраняем в session_state и localStorage
    st.session_state.update({
        "ig_token": ig_token, "ig_usernames": ig_usernames,
        "ig_max_posts": ig_max_posts, "ig_max_reels": ig_max_reels,
        "tt_token": tt_token, "tt_usernames": tt_usernames,
        "tt_max_videos": tt_max_videos,
        "results": None,
    })
    local_storage.setItem("form_data", json.dumps({
        "ig_token": ig_token, "ig_usernames": ig_usernames,
        "ig_max_posts": int(ig_max_posts), "ig_max_reels": int(ig_max_reels),
        "tt_token": tt_token, "tt_usernames": tt_usernames,
        "tt_max_videos": int(tt_max_videos),
    }))

    ig_accounts = parse_usernames(ig_usernames)
    tt_accounts = parse_usernames(tt_usernames)

    if not ig_accounts and not tt_accounts:
        st.error("Укажите хотя бы один аккаунт.")
        st.stop()

    all_rows = []
    errors = []

    # ── Instagram ──────────────────────────────────────────────────────────
    if ig_accounts and ig_token:
        for username in ig_accounts:
            with st.spinner(f"Instagram: @{username}…"):
                rows, err = instagram.collect(
                    token=ig_token,
                    username=username,
                    max_posts=int(ig_max_posts),
                    max_videos=int(ig_max_reels),
                )
                if err:
                    errors.append(err)
                all_rows.extend(rows)
    elif ig_accounts and not ig_token:
        errors.append("⚠️ Указаны Instagram-аккаунты, но не введён HikerAPI токен.")

    # ── TikTok ─────────────────────────────────────────────────────────────
    if tt_accounts and tt_token:
        for username in tt_accounts:
            with st.spinner(f"TikTok: @{username}…"):
                rows, err = tiktok.collect(
                    token=tt_token,
                    username=username,
                    max_videos=int(tt_max_videos),
                )
                if err:
                    errors.append(err)
                all_rows.extend(rows)
    elif tt_accounts and not tt_token:
        errors.append("⚠️ Указаны TikTok-аккаунты, но не введён EnsembleData токен.")

    st.session_state["results"] = all_rows
    st.session_state["errors"]  = errors

# ── Вывод результатов ─────────────────────────────────────────────────────────
if st.session_state.get("results") is not None:
    errors   = st.session_state.get("errors", [])
    all_rows = st.session_state["results"]

    for err in errors:
        st.warning(err)

    if not all_rows:
        st.error("Данных нет — проверьте токены и имена аккаунтов.")
    else:
        st.subheader(f"Результат: {len(all_rows)} записей")
        st.dataframe(all_rows, width="stretch")

        col1, col2 = st.columns(2)
        with col1:
            csv_data = rows_to_csv(all_rows)
            st.download_button(
                label="⬇️ Скачать CSV",
                data=csv_data.encode("utf-8-sig"),
                file_name="social_stats.csv",
                mime="text/csv",
                width="stretch",
            )
        with col2:
            if st.button("✨ Новый поиск", width="stretch"):
                st.session_state["results"] = None
                st.session_state["errors"]  = []
                st.rerun()
