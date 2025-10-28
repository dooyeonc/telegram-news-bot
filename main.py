import os, re, requests, asyncio
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "@newsnissue"  # 채널 아이디

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
    "KBS", "MBC", "SBS", "JTBC", "TV조선", "매일경제", "한국경제", "서울경제", "헬스조선"
]

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

def normalize_link(href):
    if href.startswith("/"):
        return "https://n.news.naver.com" + href
    return href

def get_real_link(link, press_code, title):
    try:
        html = requests.get(link, headers=UA, timeout=10).text
        sid_match = re.search(r"sid=(10[1-5])", html)
        art_match = re.search(r"/article/(\d{3})/(\d+)", link)
        if sid_match and art_match:
            sid = sid_match.group(1)
            p, aid = art_match.groups()
            return f"https://n.news.naver.com/mnews/article/{p}/{aid}?sid={sid}"
    except:
        pass
    return link

def fetch(press, code, date_str):
    url = f"https://media.naver.com/press/{code}/ranking?type=popular&date={date_str}"
    try:
        soup = BeautifulSoup(requests.get(url, headers=UA, timeout=10).text, "html.parser")
        a = soup.find("a", href=re.compile(rf"/article/{code}/\d+"))
        if not a:
            return press, []
        title = re.sub(r"^\d+\s*", "", a.get_text(strip=True))
        link = normalize_link(a["href"])
        real = get_real_link(link, code, title)
        return press, [{"title": title, "link": real}]
    except:
        return press, []

def build_msg(news):
    now = datetime.utcnow() + timedelta(hours=9)
    date = now.strftime("%m/%d")
    period = "오전" if now.hour < 12 else "오후"
    msg = [f"[{date} {period} 많이 본 뉴스 브리핑]\n"]
    for p in ORDER:
        arts = news.get(p, [])
        if not arts:
            msg.append(f"[{p}] ⚠️ 인기 기사 없음")
        else:
            msg.append(f"[{p}]")
            msg.append(arts[0]["title"])
            msg.append(arts[0]["link"])
        msg.append("")
    return "\n".join(msg).strip()

async def send(msg):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

def main():
    date_str = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y%m%d")
    all_news = {}
    for n, c in PRESS.items():
        p, i = fetch(n, c, date_str)
        all_news[p] = i
    msg = build_msg(all_news)
    asyncio.run(send(msg))

if __name__ == "__main__":
    main()
