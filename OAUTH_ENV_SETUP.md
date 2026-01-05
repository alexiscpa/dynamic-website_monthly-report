# 使用 .env 設定 OAuth 2.0 的完整指南

## 📋 概述

本指南將教你如何在 `.env` 檔案中設定 Google OAuth 2.0 憑證。

---

## 🔑 需要填入的資訊

在 `.env` 檔案中，你需要填入兩個值：

```bash
GOOGLE_CLIENT_ID=你的用戶端ID
GOOGLE_CLIENT_SECRET=你的用戶端密鑰
```

---

## 📥 如何從 Google Cloud Console 取得這些值

### 步驟 1：進入 Google Cloud Console

1. 前往：https://console.cloud.google.com/
2. 登入你的 Google 帳號
3. 選擇或建立專案（如果還沒有的話）

---

### 步驟 2：啟用 Gmail API

1. 在左側選單：點選「**API 和服務**」→「**程式庫**」
2. 搜尋：`Gmail API`
3. 點選「**Gmail API**」
4. 點選「**啟用**」

---

### 步驟 3：設定 OAuth 同意畫面

1. 左側選單：「**API 和服務**」→「**OAuth 同意畫面**」
2. 使用者類型：選擇「**外部**」（個人 Gmail）或「**內部**」（Google Workspace）
3. 點選「**建立**」
4. 填寫必要資訊：
   - **應用程式名稱**：`財務處月報系統`
   - **使用者支援電子郵件**：選擇你的 Gmail
   - **開發人員聯絡資訊**：填入你的 Email
5. 點選「**儲存並繼續**」
6. **範圍（Scopes）**：
   - 點選「**新增或移除範圍**」
   - 搜尋：`gmail.send`
   - 勾選：`https://www.googleapis.com/auth/gmail.send`
   - 點選「**更新**」
   - 點選「**儲存並繼續**」
7. **測試使用者**：
   - 點選「**+ ADD USERS**」
   - 輸入你的 Gmail 帳號
   - 點選「**儲存並繼續**」

---

### 步驟 4：建立 OAuth 用戶端 ID

1. 左側選單：「**API 和服務**」→「**憑證**」
2. 點選上方「**+ 建立憑證**」→「**OAuth 用戶端 ID**」
3. **應用程式類型**：選擇「**桌面應用程式**」
4. **名稱**：`月報郵件服務`
5. 點選「**建立**」

---

### 步驟 5：複製 Client ID 和 Client Secret

建立完成後，會出現一個對話框：

#### 📋 複製用戶端 ID (Client ID)

1. 在對話框中找到「**用戶端 ID**」
2. 點選右側的「複製」圖示
3. 用戶端 ID 格式類似：
   ```
   123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
   ```
4. **暫時貼到記事本中**

#### 📋 複製用戶端密鑰 (Client Secret)

1. 在對話框中找到「**用戶端密鑰**」
2. 點選右側的「複製」圖示
3. 用戶端密鑰格式類似：
   ```
   GOCSPX-abcdefghijklmnopqrstuvwx
   ```
4. **暫時貼到記事本中**

5. 點選「**確定**」關閉對話框

---

### 步驟 6：如果忘記複製或想重新查看

如果你關閉了對話框，還可以這樣找回：

1. 在「**憑證**」頁面
2. 找到「**OAuth 2.0 用戶端 ID**」區塊
3. 找到你剛建立的「月報郵件服務」
4. 點選右側的 **鉛筆圖示（編輯）**
5. 在編輯頁面中：
   - **用戶端 ID**：顯示在上方，可以複製
   - **用戶端密鑰**：顯示在「用戶端密鑰」區塊，可以複製

---

## ✏️ 填入 .env 檔案

現在打開專案中的 `.env` 檔案，填入你剛才複製的值：

### 範例（請替換為你的實際值）：

```bash
# ==================== Google OAuth 2.0 設定 ====================
# Google Client ID（用戶端 ID）
GOOGLE_CLIENT_ID=123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com

# Google Client Secret（用戶端密鑰）
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwx
```

### ⚠️ 注意事項：

