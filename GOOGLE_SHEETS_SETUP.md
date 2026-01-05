# Google Sheets 匯入設定指南

## 📋 前置準備

### 1. 取得 Google Sheets API 憑證

#### 步驟 A：建立 Google Cloud 專案
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 專案名稱可以叫 "財務月報系統"

#### 步驟 B：啟用 Google Sheets API
1. 在左側選單選擇「API 和服務」→「程式庫」
2. 搜尋「Google Sheets API」
3. 點擊「啟用」
4. 同樣啟用「Google Drive API」

#### 步驟 C：建立 Service Account
1. 前往「API 和服務」→「憑證」
2. 點擊「建立憑證」→「服務帳戶」
3. 填寫服務帳戶名稱，例如：「monthly-report-importer」
4. 點擊「建立並繼續」
5. 角色選擇「編輯者」
6. 點擊「完成」

#### 步驟 D：下載 JSON 憑證檔
1. 在「服務帳戶」列表中，點擊剛建立的帳戶
2. 切換到「金鑰」頁籤
3. 點擊「新增金鑰」→「建立新金鑰」
4. 選擇「JSON」格式
5. 下載的檔案重新命名為 `google_credentials.json`
6. 將檔案放到專案根目錄

### 2. 共享 Google Sheets

**重要：** 必須將你的 Google Sheets 與 Service Account 共享！

1. 開啟 `google_credentials.json`，找到 `client_email` 欄位
2. 複製該 email 地址（格式類似：xxx@xxx.iam.gserviceaccount.com）
3. 開啟你的 Google Sheets
4. 點擊右上角「共用」按鈕
5. 貼上 Service Account 的 email
6. 權限設為「編輯者」
7. 點擊「傳送」

**對兩個 Sheets 都要執行此步驟：**
- 月報內容 Sheet
- 同事名單 Sheet

---

## 🔧 安裝相依套件

```bash
pip install gspread oauth2client sqlalchemy psycopg2-binary
```

---

## 📝 設定 Sheet ID

從你的 Google Sheets 網址中提取 Sheet ID：

```
https://docs.google.com/spreadsheets/d/[這裡是 Sheet ID]/edit
```

**你的 Sheet IDs：**
- 月報內容：`1GIRUkooefilHna2CB63yoIhvqDrajLhCmhr9iUh2zGY`
- 同事名單：`1_jaR8280igaRBwVnTS0Tx9eyauVqkSlpzEiKVZ5c9R4`

---

## ⚙️ 設定資料庫連線

### 本地測試（SQLite）
```bash
# 不需要設定，會自動使用 SQLite
python import_from_sheets.py
```

### 正式環境（PostgreSQL）
```bash
# 設定環境變數
export DATABASE_URL="postgresql://username:password@hostname:port/database"

# 執行匯入
python import_from_sheets.py
```

---

## 🚀 執行匯入

```bash
cd "/mnt/c/Users/alex_chen/Desktop/vide coding/dynamic website-monthly report"
python import_from_sheets.py
```

---

## ❓ 常見問題

### Q: 出現「403 Forbidden」錯誤
**A:** 請確認已將 Google Sheets 與 Service Account 的 email 共享

### Q: 出現「gspread.exceptions.APIError」
**A:** 檢查是否已啟用 Google Sheets API 和 Google Drive API

### Q: 資料沒有正確匯入
**A:** 請確認 Google Sheets 的欄位名稱與程式中定義的相符

---

## 📊 Google Sheets 欄位格式要求

### 月報內容 Sheet
請確保第一列（標題列）包含以下欄位：
- `category` - 類別（completed, highlights, tax_info, calendar, birthday, quote）
- `title` - 標題
- `content` - 內容
- `date_info` - 日期資訊
- `order_num` - 排序編號

### 同事名單 Sheet
請確保第一列（標題列）包含以下欄位：
- `name` - 姓名
- `position` - 職位
- `department` - 部門
- `birthday` - 生日
- `email` - Email

---

## 🔄 定期自動匯入

如果想要定期自動執行匯入，可以使用 cron（Linux）或 Task Scheduler（Windows）：

### Linux/Mac (cron)
```bash
# 每天凌晨 2 點執行
0 2 * * * cd /path/to/project && python import_from_sheets.py
```

### Windows (Task Scheduler)
1. 開啟「工作排程器」
2. 建立基本工作
3. 觸發程序設定為「每天」
4. 動作選擇「啟動程式」
5. 程式選擇 Python，引數填入腳本路徑
