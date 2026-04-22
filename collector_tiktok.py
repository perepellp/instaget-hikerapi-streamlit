import requests
from datetime import datetime

BASE_URL = "https://ensembledata.com/apis"


def _fetch_posts(token, username, max_videos):
    collected = []
    cursor = 0
    warnings = []

    while len(collected) < max_videos:
        need = max_videos - len(collected)
        depth = max(1, min(need // 10 + 1, 5))

        params = {
            "username": username,
            "depth": depth,
            "start_cursor": cursor,
            "token": token,
        }
        try:
            res = requests.get(f"{BASE_URL}/tt/user/posts", params=params, timeout=30)
            res.raise_for_status()
            result = res.json()
        except Exception as e:
            warnings.append(f"Ошибка запроса: {e}")
            break

        # result = {"data": [...], "nextCursor": <int>}
        if not isinstance(result, dict):
            warnings.append(f"Неожиданный тип ответа: {type(result)}")
            break

        items = result.get("data", [])
        if not items:
            break

        collected.extend(items)

        next_cursor = result.get("nextCursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return collected[:max_videos], (warnings[0] if warnings else None)


def collect(token, username, max_videos=10):
    rows = []

    items, warn = _fetch_posts(token, username, max_videos)

    if not items and warn:
        return [], warn

    for item in items:
        stats = item.get("statistics", {})
        create_ts = item.get("create_time", 0)
        try:
            date_str = datetime.utcfromtimestamp(create_ts).strftime("%Y-%m-%d")
        except Exception:
            date_str = ""

        aweme_id = item.get("aweme_id", "")
        desc = item.get("desc", "")
        likes = stats.get("digg_count", 0)
        comments = stats.get("comment_count", 0)
        views = stats.get("play_count", 0)

        rows.append({
            "Сервис": "TikTok",
            "Аккаунт": username,
            "Тип": "Видео",
            "Дата": date_str,
            "Лайки": likes,
            "Комментарии": comments,
            "Просмотры": views,
            "Описание": desc,
            "Ссылка": "",
        })

    return rows, warn