"""
Google Sheets 匯入 PostgreSQL 腳本
將 Google Sheets 中的月報內容和同事名單匯入資料庫
"""

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, Column, Integer, String, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ==================== 配置區 ====================

# Google Sheets 設定
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# 請將你的 Google Sheets ID 填入這裡
MONTHLY_CONTENT_SHEET_ID = "YOUR_MONTHLY_CONTENT_SHEET_ID"  # 月報內容 Sheet ID
STAFF_LIST_SHEET_ID = "YOUR_STAFF_LIST_SHEET_ID"  # 同事名單 Sheet ID

# Google Service Account JSON 憑證檔案路徑
CREDENTIALS_FILE = "google_credentials.json"

# 資料庫連接（從環境變數讀取，或使用預設值）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/monthly_report")

# ==================== 資料庫模型 ====================

Base = declarative_base()

class MonthlyContent(Base):
    """月報內容資料表"""
    __tablename__ = "monthly_content"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # 類別
    title = Column(String(200))
    content = Column(Text)
    date_info = Column(String(50))
    order_num = Column(Integer, default=0)

class Staff(Base):
    """同事名單資料表"""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    position = Column(String(100))
    department = Column(String(100))
    birthday = Column(String(20))
    email = Column(String(200))

# ==================== 主要功能 ====================

def connect_to_google_sheets():
    """連接到 Google Sheets"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        print("✅ 成功連接到 Google Sheets")
        return client
    except Exception as e:
        print(f"❌ 連接 Google Sheets 失敗: {e}")
        print("\n請確保：")
        print("1. google_credentials.json 檔案存在於當前目錄")
        print("2. Google Sheets 已與 Service Account 共享（編輯權限）")
        raise

def connect_to_database():
    """連接到 PostgreSQL 資料庫"""
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print("✅ 成功連接到資料庫")
        return engine, SessionLocal
    except Exception as e:
        print(f"❌ 連接資料庫失敗: {e}")
        raise

def import_monthly_content(client, session):
    """匯入月報內容"""
    try:
        # 開啟 Google Sheet
        sheet = client.open_by_key(MONTHLY_CONTENT_SHEET_ID)
        worksheet = sheet.get_worksheet(0)  # 取得第一個工作表

        # 取得所有資料（包含標題列）
        all_records = worksheet.get_all_records()

        # 清空現有資料（可選）
        session.query(MonthlyContent).delete()

        # 匯入資料
        count = 0
        for record in all_records:
            content = MonthlyContent(
                category=record.get('category', ''),
                title=record.get('title', ''),
                content=record.get('content', ''),
                date_info=record.get('date_info', ''),
                order_num=record.get('order_num', 0)
            )
            session.add(content)
            count += 1

        session.commit()
        print(f"✅ 成功匯入 {count} 筆月報內容")

    except Exception as e:
        session.rollback()
        print(f"❌ 匯入月報內容失敗: {e}")
        raise

def import_staff_list(client, session):
    """匯入同事名單"""
    try:
        # 開啟 Google Sheet
        sheet = client.open_by_key(STAFF_LIST_SHEET_ID)
        worksheet = sheet.get_worksheet(0)

        # 取得所有資料
        all_records = worksheet.get_all_records()

        # 清空現有資料（可選）
        session.query(Staff).delete()

        # 匯入資料
        count = 0
        for record in all_records:
            staff = Staff(
                name=record.get('name', ''),
                position=record.get('position', ''),
                department=record.get('department', ''),
                birthday=record.get('birthday', ''),
                email=record.get('email', '')
            )
            session.add(staff)
            count += 1

        session.commit()
        print(f"✅ 成功匯入 {count} 筆同事資料")

    except Exception as e:
        session.rollback()
        print(f"❌ 匯入同事名單失敗: {e}")
        raise

def main():
    """主程式"""
    print("=" * 50)
    print("Google Sheets → PostgreSQL 資料匯入工具")
    print("=" * 50)
    print()

    try:
        # 1. 連接到 Google Sheets
        client = connect_to_google_sheets()

        # 2. 連接到資料庫
        engine, SessionLocal = connect_to_database()
        db = SessionLocal()

        # 3. 匯入月報內容
        print("\n📋 開始匯入月報內容...")
        import_monthly_content(client, db)

        # 4. 匯入同事名單
        print("\n👥 開始匯入同事名單...")
        import_staff_list(client, db)

        # 5. 完成
        db.close()
        print("\n" + "=" * 50)
        print("🎉 所有資料匯入完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
