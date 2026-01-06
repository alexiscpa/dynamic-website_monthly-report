# Zeabur 部署指南

本文件說明如何在 Zeabur 平台上部署財務處月報系統。

## 📋 部署前準備

### 1. 確認檔案已更新
確保以下檔案已經更新到最新版本：
- `Dockerfile` - 支援動態端口
- `main.py` - 支援 PostgreSQL SSL 連接
- `requirements.txt` - 包含所有依賴項

### 2. Git 提交變更
```bash
git add .
git commit -m "fix: 修正 Zeabur 部署配置"
git push
```

## 🚀 Zeabur 部署步驟

### 步驟 1：創建新專案

1. 登入 [Zeabur](https://zeabur.com)
2. 點擊「Create New Project」
3. 選擇你的專案名稱（例如：`monthly-report`）

### 步驟 2：部署應用程式

1. 在專案中點擊「Add Service」
2. 選擇「Git」
3. 連接你的 GitHub/GitLab 帳號
4. 選擇這個專案的儲存庫
5. Zeabur 會自動偵測到 Dockerfile 並開始部署

### 步驟 3：添加 PostgreSQL 資料庫

1. 在同一個專案中，再次點擊「Add Service」
2. 選擇「Marketplace」
3. 搜尋並選擇「PostgreSQL」
4. 點擊「Deploy」

**重要：** Zeabur 會自動將 PostgreSQL 的 `DATABASE_URL` 環境變數注入到你的應用程式中！

### 步驟 4：設定環境變數

在你的應用程式服務中，點擊「Variables」標籤，添加以下環境變數：

#### 必要環境變數

```bash
# Gmail OAuth 設定（用於寄送郵件）
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
SENDER_NAME=財務處

# 應用程式網址（部署後從 Zeabur 獲取）
APP_URL=https://your-app.zeabur.app

# 同事資料（JSON 格式，重要！）
STAFF_DATA_JSON=[{"id":1,"name":"周渝民","email":"alexiscpa@gmail.com","birthday":"1970.1.5"},{"id":2,"name":"許瑋甯","email":"ahua.li@test.com","birthday":"1985.1.6"},{"id":3,"name":"王淨","email":"datong@demo.com","birthday":"1995.1.6"},{"id":4,"name":"安心亞","email":"meimei@mail.com","birthday":"1993.1.7"},{"id":5,"name":"柯佳嬿","email":"","birthday":"1980.3.5"},{"id":6,"name":"賴雅妍","email":"","birthday":"1979.4.10"},{"id":7,"name":"張惠妹","email":"","birthday":"1978.10.3"},{"id":8,"name":"林辰唏","email":"","birthday":"1985.11.20"},{"id":9,"name":"李千娜","email":"","birthday":"1994.6.1"},{"id":10,"name":"林予晞","email":"","birthday":"1987.3.5"}]
```

**重要說明：**
- `STAFF_DATA_JSON` 必須是**壓縮成單行的 JSON 格式**（不能有換行）
- 這是因為 `staff_data.json` 包含個人資料，不會被推送到 GitHub
- 系統會優先從環境變數載入同事資料，如果沒有則使用範例資料

#### 取得 Gmail 應用程式密碼

1. 前往 [Google 帳戶安全性設定](https://myaccount.google.com/security)
2. 啟用「兩步驟驗證」
3. 前往 [應用程式密碼](https://myaccount.google.com/apppasswords)
4. 生成新的應用程式密碼（選擇「郵件」和「其他裝置」）
5. 將 16 位數密碼複製並貼到 `GMAIL_APP_PASSWORD` 環境變數中

### 步驟 5：獲取應用程式網址

1. 部署完成後，點擊「Networking」標籤
2. 點擊「Generate Domain」生成公開網址
3. 複製生成的網址（例如：`https://your-app.zeabur.app`）
4. 回到「Variables」標籤，更新 `APP_URL` 環境變數

### 步驟 6：驗證部署

1. 開啟應用程式網址，應該會看到月報頁面
2. 檢查 `/health` 端點：`https://your-app.zeabur.app/health`
   - 應該返回：`{"status": "healthy", "database": "connected"}`
3. 檢查應用程式日誌（Logs 標籤）確認沒有錯誤

### 步驟 7：同步同事資料（重要！）

**如果首頁顯示的壽星名字不正確（例如：張三、李四、王五），請執行以下步驟：**

#### 方法 1：使用 API 同步（推薦）

在瀏覽器或使用 curl 命令呼叫同步 API：

```bash
curl -X POST https://your-app.zeabur.app/api/staff/sync
```

**或者直接在瀏覽器中訪問（建議使用 Postman 等工具）：**
- 網址：`https://your-app.zeabur.app/api/staff/sync`
- 方法：POST

成功後會返回：
```json
{
  "success": true,
  "message": "成功同步 10 筆同事資料",
  "count": 10
}
```

#### 方法 2：重新部署

如果已經設定好 `STAFF_DATA_JSON` 環境變數但資料庫已有舊資料：

1. 在 Zeabur 專案中，刪除 PostgreSQL 服務
2. 重新添加 PostgreSQL 服務
3. 應用程式會自動重新啟動並載入正確的同事資料

#### 驗證同事資料

訪問 API 端點查看同事名單：
```
https://your-app.zeabur.app/api/staff
```

應該會看到正確的同事資料（周渝民、許瑋甯等）。

## 🔍 常見問題排除

### 問題 1：應用程式無法啟動

**症狀：** 部署失敗或服務一直重啟

**解決方法：**
1. 檢查「Logs」標籤查看錯誤訊息
2. 確認 `DATABASE_URL` 環境變數已自動設定（Zeabur 會自動處理）
3. 確認所有必要的環境變數都已設定

### 問題 2：資料庫連接失敗

**症狀：** 日誌顯示資料庫連接錯誤

**解決方法：**
1. 確認 PostgreSQL 服務已經成功部署
2. 檢查 PostgreSQL 和應用程式是否在同一個專案中
3. Zeabur 會自動處理內部網路連接，不需要手動設定

### 問題 3：網頁無法開啟

**症狀：** 訪問網址時顯示錯誤

**解決方法：**
1. 確認應用程式已經成功部署（狀態為 Running）
2. 檢查是否已生成 Domain
3. 等待 1-2 分鐘讓 DNS 生效
4. 清除瀏覽器快取後重試

### 問題 4：郵件無法發送

**症狀：** 日誌顯示郵件發送失敗

**解決方法：**
1. 確認 `GMAIL_USER` 和 `GMAIL_APP_PASSWORD` 已正確設定
2. 確認使用的是「應用程式密碼」而非 Gmail 登入密碼
3. 確認 Gmail 帳號已啟用「兩步驟驗證」
4. 檢查 `staff_data.json` 中的電子郵件地址是否正確

### 問題 5：OAuth 瀏覽器錯誤

**症狀：** 日誌顯示 `could not locate runnable browser`

**說明：** 這是正常的警告訊息，不影響功能。
- OAuth 認證已改用環境變數方式（`.env` 檔案）
- 郵件功能使用 Gmail App Password，不需要瀏覽器認證
- 可以忽略此警告

### 問題 6：壽星名字顯示錯誤（張三、李四、王五）

**症狀：** 首頁的壽星區塊顯示範例資料，而不是真實同事名字

**原因：**
- `staff_data.json`（真實同事資料）因安全考量不會被推送到 GitHub
- 部署時使用了 `staff_data.example.json`（範例資料）
- 資料庫已有舊資料，所以沒有重新載入

**解決方法：**

1. **在 Zeabur 設定環境變數**（最重要）
   - 進入應用程式的 Variables 標籤
   - 添加 `STAFF_DATA_JSON` 環境變數（參考步驟 4）
   - 環境變數必須是單行 JSON 格式

2. **呼叫同步 API**
   ```bash
   curl -X POST https://your-app.zeabur.app/api/staff/sync
   ```

3. **驗證結果**
   - 訪問：`https://your-app.zeabur.app/api/staff`
   - 確認返回的是正確的同事資料
   - 重新整理首頁，檢查壽星區塊

## 📊 資料庫管理

### 查看資料庫內容

1. 在 Zeabur 專案中，點擊 PostgreSQL 服務
2. 點擊「Database」標籤
3. 可以看到連接資訊和使用 SQL 查詢工具

### 備份資料庫

1. 點擊 PostgreSQL 服務
2. 點擊「Settings」標籤
3. 可以設定自動備份

## 🔄 更新部署

當你修改程式碼並推送到 Git 儲存庫後：

1. Zeabur 會自動偵測到變更
2. 自動重新建置並部署新版本
3. 在「Deployments」標籤可以看到部署歷史

## 📝 監控與日誌

### 查看應用程式日誌

1. 點擊應用程式服務
2. 點擊「Logs」標籤
3. 可以看到即時日誌輸出

### 監控資源使用

1. 點擊專案
2. 查看「Usage」標籤
3. 可以看到 CPU、記憶體、流量等使用情況

## 🎯 下一步

部署完成後，你可以：

1. 設定自訂網域（在 Networking 標籤中）
2. 配置 Google Sheets 整合（參考 `GOOGLE_SHEETS_SETUP.md`）
3. 調整排程任務時間（在 `scheduler.py` 中修改）
4. 自訂月報內容（透過 API 或資料庫）

## 🆘 需要協助？

- [Zeabur 官方文件](https://zeabur.com/docs)
- [Zeabur Discord 社群](https://discord.gg/zeabur)
- 檢查專案的 `README.md` 了解更多功能說明
