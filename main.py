import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
import asyncio
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "@newsnissue"

PRESS = {
    "연합뉴스": "001", "YTN": "052", "조선일보": "023", "중앙일보": "025", "동아일보": "020",
    "국민일보": "005", "한국일보": "469", "서울신문": "081", "한겨레": "028", "경향신문": "032",
    "문화일보": "021", "뉴시스": "003", "뉴스1": "421", "KBS": "056", "MBC": "214",
    "SBS": "055", "JTBC": "437", "TV조선": "448", "매일경제": "009",
    "한국경제": "015", "서울경제": "011", "헬스조선": "346"
}

ORDER = [
    "연합뉴스", "YTN", "조선일보", "중앙일보", "동아일보", "국민일보", "한국일보",
    "서울신문", "한겨레", "경향신문", "문화일보", "뉴시스", "뉴스1",
    "KBS", "MBC", "SBS", "JTBC", "TV조선", "매일경제",
    "한국경제", "서울경제", "헬스조선"
]

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}
TIMEOUT = 15


def normalize_link(href: str):
    if href.startswith("/"):
        return "https://n.news.naver.com" + href
    if href.startswith("http"):
        return href
    return "https://n.news.naver.com/" + href.lstrip("/")


def extract_real_sid_link(html, press_code, ranking_link):
    """HTML 내에서 sid=가 포함된 진짜 기사 주소를 찾아냄."""
    soup = BeautifulSoup(html, "html.parser")
    og = soup.find("meta", property="og:url")
    if og and og.get("content") and f"/article/{press_code}/" in og["content"]:
        return og["content"]
    canon = soup.find("link", rel="canonical")
    if canon and canon.get("href") and f"/article/{press_code}/" in canon["href"]:
        return canon["href"]
    sid_match = re.search(r"sid=(10[1-5])", html)
    art_match = re.search(r"/article/(\d{3})/(\d+)", ranking_link)
    if sid_match and art_match:
        sid = sid_match.group(1)
        p, aid = art_match.groups()
        return f"https://n.news.naver.com/mnews/article/{p}/{aid}?sid={sid}"
    return None


def get_real_article_link(ranking_link, press_code, title):
    """본문 열어서 sid 주소 찾기 + 검색 fallback"""
    try:
        html = requests.get(ranking_link, headers=UA, timeout=8).text
        real = extract_real_sid_link(html, press_code, ranking_link)
        if real:
            return real
    except Exception:
        pass

    # fallback: 네이버 뉴스 검색
    try:
        search_url = f"https://search.naver.com/search.naver?where=news&query={requests.utils.quote(title)}"
        s_html = requests.get(search_url, headers=UA, timeout=8).text
        soup = BeautifulSoup(s_html, "html.parser")
        for a in soup.find_all("a", href=re.compile(rf"https://n\.news\.naver\.com/(mnews/)?article/{press_code}/\d+")):
            return a["href"]
    except Exception:
        pass

    return ranking_link


def clean_title(text: str) -> str:
    """제목에서 순위 숫자/영상/조회수 등 노이즈 제거"""
    t = text.strip()
    # 숫자로 시작하는 제목(예: 40대 같은...) 보존 처리
    t = re.sub(r"(?<=\s)\d+\s*", "", t)
    t = re.sub(r"\[[^\]]*영상[^\]]*\]", "", t)
    t = re.sub(r"\([^)]*영상[^)]*\)", "", t)
    t = re.sub(r"조회수\s*\d[\d,]*", "", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def fetch_news_by_press(press_name, code, date_str):
    """언론사별 상위 기사 1~2개 가져오기"""
    url = f"https://media.naver.com/press/{code}/ranking?type=popular&date={date_str}"
    try:
        html = requests.get(url, headers=UA, timeout=TIMEOUT).text
        soup = BeautifulSoup(html, "html.parser")

        a_tags = soup.find_all("a", href=re.compile(rf"/article/{code}/\d+"))
        items, seen = [], set()

        for a in a_tags:
            href = a.get("href", "")
            m = re.search(rf"/article/{code}/(\d+)", href)
            if not m:
                continue
            aid = m.group(1)
            if aid in seen:
                continue
            seen.add(aid)

            title = clean_title(a.get_text(strip=True))
            if not title:
                continue

            link = normalize_link(href)
            real_link = get_real_article_link(link, code, title)
            items.append({"title": title, "link": real_link})

            if len(items) >= 2:
                break

        return press_name, items
    except Exception as e:
        print(f"⚠️ {press_name} 오류: {e}")
        return press_name, []


def build_message(news_dict):
    now = datetime.utcnow() + timedelta(hours=9)
    date_str = now.strftime("%m/%d")
    lines = [f"<b>{date_str} 많이 본 뉴스 브리핑</b>\n"]

    for press in ORDER:
        arts = news_dict.get(press, [])
        if not arts:
            lines.append(f"[{press}] ⚠️ 인기 기사 없음")
            continue
        lines.append(f"[{press}]")
        for art in arts[:1]:
            lines.append(f"{art['title']}")
            lines.append(art["link"])
        lines.append("")

    return "\n".join(lines).rstrip()


async def send_to_telegram(text):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN이 없습니다.")
        return
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


def main():
    date_str = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y%m%d")
    all_news = {}
    for name, code in PRESS.items():
        press, items = fetch_news_by_press(name, code, date_str)
        all_news[press] = items
    msg = build_message(all_news)
    asyncio.run(send_to_telegram(msg))
    print("✅ Sent")


if __name__ == "__main__":
    main()