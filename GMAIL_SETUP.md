# Gmail 郵件功能設定指南

## 功能說明

本系統已整合以下自動郵件功能：

### 📧 每月月報郵件
- **排程時間**：每月第一天上午 9:00
- **收件人**：所有同事
- **內容**：上個月的月報摘要 + 完整月報連結

### 🎂 生日賀卡
- **排程時間**：每天上午 8:00 檢查
- **收件人**：當天生日的同事
- **內容**：生日祝福賀卡

### 🎊 節日賀卡
系統會在以下節日自動寄送賀卡給所有同事：
- **聖誕節**：12月25日 上午 8:00
- **元旦**：1月1日 上午 0:00
- **農曆新年**：農曆正月初一 上午 0:00（系統會自動換算日期）

---

## Gmail 設定步驟

### 步驟 1：啟用 Google 兩步驟驗證

1. 前往 [Google 帳戶安全性設定](https://myaccount.google.com/security)
2. 在「登入 Google」區塊中，點選「兩步驟驗證」
3. 按照指示完成兩步驟驗證設定

### 步驟 2：建立應用程式密碼

1. 前往 [Google 應用程式密碼](https://myaccount.google.com/apppasswords)
2. 在「選取應用程式」下拉選單中，選擇「郵件」
3. 在「選取裝置」下拉選單中，選擇「其他 (自訂名稱)」
4. 輸入名稱：`財務處月報系統`
5. 點選「產生」
6. **複製產生的 16 位數密碼**（去除空格）

### 步驟 3：設定環境變數

1. 複製 `.env.example` 檔案並重新命名為 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 檔案，填入你的 Gmail 資訊：
   ```bash
   # Gmail 帳號 (寄件人)
   GMAIL_USER=your-email@gmail.com

   # Gmail 應用程式密碼 (16 位數，去除空格)
   GMAIL_APP_PASSWORD=abcdabcdabcdabcd

   # 寄件人顯示名稱
   SENDER_NAME=財務處

   # 應用程式網址
   APP_URL=http://localhost:8000
   ```

### 步驟 4：測試郵件功能

啟動系統後，可以在 Python 中測試發送郵件：

```python
from email_service import email_service

# 測試發送郵件
test_staff = {
    "name": "測試員工",
    "email": "test@example.com"
}

# 測試生日賀卡
result = email_service.send_birthday_card(test_staff)
print(f"郵件發送結果: {result}")
```

---

## 注意事項

⚠️ **安全性提醒**：
- `.env` 檔案包含敏感資訊，請勿上傳至 Git
- 已在 `.gitignore` 中排除 `.env` 檔案
- 應用程式密碼與 Gmail 登入密碼不同，僅用於應用程式存取

⚠️ **Gmail 限制**：
- Gmail 每天有發送郵件數量限制（免費帳號約 500 封/天）
- 如果發送量大，建議使用 G Suite / Google Workspace 帳號

---

## 排程時間表

| 任務 | 觸發時間 | 說明 |
|------|---------|------|
| 月報郵件 | 每月 1 日 09:00 | 寄送上個月的月報給所有同事 |
| 生日檢查 | 每天 08:00 | 檢查當天是否有壽星並寄送賀卡 |
| 聖誕賀卡 | 12/25 08:00 | 寄送聖誕節賀卡 |
| 新年賀卡 | 1/1 00:00 | 寄送新年賀卡 |
| 農曆新年檢查 | 每天 00:00 | 檢查是否為農曆正月初一 |

---

## 疑難排解

### 郵件發送失敗

**問題**：看到錯誤訊息 `Gmail 認證資訊未設定`
**解決方法**：
1. 確認 `.env` 檔案是否存在
2. 確認 `GMAIL_USER` 和 `GMAIL_APP_PASSWORD` 是否正確設定
3. 重新啟動系統

**問題**：錯誤訊息 `Username and Password not accepted`
**解決方法**：
1. 確認是否已啟用兩步驟驗證
2. 確認使用的是「應用程式密碼」而非 Gmail 登入密碼
3. 應用程式密碼請去除空格（16 個連續字元）

**問題**：郵件進入垃圾郵件匣
**解決方法**：
1. 請收件人將寄件人加入聯絡人
2. 請收件人標記為「非垃圾郵件」

---

## 技術架構

- **郵件服務**：`email_service.py` - 使用 Gmail SMTP (smtplib)
- **排程系統**：`scheduler.py` - 使用 APScheduler
- **HTML 模板**：使用 Jinja2 生成精美的郵件內容
- **農曆轉換**：使用 `lunarcalendar` 套件計算農曆新年日期

需要協助可以隨時詢問！
