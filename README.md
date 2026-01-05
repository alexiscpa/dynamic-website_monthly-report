# 財務處自動化月報系統

企業內部財務處月報系統，使用 FastAPI + PostgreSQL 開發，可部署至 Zeabur。

## ✨ 功能特點

- **自動建立資料庫表結構**
- **啟動時自動填入初始資料**（月報內容 + 同事名單）
- **響應式電子報風格設計**
- **支援環境變數配置**
- **從 Google Sheets 匯入的真實資料**

## 📊 資料結構

### 月報內容（monthly_reports）
- `month` - 月份（格式：2026-01）
- `completed` - 上月達成工作（JSON 格式）
- `focus` - 本月工作重點（JSON 格式）
- `tax_news` - 稅務快訊（JSON 格式，5則）
- `calendar` - 行事曆（JSON 格式）
- `quotes` - 勵志金句

### 同事名單（staff）
- `id` - 員工編號
- `name` - 姓名
- `email` - 電子郵件
- `birthday` - 生日（格式：1970.1.5）

## 🚀 本地開發

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定同事資料（重要）

**方式 A：使用實際資料**
```bash
# 複製範例檔案
cp staff_data.example.json staff_data.json

# 編輯 staff_data.json，填入實際同事資料
# 注意：此檔案已加入 .gitignore，不會被提交到 Git
```

**方式 B：使用範例資料**
```bash
# 不需任何操作，系統會自動使用 staff_data.example.json
```

### 3. 啟動應用

```bash
uvicorn main:app --reload
```

系統會：
- ✅ 自動建立 `monthly_reports` 和 `staff` 資料表
- ✅ 檢查資料庫是否為空
- ✅ 如果為空，自動寫入 2026-01 月報和 10 位同事資料
- ✅ 啟動 Web 服務於 `http://localhost:8000`

### 3. 預覽頁面

開啟瀏覽器訪問：
- 首頁：`http://localhost:8000`
- API 健康檢查：`http://localhost:8000/health`
- 同事名單 API：`http://localhost:8000/api/staff`
- 月報 API：`http://localhost:8000/api/report/2026-01`

## ☁️ 部署到 Zeabur

### 方法 1：使用 GitHub（推薦）

1. **推送代碼到 GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **在 Zeabur 建立專案**
   - 前往 [Zeabur Dashboard](https://zeabur.com)
   - 點擊「New Project」
   - 連接你的 GitHub 倉庫

3. **添加 PostgreSQL 服務**
   - 在專案中點擊「Add Service」
   - 選擇「PostgreSQL」
   - Zeabur 會自動設定 `DATABASE_URL` 環境變數

4. **部署應用**
   - 添加你的 Python 應用服務
   - Zeabur 會自動檢測 `Procfile` 並部署
   - 首次啟動時會自動初始化資料庫

### 方法 2：使用 CLI

```bash
# 安裝 Zeabur CLI
npm install -g @zeabur/cli

# 登入
zeabur auth login

# 部署
zeabur deploy
```

## 📝 API 端點

### GET `/`
顯示月報首頁（HTML）

### GET `/health`
健康檢查
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### GET `/api/staff`
取得所有同事名單
```json
{
  "total": 10,
  "data": [
    {
      "id": 1,
      "name": "周渝民",
      "email": "alexiscpa@gmail.com",
      "birthday": "1970.1.5"
    }
  ]
}
```

### GET `/api/report/{month}`
取得指定月份的月報（例如：`/api/report/2026-01`）

## 🎨 視覺設計規範

### 色彩方案（CSS 變數）

- `--bg-color: #fffffe` - 背景色
- `--dark-color: #272343` - 深色文字/框線
- `--accent-color: #ffd803` - 黃色強調

### 設計特點

- 電子報風格排版
- 大標題、粗邊框、區塊化設計
- 無陰影、無漸層
- 統一使用 `2px solid #272343` 邊框
- 完整響應式設計支持

## 📋 頁面區塊

1. **Header** - 深色背景 (#272343)，黃色大標題
2. **Quote Section** - 全寬黃色區塊顯示激勵金句
3. **上月完成工作** - 兩欄佈局（左圖右文）
4. **本月工作重點** - 深框強調區塊
5. **本月重要行事曆** - 左側表格 + 右側小月曆
6. **本月壽星祝福** - 自動顯示當月生日的同事

## 🔄 更新資料

### 方式 1：直接修改 main.py
編輯 `init_db()` 函數中的資料內容，然後重新部署。

### 方式 2：使用資料庫管理工具
連接到 PostgreSQL 資料庫，直接編輯資料表內容。

### 方式 3：建立管理後台（未來功能）
可以考慮新增一個管理介面來編輯月報內容。

## 🗂️ 專案結構

```
.
├── main.py                    # FastAPI 主應用程式
├── requirements.txt           # Python 依賴套件
├── Procfile                   # Zeabur/Heroku 部署配置
├── Dockerfile                 # Docker 容器配置（可選）
├── docker-compose.yml         # Docker Compose（可選）
├── preview.html               # 靜態預覽頁面
├── README.md                  # 本文件
├── .env.example               # 環境變數範例
├── .gitignore                 # Git 忽略配置
├── GOOGLE_SHEETS_SETUP.md     # Google Sheets 設置指南
└── import_from_sheets.py      # Google Sheets 匯入腳本（可選）
```

## 🔧 環境變數

### DATABASE_URL
PostgreSQL 連接字串

**本地開發（SQLite）：**
```bash
# 不需設定，會自動使用 sqlite:///./monthly_report.db
```

**生產環境（PostgreSQL）：**
```bash
export DATABASE_URL="postgresql://username:password@hostname:port/database"
```

**Zeabur 部署：**
- 自動由 PostgreSQL 服務提供，無需手動設定

## 📦 相依套件

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

## 🎯 技術規格

- **後端框架**: FastAPI 0.109.0
- **資料庫**: PostgreSQL（生產）/ SQLite（開發）
- **ORM**: SQLAlchemy 2.0.25
- **部署平台**: Zeabur / Docker
- **Python 版本**: 3.11+

## 🐛 常見問題

### Q: 首次部署後看不到資料？
**A:** 檢查應用程式啟動日誌，確認初始化是否成功執行。

### Q: 如何修改月報內容？
**A:** 編輯 `main.py` 中 `init_db()` 函數的資料，或直接連接資料庫修改。

### Q: 壽星沒有顯示？
**A:** 系統會根據當前月份自動篩選，確認同事的生日格式正確（yyyy.m.d）。

### Q: 如何新增其他月份的月報？
**A:** 在資料庫中新增一筆 `month` 不同的記錄，或修改首頁路由讀取邏輯。

## 📧 聯絡方式

如有問題，請聯絡財務處技術支援團隊。

---

**© 2026 財務處自動化月報系統**
*Powered by FastAPI & PostgreSQL*
