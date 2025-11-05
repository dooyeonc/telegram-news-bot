def build_message(news_dict):
    now = datetime.utcnow() + timedelta(hours=9)
    date_str = now.strftime("%m/%d")
    lines = [f"<b>{date_str} 많이 본 뉴스 브리핑</b>\n"]  # ✅ 오전/오후 제거

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