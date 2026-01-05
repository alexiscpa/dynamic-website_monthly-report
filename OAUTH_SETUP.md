# Google OAuth 2.0 設定指南

## 📋 重新導向 URI 設定

在 Google Cloud Console 中，你需要填入的**已授權的重新導向 URI**：

### 開發環境（本機測試）
```
http://localhost:8080/
```

### 生產環境（如果有正式網域）
```
https://your-domain.com/oauth2callback
```

---

## 🚀 完整設定步驟

### 步驟 1：Google Cloud Console 設定

#### 1.1 建立專案
1. 前往 https://console.cloud.google.com/
2. 點選上方專案下拉選單 → 「新增專案」
3. 專案名稱：`財務處月報系統`
4. 點選「建立」

#### 1.2 啟用 Gmail API
1. 在左側選單：「API 和服務」→「程式庫」
2. 搜尋：`Gmail API`
3. 點選「Gmail API」
4. 點選「啟用」

#### 1.3 設定 OAuth 同意畫面
1. 左側選單：「API 和服務」→「OAuth 同意畫面」
2. 使用者類型：
   - 選擇「外部」（個人 Gmail 帳號）
   - 或選擇「內部」（如果是 Google Workspace）
3. 點選「建立」
4. 填寫資訊：
   - **應用程式名稱**：`財務處月報系統`
   - **使用者支援電子郵件**：選擇你的 Gmail
   - **應用程式標誌**：可略過
   - **開發人員聯絡資訊**：填入你的 Email
5. 點選「儲存並繼續」
6. **範圍（Scopes）**：
   - 點選「新增或移除範圍」
   - 搜尋：`gmail.send`
   - 勾選：`https://www.googleapis.com/auth/gmail.send`
   - 點選「更新」
   - 點選「儲存並繼續」
7. **測試使用者**：
   - 點選「+ ADD USERS」
   - 輸入你的 Gmail 帳號（用來發送郵件的帳號）
   - 點選「新增」
   - 點選「儲存並繼續」
8. 點選「返回資訊主頁」

#### 1.4 建立 OAuth 用戶端 ID
1. 左側選單：「API 和服務」→「憑證」
2. 點選上方「+ 建立憑證」→「OAuth 用戶端 ID」
3. 應用程式類型：選擇「**桌面應用程式**」（重要！）
4. 名稱：`月報郵件服務`
5. 點選「建立」
6. 會出現對話框顯示「用戶端 ID」和「用戶端密鑰」
7. **點選「下載 JSON」** ← 非常重要！
8. 點選「確定」

#### 1.5 放置憑證檔案
1. 將下載的 JSON 檔案重新命名為：`credentials.json`
2. 放到專案根目錄（與 `main.py` 同一層）

```
你的專案目錄/
├── main.py
├── email_service_oauth.py
├── scheduler.py
├── credentials.json  ← 放這裡
└── ...
```

---

### 步驟 2：安裝 Python 套件

```bash
pip install -r requirements.txt
```

這會安裝以下 Google API 相關套件：
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client

---

### 步驟 3：首次 OAuth 認證

#### 3.1 啟動系統
```bash
python main.py
```

或使用 uvicorn：
```bash
uvicorn main:app --reload
```

#### 3.2 OAuth 認證流程

首次啟動時，系統會自動開啟瀏覽器進行 OAuth 認證：

1. **瀏覽器自動開啟**，顯示 Google 登入畫面
2. 選擇你的 Gmail 帳號（用來發送郵件的帳號）
3. 可能會看到警告：「Google 尚未驗證這個應用程式」
   - 點選「進階」
   - 點選「前往財務處月報系統（不安全）」
4. 授權畫面會顯示：「財務處月報系統想要存取你的 Google 帳戶」
   - 勾選：「傳送電子郵件」
   - 點選「繼續」
5. 看到「驗證成功」或「已完成授權」訊息
6. 回到終端機，應該會看到：
   ```
   ✅ OAuth 認證成功
   ✅ 已儲存認證至 token.json
   ✅ Gmail API 服務已初始化，寄件人: your-email@gmail.com
   ```

