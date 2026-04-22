"""
VK collector via official API (service token).
Возвращает унифицированный список строк для таблицы.
"""

import requests
from datetime import datetime


API_VERSION = "5.199"
BASE_URL = "https://api.vk.com/method/"


def _api_call(method: str, params: dict, token: str) -> dict:
    params.update({
        "access_token": token,
        "v": API_VERSION,
    })
    response = requests.get(BASE_URL + method, params=params).json()
    return response


def _fetch_posts(owner_id: str, count: int, token: str) -> list:
    items = []
    offset = 0
    batch_size = 100

    while len(items) < count:
        resp = _api_call("wall.get", {
            "owner_id": owner_id,
            "count": min(batch_size, count - len(items)),
            "offset": offset,
        }, token)

        if "error" in resp:
            break

        chunk = resp.get("response", {}).get("items", [])
        if not chunk:
            break

        items.extend(chunk)
        offset += len(chunk)

    return items[:count]


def _get_views(item: dict) -> int:
    views = item.get("views")
    if isinstance(views, dict):
        return views.get("count", 0)
    return 0

def _extract_video_description(item: dict) -> str:
    attachments = item.get("attachments", [])
    for att in attachments:
        if att.get("type") == "video":
            video = att.get("video", {})
            return video.get("description", "") or ""
    return ""

def _build_wall_url(owner_id: str, post_id: int) -> str:
    return f"https://vk.com/wall{owner_id}_{post_id}"

def _to_rows(items: list, username: str, owner_id: str) -> list:
    rows = []

    for item in items:
        text = item.get("text", "") or ""
        video_desc = _extract_video_description(item)

        full_text = (text + " " + video_desc).strip()

        rows.append({
            "Сервис": "VK",
            "Аккаунт": f"@{username}",
            "Тип": "Пост",
            "Дата": datetime.fromtimestamp(item.get("date", 0)).strftime("%Y-%m-%d"),
            "Лайки": item.get("likes", {}).get("count", 0),
            "Комментарии": item.get("comments", {}).get("count", 0),
            "Просмотры": item.get("views", {}).get("count", 0),
            "Описание": full_text.replace("\n", " ")[:200],
            "Ссылка": _build_wall_url(owner_id, item.get("id")),
        })

    return rows


def _resolve_username(username: str, token: str) -> str:
    """
    Преобразует username (screen_name) в owner_id
    """
    resp = _api_call("utils.resolveScreenName", {
        "screen_name": username
    }, token)

    if "error" in resp:
        raise Exception(resp["error"]["error_msg"])

    data = resp.get("response", {})
    obj_id = data.get("object_id")
    obj_type = data.get("type")

    if not obj_id:
        raise Exception("Не удалось определить ID")

    # группы — отрицательный ID
    if obj_type == "group":
        return f"-{obj_id}"

    return str(obj_id)


def check_api_error(response: dict) -> str | None:
    if "error" in response:
        return f"❌ VK API: {response['error'].get('error_msg', 'Неизвестная ошибка')}"
    return None


def collect(token: str, username: str, max_posts: int) -> tuple[list, str]:
    """
    Собирает посты VK (видео отдельно не обрабатываются).
    Возвращает (rows, error_message).
    """
    try:
        owner_id = _resolve_username(username, token)
    except Exception as e:
        return [], f"❌ VK @{username}: {e}"

    rows = []

    print("owner_id:",owner_id)

    try:
        posts = _fetch_posts(owner_id, max_posts, token)
        rows += _to_rows(posts, username, owner_id)
    except Exception as e:
        return [], f"❌ VK @{username}: {e}"

    # VK не разделяет посты и reels аналогично Instagram
    # max_videos игнорируем (или можно расширить через video.get)

    return rows, ""