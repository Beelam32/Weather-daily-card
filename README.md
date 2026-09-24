# 每朝簡報（香港天氣 + 過海交通）

每日香港時間 09:00，GitHub Actions 自動：

1. 攞香港天文台開放數據（現時溫度／濕度／紫外線＋明日預測）
2. 攞運輸署 JTIS 行車時間（紅隧／東隧／西隧，每 2 分鐘更新）
3. 用 PIL 生成一張 1080×1440 天氣交通卡 PNG
4. Commit 張卡上 `output/`
5. 用 CallMeBot 發 WhatsApp 訊息（文字摘要＋張卡嘅連結）畀你自己

## 首次設定（約 10 分鐘）

### 1. 開 GitHub repo 並推上去

```bash
git init
git add .
git commit -m "daily card bot"
git branch -M main
git remote add origin https://github.com/Beelam32/Weather-daily-card.git
git push -u origin main
```

### 2. 啟用 CallMeBot（免費，只可以發畀你自己）

1. 喺 WhatsApp 加聯絡人：**+34 684 73 40 44**（號碼可能變，以 callmebot.com 官網為準）
2. 用 WhatsApp send 呢句畀佢：`I allow callmebot to send me messages`
3. 等佢回覆：`API Activated for your phone number. Your APIKEY is xxxxxx`

### 3. 喺 repo 加 Secrets

GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**，加兩個：

| Secret 名 | 值 |
|---|---|
| `CALLMEBOT_PHONE` | 你嘅 WhatsApp 號碼（國際格式，如 `+8526xxxxxxx`） |
| `CALLMEBOT_APIKEY` | CallMeBot 回覆你嗰個 APIKEY |

### 4. 手動測試

repo → **Actions** tab → 揀 **Daily Card 09:00 HKT** → **Run workflow** → 撳一下就得。
成功嘅話：WhatsApp 會收到訊息，`output/` 會多咗張當日卡。

之後每朝 09:00 自動行，唔使理。

## 檔案結構

```
daily-card/
├── .github/workflows/daily_card.yml   # 排程 + 自動化流程
├── generate_daily_card.py             # 生成器（天文台 + JTIS + PIL）
├── requirements.txt
└── output/                            # 每日張卡（自動 commit）
```

## 自訂

- 改隧道起點：`generate_daily_card.py` 入面 `JTIS_VANTAGE`（預設 H4 灣仔黃泥涌道；
  其他選擇見運輸署 dataspec，如 H1 告士打道、K07 西九龍公路）
- 改觸發時間：`daily_card.yml` 入面 `cron`（記住係 UTC，香港 = UTC+8）
- 留意：GitHub 免費排程唔保證分秒不差，通常延遲 0–15 分鐘

## 成本

GitHub Actions 公開 repo 完全免費；CallMeBot 免費（個人用）。
