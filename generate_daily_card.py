# -*- coding: utf-8 -*-
"""
每朝簡報卡片生成器（雲端版）
====================
數據來源（全部官方、免費、毋須登記）：
  - 香港天文台開放數據 API：現時溫度/濕度/紫外線 + 明日預測
  - 運輸署 JTIS 行車時間顯示器（每 2 分鐘更新）：過海隧道行車時間

跨平台字體：Windows 用微軟正黑體；Linux（GitHub Actions）用 Noto Sans CJK。
輸出：
  - output/daily_card_YYYYMMDD.png（1080 x 1440）
  - output/message.txt（WhatsApp 訊息文字，連圖片連結）
"""
import io
import os
import sys
import datetime
import requests
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

# ---- 設定 ----
FONT_CANDIDATES = [
    # (regular, bold)
    (r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\msjhbd.ttc"),                          # Windows 微軟正黑體
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),  # Linux Noto CJK
]

HKO_RHRREAD = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
HKO_FND = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=tc"
JTIS_XML = "https://resource.data.one.gov.hk/td/jss/Journeytimev2.xml"
HKO_ICON = "https://www.hko.gov.hk/images/HKOWxIconOutline/pic{code}.png"

# 過海隧道起點：H4 = 黃泥涌道北行近皇后大道東（灣仔），三隧齊全
JTIS_VANTAGE = "H4"
TUNNELS = [("CH", "紅隧"), ("EH", "東隧"), ("WH", "西隧")]
TUNNEL_STATUS = {1: "塞車", 2: "繁忙", 3: "暢通"}

BG = (10, 32, 58)
CARD = (16, 48, 84)
INK = (255, 255, 255)
INK_SUB = (155, 190, 225)
ACCENT = (89, 160, 224)
TRAFFIC_COLOUR = {1: (226, 75, 74), 2: (239, 159, 39), 3: (29, 158, 117)}


def resolve_fonts():
    for reg, bold in FONT_CANDIDATES:
        if os.path.exists(reg):
            return reg, (bold if os.path.exists(bold) else reg)
    raise RuntimeError("搵唔到中文字體——GitHub Actions 要先 apt-get install fonts-noto-cjk")