#### 3.3 認證完成

系統會自動建立 `token.json` 檔案，之後就不需要再次認證了！

```
你的專案目錄/
├── credentials.json  （OAuth 憑證）
├── token.json        （認證 token，自動產生）
└── ...
```

---

### 步驟 4：測試郵件功能

開啟 Python 互動環境：

```bash
python
```

測試發送郵件：

```python
from email_service_oauth import email_service

# 測試發送生日賀卡
test_staff = {
    "name": "測試員工",
    "email": "your-test-email@gmail.com"  # 改成你的測試 Email
}

result = email_service.send_birthday_card(test_staff)

if result:
    print("✅ 郵件發送成功！")
else:
    print("❌ 郵件發送失敗")
```

檢查你的 Email 信箱，應該會收到生日賀卡！

---

## 📁 檔案結構

```
你的專案目錄/
├── main.py                    # FastAPI 主程式
├── email_service.py           # SMTP 版本（舊的，可保留）
├── email_service_oauth.py     # OAuth 版本（新的）✨
├── scheduler.py               # 排程器（已更新使用 OAuth）
├── credentials.json           # OAuth 憑證（從 Google 下載）
├── token.json                 # 認證 token（自動產生）
├── .env                       # 環境變數
├── requirements.txt           # Python 套件清單
└── ...
```

---

## ⚙️ 排程時間表

系統啟動後，會自動在以下時間發送郵件：

| 任務 | 時間 | 對象 | 內容 |
|------|------|------|------|
| 📧 月報郵件 | 每月 1 日 09:00 | 全體同事 | 上個月的月報 |
| 🎂 生日賀卡 | 每天 08:00 | 當天壽星 | 生日祝福 |
| 🎄 聖誕賀卡 | 12/25 08:00 | 全體同事 | 聖誕祝福 |
| 🎆 新年賀卡 | 1/1 00:00 | 全體同事 | 新年祝福 |
| 🧧 農曆新年賀卡 | 農曆初一 00:00 | 全體同事 | 新年祝福 |

---

## ❓ 常見問題

### Q1: 找不到 credentials.json

**錯誤訊息**：
```
❌ 找不到 credentials.json 檔案
```

**解決方法**：
1. 確認已從 Google Cloud Console 下載 OAuth 憑證
2. 確認檔案名稱是 `credentials.json`（不是 `client_secret_xxx.json`）
3. 確認檔案在專案根目錄

---

### Q2: OAuth 認證視窗沒有開啟

**解決方法**：
1. 手動前往終端機顯示的 URL
2. 複製 URL 到瀏覽器開啟
3. 完成認證後，授權碼會自動回傳

---

### Q3: 警告「Google 尚未驗證這個應用程式」

這是**正常的**！因為你的應用程式還在測試階段。

**解決方法**：
1. 點選「進階」
2. 點選「前往財務處月報系統（不安全）」
3. 繼續完成授權

如果要移除這個警告，需要通過 Google 的應用程式審查（不必要）。

---

### Q4: token.json 過期

Token 通常可以自動更新，但如果失敗：

**解決方法**：
1. 刪除 `token.json`
2. 重新啟動系統
3. 重新進行 OAuth 認證

---

### Q5: 重新導向 URI 不符

**錯誤訊息**：
```
redirect_uri_mismatch
```

**解決方法**：
1. 確認應用程式類型選擇「**桌面應用程式**」（不是網路應用程式）
2. 桌面應用程式會自動使用 `http://localhost:8080/` 作為重新導向 URI

---

## 🔒 安全性注意事項

⚠️ **重要**：
- `credentials.json` 和 `token.json` 包含敏感資訊
- 請勿上傳至 Git 或公開分享
- 建議加入 `.gitignore`：

```bash
# 在 .gitignore 中加入
credentials.json
token.json
.env
```

---

## 🎉 完成！

設定完成後，你的系統會：
- ✅ 使用 Gmail API + OAuth 2.0 發送郵件
- ✅ 自動在指定時間發送月報、生日賀卡、節日賀卡
- ✅ Token 自動更新，無需重複認證

有任何問題隨時詢問！