1. **等號兩邊不要有空格**
   - ✅ 正確：`GOOGLE_CLIENT_ID=123456...`
   - ❌ 錯誤：`GOOGLE_CLIENT_ID = 123456...`

2. **不要加引號**
   - ✅ 正確：`GOOGLE_CLIENT_ID=123456...`
   - ❌ 錯誤：`GOOGLE_CLIENT_ID="123456..."`

3. **完整複製整個 ID 和 Secret**
   - Client ID 很長，確保完整複製
   - Client Secret 也要完整複製

4. **儲存檔案**
   - 確認檔案名稱是 `.env`（不是 `.env.txt`）

---

## 🚀 啟動系統

填入完成後，安裝套件並啟動系統：

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 啟動系統

```bash
uvicorn main:app --reload
```

### 3. OAuth 認證流程

首次啟動時：

1. **瀏覽器會自動開啟**（或終端機會顯示一個 URL）
2. 選擇你的 Gmail 帳號
3. 可能會看到警告：「**Google 尚未驗證這個應用程式**」
   - 點選「**進階**」
   - 點選「**前往財務處月報系統（不安全）**」
4. 授權畫面：
   - 勾選：「**傳送電子郵件**」權限
   - 點選「**繼續**」
5. 看到「**驗證成功**」訊息
6. 回到終端機，應該會看到：
   ```
   📝 使用 .env 中的 OAuth 設定
   ✅ OAuth 認證成功（使用 .env 設定）
   ✅ 已儲存認證至 token.json
   ✅ Gmail API 服務已初始化
   ```

### 4. 完成！

系統會自動建立 `token.json` 檔案，之後就不需要重複認證了。

---

## 🧪 測試郵件功能

```bash
python
```

```python
from email_service_oauth import email_service

# 測試發送生日賀卡
test_staff = {
    "name": "測試員工",
    "email": "你的Email@gmail.com"  # 改成你的 Email
}

result = email_service.send_birthday_card(test_staff)

if result:
    print("✅ 郵件發送成功！請檢查信箱")
else:
    print("❌ 郵件發送失敗，請檢查設定")
```

---

## 📁 檔案結構

設定完成後，你的專案目錄應該有：

```
你的專案目錄/
├── .env                       ✅ 包含 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET
├── token.json                 ✅ 首次認證後自動產生
├── main.py
├── email_service_oauth.py
├── scheduler.py
└── ...
```

**不需要** `credentials.json` 檔案（因為我們用 .env 方式）

---

## ❓ 常見問題

### Q1: 找不到用戶端 ID 和密鑰

**解決方法**：
1. 前往 Google Cloud Console
2. 左側選單：「API 和服務」→「憑證」
3. 找到你建立的 OAuth 用戶端 ID
4. 點選鉛筆圖示（編輯）
5. 就可以看到並複製 Client ID 和 Secret

---

### Q2: 錯誤訊息「invalid_client」

**原因**：Client ID 或 Secret 錯誤

**解決方法**：
1. 檢查 `.env` 中的值是否完整複製
2. 確認沒有多餘的空格或引號
3. 重新從 Google Cloud Console 複製一次

---

### Q3: 瀏覽器沒有自動開啟

**解決方法**：
1. 查看終端機顯示的 URL
2. 手動複製 URL 到瀏覽器開啟
3. 完成認證後會自動回傳

---

### Q4: 警告「Google 尚未驗證這個應用程式」

這是**正常的**！因為你的應用程式在測試階段。

**解決方法**：
1. 點選「進階」
2. 點選「前往財務處月報系統（不安全）」
3. 繼續完成授權

---

## 🔒 安全性提醒

⚠️ **重要**：
- `.env` 檔案包含敏感資訊
- 請勿分享或上傳到 Git
- 已加入 `.gitignore`，確保不會被上傳

---

## ✅ 完成！

設定完成後，你的郵件系統會：
- ✅ 使用 Gmail API + OAuth 2.0 發送郵件
- ✅ 自動在指定時間發送月報、生日賀卡、節日賀卡
- ✅ Token 自動更新，無需重複認證

有任何問題隨時詢問！