def fetch_json(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def get_weather():
    d = fetch_json(HKO_RHRREAD)
    temp = next(x for x in d["temperature"]["data"] if x["place"] == "香港天文台")
    hum = d["humidity"]["data"][0]
    uv = d.get("uvindex", {}).get("data", [])
    uv = next((x for x in uv if x["place"] == "京士柏"), None)
    icon_code = d.get("icon", [None])[0]
    return {
        "temp": temp["value"],
        "humidity": hum["value"],
        "uv": uv["value"] if uv else None,
        "uv_desc": uv["desc"] if uv else "",
        "icon": icon_code,
    }


def get_tomorrow_forecast():
    d = fetch_json(HKO_FND)
    w = d["weatherForecast"][0]
    return {
        "date": w["forecastDate"],
        "min": w["forecastMintemp"]["value"],
        "max": w["forecastMaxtemp"]["value"],
        "psr": w.get("PSR", ""),
    }


def get_traffic():
    r = requests.get(JTIS_XML, timeout=30)
    r.raise_for_status()
    ns = {"t": "http://data.one.gov.hk/td"}
    root = ET.fromstring(r.content)
    out = {}
    for jt in root.findall("t:jtis_journey_time", ns):
        d = {c.tag.split("}")[1]: c.text for c in jt}
        if d["LOCATION_ID"] == JTIS_VANTAGE and d["JOURNEY_TYPE"] == "1":
            out[d["DESTINATION_ID"]] = (int(d["JOURNEY_DATA"]), int(d["COLOUR_ID"]))
    return out


def fetch_icon(code):
    if not code:
        return None
    try:
        r = requests.get(HKO_ICON.format(code=code), timeout=30)
        if r.status_code == 200 and r.content:
            return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        pass
    return None


def font(path_reg, path_bold, size, bold=False):
    return ImageFont.truetype(path_bold if bold else path_reg, size)


def generate():
    wx = get_weather()
    fnd = get_tomorrow_forecast()
    traffic = get_traffic()
    icon = fetch_icon(wx["icon"])
    reg, bold = resolve_fonts()

    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    today = datetime.date.today()

    # ---- 頂部：日期 ----
    weekdays = "一二三四五六日"
    date_str = f"{today.month}月{today.day}日 星期{weekdays[today.weekday()]}"
    draw.text((80, 72), date_str, font=font(reg, bold, 52, True), fill=INK)
    draw.text((80, 148), "每朝簡報", font=font(reg, bold, 30), fill=ACCENT)
    draw.line([(80, 214), (W - 80, 214)], fill=(35, 78, 124), width=3)

    # ---- 主卡：現時天氣 ----
    y0 = 250
    draw.rounded_rectangle((80, y0, W - 80, y0 + 400), radius=28, fill=CARD)
    if icon:
        icon = icon.resize((300, 300))
        img.paste(icon, (W - 400, y0 + 50), icon)
    draw.text((120, y0 + 60), f'{wx["temp"]}°C', font=font(reg, bold, 150, True), fill=INK)
    draw.text((120, y0 + 250), "香港天文台・現時", font=font(reg, bold, 28), fill=INK_SUB)
    x = 120
    draw.text((x, y0 + 308), "相對濕度", font=font(reg, bold, 28), fill=INK_SUB)
    draw.text((x + 130, y0 + 308), f'{wx["humidity"]}%', font=font(reg, bold, 30, True), fill=INK)
    if wx["uv"] is not None:
        draw.text((x + 440, y0 + 308), "紫外線", font=font(reg, bold, 28), fill=INK_SUB)
        draw.text((x + 570, y0 + 308), f'{wx["uv"]}（{wx["uv_desc"]}）', font=font(reg, bold, 30, True), fill=INK)

    # ---- 明日預測卡 ----
    y1 = 690
    draw.rounded_rectangle((80, y1, W - 80, y1 + 210), radius=28, fill=CARD)
    draw.text((120, y1 + 36), "明日預測", font=font(reg, bold, 32, True), fill=ACCENT)
    draw.text((120, y1 + 96), f'{fnd["min"]} – {fnd["max"]}°C', font=font(reg, bold, 64, True), fill=INK)
    draw.text((120, y1 + 168), f'降雨機會：{fnd["psr"]}', font=font(reg, bold, 28), fill=INK_SUB)

    # ---- 過海隧道卡 ----
    y2 = 940
    draw.rounded_rectangle((80, y2, W - 80, y2 + 330), radius=28, fill=CARD)
    draw.text((120, y2 + 36), "過海隧道・行車時間", font=font(reg, bold, 32, True), fill=ACCENT)
    draw.text((120, y2 + 82), "起點：黃泥涌道（灣仔）", font=font(reg, bold, 24), fill=INK_SUB)
    col_w = (W - 160 - 80) // 3
    for i, (tid, name) in enumerate(TUNNELS):
        mins, colour = traffic.get(tid, (None, None))
        cx = 120 + i * (col_w + 20)
        cy = y2 + 150
        draw.rounded_rectangle((cx - 20, cy - 20, cx + col_w - 20, cy + 130), radius=20, fill=(13, 40, 70))
        draw.text((cx, cy), name, font=font(reg, bold, 34, True), fill=INK)
        if mins is not None:
            draw.text((cx, cy + 56), f"{mins} 分鐘", font=font(reg, bold, 30), fill=INK)
            if colour in TRAFFIC_COLOUR:
                draw.ellipse((cx + col_w - 70, cy + 66, cx + col_w - 46, cy + 90), fill=TRAFFIC_COLOUR[colour])
        else:
            draw.text((cx, cy + 56), "－", font=font(reg, bold, 30), fill=INK_SUB)

    # ---- 底部 ----
    draw.text((80, H - 92), "資料來源：香港天文台・運輸署 JTIS（每 2 分鐘更新）", font=font(reg, bold, 24), fill=INK_SUB)
    now = datetime.datetime.now().strftime("%H:%M")
    draw.text((80, H - 56), f"自動生成於 {now}", font=font(reg, bold, 24), fill=INK_SUB)

    os.makedirs("output", exist_ok=True)
    fname = f"daily_card_{today.strftime('%Y%m%d')}.png"
    out = os.path.join("output", fname)
    img.save(out, "PNG")
    img.save(os.path.join("output", "latest.png"), "PNG")  # 固定檔名，供網頁同 Telegram 使用
    print("saved:", out)

    # ---- 產生 WhatsApp 訊息文字 ----
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    img_url = f"https://raw.githubusercontent.com/{repo}/main/output/{fname}" if repo else ""
    tunnel_parts = []
    for tid, name in TUNNELS:
        mins, colour = traffic.get(tid, (None, None))
        if mins is None:
            tunnel_parts.append(f"{name}－")
        else:
            tunnel_parts.append(f"{name}{mins}分({TUNNEL_STATUS.get(colour, '')})")
    lines = [
        f"☀️ 每朝簡報 {date_str}",
        f"🌡 現在 {wx['temp']}°C・濕度 {wx['humidity']}%",
    ]
    if wx["uv"] is not None:
        lines.append(f"🔆 紫外線 {wx['uv']}（{wx['uv_desc']}）")
    lines.append(f"📈 明日 {fnd['min']}–{fnd['max']}°C・降雨{fnd['psr']}")
    lines.append("🚗 過海（灣仔起）：" + "・".join(tunnel_parts))
    if img_url:
        lines.append(f"📊 {img_url}")
    msg = "\n".join(lines)
    with open("output/message.txt", "w", encoding="utf-8") as f:
        f.write(msg)
    print("--- message ---")
    print(msg)
    return out


if __name__ == "__main__":
    generate()
