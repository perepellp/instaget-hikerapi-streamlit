import io
import csv
import streamlit as st
from hikerapi import Client

st.set_page_config(page_title="Instagram Stats", page_icon="📊", layout="centered")

st.title("📊 Instagram Stats via HikerAPI")
st.caption("Собирает посты и Reels пользователя: лайки, комментарии, подписи.")

# ── Форма с запоминанием через session_state ──────────────────────────────────

with st.form("params"):
    token = st.text_input(
        "🔑 HikerAPI Token",
        value=st.session_state.get("token", ""),
        type="password",
        help="Получить токен: https://hikerapi.com (100 бесплатных запросов)",
    )
    username = st.text_input(
        "👤 Instagram username",
        value=st.session_state.get("username", ""),
        placeholder="например: instagram",
    )
    col1, col2 = st.columns(2)
    max_posts = col1.number_input(
        "📷 Постов",
        min_value=1, max_value=100,
        value=st.session_state.get("max_posts", 20),
    )
    max_reels = col2.number_input(
        "🎬 Reels",
        min_value=1, max_value=100,
        value=st.session_state.get("max_reels", 20),
    )
    submitted = st.form_submit_button("🚀 Собрать данные", use_container_width=True)

# ── Логика ────────────────────────────────────────────────────────────────────

def fetch_chunk(method, user_id, amount):
    """Собирает данные постранично."""
    items, end_cursor = [], None
    while len(items) < amount:
        result = method(user_id=user_id, end_cursor=end_cursor)
        if isinstance(result, (list, tuple)) and len(result) == 2:
            chunk, end_cursor = result
        elif isinstance(result, dict):
            chunk = result.get("items", [])
            end_cursor = result.get("next_max_id") or result.get("end_cursor")
        else:
            break
        if not chunk:
            break
        items.extend(chunk)
        if not end_cursor:
            break
    return items[:amount]


def get_caption(item):
    cap = item.get("caption")
    if isinstance(cap, dict):
        return cap.get("text", "") or ""
    return cap or ""


def items_to_rows(items, media_type):
    rows = []
    for item in items:
        rows.append({
            "Тип": media_type,
            "Дата": str(item.get("taken_at", ""))[:10],
            "Лайки": item.get("like_count", 0),
            "Комментарии": item.get("comment_count", 0),
            "Подпись": get_caption(item).replace("\n", " ")[:200],
            "Shortcode": item.get("code", ""),
        })
    return rows


def rows_to_csv(rows):
    buf = io.StringIO()
    if not rows:
        return buf.getvalue()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


if submitted:
    # Запоминаем параметры
    st.session_state["token"]     = token
    st.session_state["username"]  = username
    st.session_state["max_posts"] = max_posts
    st.session_state["max_reels"] = max_reels

    if not token or not username:
        st.error("Заполните токен и username.")
        st.stop()

    cl = Client(token=token)

    with st.spinner("Получаем профиль…"):
        try:
            user = cl.user_by_username_v1(username)
        except Exception as e:
            st.error(f"Ошибка: {e}")
            st.stop()

    user_id = str(user.get("pk") or user.get("id", ""))
    st.success(
        f"**{user.get('full_name', username)}** (@{username}) — "
        f"{user.get('follower_count', 0):,} подписчиков"
    )

    all_rows = []

    with st.spinner(f"Загружаем посты (до {max_posts})…"):
        try:
            posts = fetch_chunk(cl.user_medias_chunk_v1, user_id, int(max_posts))
            all_rows += items_to_rows(posts, "Пост")
        except Exception as e:
            st.warning(f"Посты: {e}")

    with st.spinner(f"Загружаем Reels (до {max_reels})…"):
        try:
            reels = fetch_chunk(cl.user_clips_chunk_v1, user_id, int(max_reels))
            all_rows += items_to_rows(reels, "Reels")
        except Exception as e:
            st.warning(f"Reels: {e}")

    if not all_rows:
        st.error("Данных нет — возможно, аккаунт закрытый или токен недействителен.")
        st.stop()

    st.subheader(f"Результат: {len(all_rows)} записей")
    st.dataframe(all_rows, use_container_width=True)

    csv_data = rows_to_csv(all_rows)
    st.download_button(
        label="⬇️ Скачать CSV",
        data=csv_data.encode("utf-8-sig"),  # utf-8-sig для корректного открытия в Excel
        file_name=f"{username}_stats.csv",
        mime="text/csv",
        use_container_width=True,
    )
