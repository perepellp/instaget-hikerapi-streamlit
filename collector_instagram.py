"""
Instagram collector via HikerAPI.
Возвращает унифицированный список строк для таблицы.
"""
from hikerapi import Client


def _fetch_chunk(method, user_id: str, amount: int) -> list:
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


def _get_caption(item: dict) -> str:
    text = item.get("caption_text", "")
    if text:
        return text
    cap = item.get("caption")
    if isinstance(cap, dict):
        return cap.get("text", "") or ""
    return cap or ""


def _to_rows(items: list, username: str, content_type: str) -> list:
    rows = []
    for item in items:
        rows.append({
            "Сервис": "Instagram",
            "Аккаунт": f"@{username}",
            "Тип": content_type,
            "Дата": str(item.get("taken_at", ""))[:10],
            "Лайки": item.get("like_count", 0),
            "Комментарии": item.get("comment_count", 0),
            "Просмотры": item.get("view_count") or item.get("play_count") or 0,
            "Описание": _get_caption(item).replace("\n", " ")[:200],
            "Ссылка": "",
        })
    return rows


def check_api_error(response: dict) -> str | None:
    """Возвращает текст ошибки если API вернул ошибку, иначе None."""
    if isinstance(response, dict) and response.get("state") is False:
        exc = response.get("exc_type", "")
        if exc == "InsufficientFunds":
            return "❌ Недостаточно средств HikerAPI. Пополните: https://hikerapi.com/billing"
        return f"❌ HikerAPI: {response.get('error', 'Неизвестная ошибка')}"
    return None


def collect(token: str, username: str, max_posts: int, max_videos: int) -> tuple[list, str]:
    """
    Собирает посты и Reels для одного аккаунта Instagram.
    Возвращает (rows, error_message). Если ошибки нет — error_message пустой.
    """
    cl = Client(token=token)

    try:
        user = cl.user_by_username_v1(username)
    except Exception as e:
        return [], f"❌ Instagram @{username}: {e}"

    err = check_api_error(user)
    if err:
        return [], f"{err} (аккаунт @{username})"

    user_id = str(user.get("pk") or user.get("id", ""))
    rows = []

    try:
        posts = _fetch_chunk(cl.user_medias_chunk_v1, user_id, max_posts)
        rows += _to_rows(posts, username, "Пост")
    except Exception as e:
        rows += []  # не прерываем, просто пропускаем

    try:
        reels = _fetch_chunk(cl.user_clips_chunk_v1, user_id, max_videos)
        rows += _to_rows(reels, username, "Reels")
    except Exception:
        pass

    return rows, ""
