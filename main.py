from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 讀取環境變數（本地開發預設使用 SQLite）
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./monthly_report.db")

# 建立資料庫引擎
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith("postgresql"):
    # PostgreSQL 連接設定（支援 SSL）
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "prefer"},  # Zeabur PostgreSQL 可能需要 SSL
        pool_pre_ping=True,  # 檢查連接是否有效
        pool_size=5,
        max_overflow=10
    )
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== 資料庫模型 ====================

class MonthlyReport(Base):
    """月報內容資料表"""
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(String(10), unique=True, nullable=False, index=True)  # 格式：2026-01
    completed = Column(Text)  # 上月達成（JSON 格式儲存列表）
    focus = Column(Text)  # 本月重點（JSON 格式儲存列表）
    tax_news = Column(Text)  # 稅務快訊（JSON 格式儲存列表，5則）
    calendar = Column(Text)  # 行事曆（JSON 格式儲存）
    quotes = Column(Text)  # 勵志金句

class Staff(Base):
    """同事名單資料表"""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200))
    birthday = Column(String(20))  # 格式：1970.1.5

# 建立 FastAPI 應用
app = FastAPI(title="財務處月報系統")

# ==================== 初始化資料庫 ====================

def init_db():
    """初始化資料庫並填入資料"""
    # 建立所有資料表
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 檢查月報資料是否已存在
        existing_report = db.query(MonthlyReport).first()

        if not existing_report:
            print("📋 資料庫為空，開始寫入初始資料...")

            # ============ 月報內容 ============
            monthly_data = MonthlyReport(
                month="2026-01",
                completed=json.dumps([
                    {"title": "年度預算審核", "content": "完成 2026 年度預算審核，並提交董事會核准"},
                    {"title": "Q4 報稅", "content": "完成第四季度營業稅及所得稅申報作業"},
                    {"title": "會計師查帳", "content": "配合外部會計師完成年度財務報表查核"}
                ], ensure_ascii=False),

                focus=json.dumps([
                    {"title": "年終獎金試算", "content": "完成全體員工年終獎金試算與核對"},
                    {"title": "新會計系統測試", "content": "進行新一代 ERP 會計模組上線前測試"}
                ], ensure_ascii=False),

                tax_news=json.dumps([
                    {"title": "CFC 新制上路", "content": "受控外國企業（CFC）制度已正式實施，跨國企業需留意申報義務"},
                    {"title": "IFRS 17 保險合約", "content": "IFRS 17 保險合約新準則已生效，金融業需注意會計處理變更"},
                    {"title": "營業稅電子發票", "content": "財政部推動 100% 電子發票，請確認公司發票系統符合規範"},
                    {"title": "最低稅負制調整", "content": "2026 年最低稅負制門檻調整，請重新評估稅務規劃"},
                    {"title": "碳費開徵預告", "content": "環境部預計 2026 年下半年開徵碳費，建議提前盤查碳排數據"}
                ], ensure_ascii=False),

                calendar=json.dumps([
                    {"date": "1/10", "event": "營業稅申報", "detail": "1 月 10 日前完成 12 月份營業稅申報"},
                    {"date": "1/25", "event": "員工薪資發放", "detail": "1 月 25 日發放 1 月份薪資"},
                    {"date": "1/31", "event": "月底結帳", "detail": "1 月 31 日完成月度財務結帳作業"}
                ], ensure_ascii=False),

                quotes="細緻的數字背後，是財務人對公司價值的守護。"
            )

            db.add(monthly_data)

            # ============ 同事名單（優先從環境變數載入）============
            # 1. 優先從環境變數 STAFF_DATA_JSON 讀取（用於 Zeabur 等雲端部署）
            # 2. 如果沒有環境變數，則從檔案讀取
            staff_list = []

            # 嘗試從環境變數載入
            staff_json_env = os.getenv("STAFF_DATA_JSON")
            if staff_json_env:
                try:
                    staff_list = json.loads(staff_json_env)
                    print(f"✅ 從環境變數載入同事資料：{len(staff_list)} 筆")
                except Exception as e:
                    print(f"❌ 解析環境變數 STAFF_DATA_JSON 失敗：{e}")

            # 如果環境變數沒有資料，從檔案讀取
            if not staff_list:
                staff_file = "staff_data.json"
                if not os.path.exists(staff_file):
                    staff_file = "staff_data.example.json"
                    print(f"⚠️  找不到 staff_data.json，使用範例資料：{staff_file}")

                try:
                    with open(staff_file, 'r', encoding='utf-8') as f:
                        staff_list = json.load(f)
                    print(f"✅ 從檔案載入同事資料：{len(staff_list)} 筆")
                except Exception as e:
                    print(f"❌ 載入同事資料失敗：{e}")
                    # 使用最小範例資料
                    staff_list = [
                        {"id": 1, "name": "範例員工", "email": "example@company.com", "birthday": "1990.1.1"}
                    ]

            for staff_data in staff_list:
                staff = Staff(
                    id=staff_data["id"],
                    name=staff_data["name"],
                    email=staff_data.get("email", ""),
                    birthday=staff_data["birthday"]
                )
                db.add(staff)

            db.commit()
            print("✅ 初始資料寫入完成！")
            print(f"   - 月報資料：1 筆（2026-01）")
            print(f"   - 同事名單：{len(staff_list)} 筆")
        else:
            print("ℹ️  資料庫已有資料，跳過初始化")

    except Exception as e:
        db.rollback()
        print(f"❌ 資料初始化失敗: {e}")
        raise
    finally:
        db.close()

# 啟動時初始化資料庫和排程器
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("🚀 財務處月報系統啟動中...")
    print("=" * 50)
    init_db()

    # 初始化並啟動排程器
    from scheduler import SchedulerService
    global scheduler_service
    scheduler_service = SchedulerService(SessionLocal)
    scheduler_service.start()
    print("✅ 郵件排程系統已啟動")

# 關閉時停止排程器
@app.on_event("shutdown")
async def shutdown_event():
    global scheduler_service
    if scheduler_service:
        scheduler_service.shutdown()
    print("👋 系統已關閉")

# 全域排程器實例
scheduler_service = None

# ==================== 輔助函數 ====================

def get_current_month_birthdays(staff_list, month=1):
    """取得本月壽星"""
    birthdays = []
    for staff in staff_list:
        if staff.birthday:
            try:
                # 解析生日格式：1970.1.5
                parts = staff.birthday.split('.')
                if len(parts) >= 2:
                    birth_month = int(parts[1])
                    birth_day = int(parts[2]) if len(parts) >= 3 else 1
                    if birth_month == month:
                        birthdays.append({
                            "name": staff.name,
                            "date": f"{birth_month}/{birth_day}",
                            "email": staff.email or "未提供"
                        })
            except:
                continue
    return birthdays

# ==================== 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """首頁 - 顯示月報"""
    db = SessionLocal()

    try:
        # 取得當前月份的月報（預設 2026-01）
        report = db.query(MonthlyReport).filter(MonthlyReport.month == "2026-01").first()

        if not report:
            return HTMLResponse("<h1>找不到月報資料</h1><p>請確認資料庫是否正確初始化</p>")

        # 解析 JSON 資料
        completed = json.loads(report.completed)
        focus = json.loads(report.focus)
        tax_news = json.loads(report.tax_news)
        calendar = json.loads(report.calendar)

        # 取得所有同事
        all_staff = db.query(Staff).all()

        # 取得 1 月壽星
        birthdays = get_current_month_birthdays(all_staff, month=1)

    finally:
        db.close()

    # 生成 HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>財務處月報系統</title>
        <style>
            :root {{
                --bg-color: #fffffe;
                --dark-color: #272343;
                --accent-color: #ffd803;
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                background-color: var(--bg-color);
                font-family: 'Arial', 'Microsoft JhengHei', sans-serif;
                line-height: 1.6;
                color: var(--dark-color);
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 0;
            }}

            .header {{
                background-color: var(--dark-color);
                padding: 48px 24px;
                text-align: center;
                border: 2px solid var(--dark-color);
            }}

            .header h1 {{
                color: var(--accent-color);
                font-size: 48px;
                font-weight: bold;
                letter-spacing: 4px;
                margin-bottom: 8px;
            }}

            .header p {{
                color: var(--accent-color);
                font-size: 18px;
                letter-spacing: 2px;
            }}

            .quote-section {{
                background-color: var(--accent-color);
                padding: 32px 24px;
                text-align: center;
                border: 2px solid var(--dark-color);
                border-top: none;
            }}

            .quote-section p {{
                color: var(--dark-color);
                font-size: 28px;
                font-weight: bold;
                font-style: italic;
                letter-spacing: 1px;
            }}

            .section {{
                background-color: var(--bg-color);
                border: 2px solid var(--dark-color);
                padding: 32px 24px;
                margin-top: -2px;
            }}

            .section-title {{
                font-size: 32px;
                font-weight: bold;
                color: var(--dark-color);
                border-bottom: 4px solid var(--dark-color);
                padding-bottom: 12px;
                margin-bottom: 24px;
                text-transform: uppercase;
            }}

            .retrospective-grid {{
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 32px;
                align-items: start;
            }}

            .work-image {{
                width: 100%;
                height: auto;
                border: 2px solid var(--dark-color);
                object-fit: cover;
                aspect-ratio: 4/3;
            }}

            .work-list {{
                list-style: none;
            }}

            .work-list li {{
                padding: 16px 0;
                border-bottom: 2px solid var(--dark-color);
            }}

            .work-list li:last-child {{
                border-bottom: none;
            }}

            .work-list li strong {{
                font-size: 20px;
                display: block;
                margin-bottom: 8px;
            }}

            .work-list li p {{
                color: var(--dark-color);
                opacity: 0.8;
            }}

            .highlight-box {{
                background-color: var(--dark-color);
                color: var(--accent-color);
                padding: 24px;
                border: 2px solid var(--dark-color);
                margin-top: 24px;
            }}

            .highlight-box h3 {{
                font-size: 24px;
                margin-bottom: 16px;
            }}

            .highlight-box ul {{
                list-style: none;
            }}

            .highlight-box li {{
                padding: 12px 0;
                border-bottom: 1px solid var(--accent-color);
            }}

            .highlight-box li:last-child {{
                border-bottom: none;
            }}

            .calendar-grid {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 24px;
                margin-top: 24px;
            }}

            .calendar-table {{
                width: 100%;
                border-collapse: collapse;
            }}

            .calendar-table th {{
                background-color: var(--dark-color);
                color: var(--accent-color);
                padding: 16px;
                text-align: left;
                border: 2px solid var(--dark-color);
                font-size: 18px;
            }}

            .calendar-table td {{
                padding: 16px;
                border: 2px solid var(--dark-color);
            }}

            .calendar-table tr:nth-child(even) {{
                background-color: rgba(255, 216, 3, 0.1);
            }}

            .date-badge {{
                background-color: var(--accent-color);
                color: var(--dark-color);
                padding: 8px 16px;
                border: 2px solid var(--dark-color);
                font-weight: bold;
                display: inline-block;
                margin-right: 12px;
            }}

            .month-calendar {{
                border: 2px solid var(--dark-color);
                padding: 16px;
                background-color: var(--bg-color);
            }}

            .month-calendar-header {{
                text-align: center;
                background-color: var(--dark-color);
                color: var(--accent-color);
                padding: 12px;
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 12px;
                border: 2px solid var(--dark-color);
            }}

            .calendar-weekdays {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 4px;
                margin-bottom: 4px;
            }}

            .calendar-weekdays div {{
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 4px;
                background-color: var(--accent-color);
                border: 1px solid var(--dark-color);
            }}

            .calendar-days {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 4px;
            }}

            .calendar-days div {{
                text-align: center;
                padding: 8px 4px;
                border: 1px solid var(--dark-color);
                font-size: 14px;
                min-height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .calendar-days .empty {{
                border: none;
            }}

            .calendar-days .event-day {{
                background-color: var(--accent-color);
                font-weight: bold;
            }}

            .calendar-days .today {{
                background-color: var(--dark-color);
                color: var(--accent-color);
                font-weight: bold;
            }}

            .birthday-section {{
                background-color: var(--bg-color);
                border: 2px solid var(--dark-color);
                padding: 32px 24px;
                margin-top: -2px;
            }}

            .birthday-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 24px;
                margin-top: 24px;
            }}

            .birthday-card {{
                background-color: var(--accent-color);
                border: 2px solid var(--dark-color);
                padding: 24px;
                text-align: center;
            }}

            .birthday-card h3 {{
                font-size: 28px;
                margin-bottom: 8px;
            }}

            .birthday-card p {{
                font-size: 16px;
                margin-bottom: 4px;
            }}

            .birthday-card .date {{
                font-weight: bold;
                font-size: 18px;
                margin-top: 8px;
            }}

            .footer {{
                text-align: center;
                padding: 32px 24px;
                color: var(--dark-color);
                opacity: 0.6;
                font-size: 14px;
            }}

            @media (max-width: 768px) {{
                .header h1 {{
                    font-size: 32px;
                }}

                .quote-section p {{
                    font-size: 20px;
                }}

                .section-title {{
                    font-size: 24px;
                }}

                .retrospective-grid {{
                    grid-template-columns: 1fr;
                }}

                .calendar-grid {{
                    grid-template-columns: 1fr;
                }}

                .birthday-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>MONTHLY REPORT</h1>
                <p>財務處 2026 年 1 月份月報</p>
            </div>

            <div class="quote-section">
                <p>{report.quotes}</p>
            </div>

            <div class="section">
                <h2 class="section-title">上月完成工作 Retrospective</h2>
                <div class="retrospective-grid">
                    <img src="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop"
                         alt="工作側拍" class="work-image">
                    <ul class="work-list">
                        {"".join([f'<li><strong>{item["title"]}</strong><p>{item["content"]}</p></li>' for item in completed])}
                    </ul>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">本月工作重點 Focus Area</h2>
                <div class="highlight-box">
                    <ul>
                        {"".join([f'<li><h3>{item["title"]}</h3><p>{item["content"]}</p></li>' for item in focus])}
                    </ul>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">本月重要行事曆 Calendar</h2>
                <div class="calendar-grid">
                    <div>
                        <table class="calendar-table">
                            <thead>
                                <tr>
                                    <th>日期</th>
                                    <th>事項</th>
                                    <th>說明</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([f'<tr><td><span class="date-badge">{item["date"]}</span></td><td><strong>{item["event"]}</strong></td><td>{item["detail"]}</td></tr>' for item in calendar])}
                            </tbody>
                        </table>
                    </div>

                    <div class="month-calendar">
                        <div class="month-calendar-header">2026 年 1 月</div>
                        <div class="calendar-weekdays">
                            <div>日</div>
                            <div>一</div>
                            <div>二</div>
                            <div>三</div>
                            <div>四</div>
                            <div>五</div>
                            <div>六</div>
                        </div>
                        <div class="calendar-days">
                            <div class="empty"></div>
                            <div class="empty"></div>
                            <div class="empty"></div>
                            <div>1</div>
                            <div>2</div>
                            <div>3</div>
                            <div>4</div>
                            <div class="today">5</div>
                            <div>6</div>
                            <div>7</div>
                            <div>8</div>
                            <div>9</div>
                            <div class="event-day">10</div>
                            <div>11</div>
                            <div>12</div>
                            <div>13</div>
                            <div>14</div>
                            <div>15</div>
                            <div>16</div>
                            <div>17</div>
                            <div>18</div>
                            <div>19</div>
                            <div>20</div>
                            <div>21</div>
                            <div>22</div>
                            <div>23</div>
                            <div>24</div>
                            <div class="event-day">25</div>
                            <div>26</div>
                            <div>27</div>
                            <div>28</div>
                            <div>29</div>
                            <div>30</div>
                            <div class="event-day">31</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="birthday-section">
                <h2 class="section-title">本月壽星祝福 Birthday Celebration</h2>
                <div class="birthday-grid">
                    {"".join([f'<div class="birthday-card"><h3>🎉 {bd["name"]}</h3><p>{bd["email"]}</p><p class="date">生日：{bd["date"]}</p></div>' for bd in birthdays]) if birthdays else '<p style="text-align: center; opacity: 0.6;">本月無壽星</p>'}
                </div>
            </div>

            <div class="footer">
                <p>© 2026 財務處自動化月報系統 | Powered by FastAPI & PostgreSQL</p>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "database": "connected"}

@app.get("/api/staff")
async def get_staff():
    """API：取得所有同事名單"""
    db = SessionLocal()
    try:
        staff = db.query(Staff).all()
        return {
            "total": len(staff),
            "data": [
                {
                    "id": s.id,
                    "name": s.name,
                    "email": s.email,
                    "birthday": s.birthday
                }
                for s in staff
            ]
        }
    finally:
        db.close()

@app.get("/api/report/{month}")
async def get_report(month: str):
    """API：取得指定月份的月報"""
    db = SessionLocal()
    try:
        report = db.query(MonthlyReport).filter(MonthlyReport.month == month).first()
        if not report:
            return {"error": "找不到該月份的月報"}

        return {
            "month": report.month,
            "completed": json.loads(report.completed),
            "focus": json.loads(report.focus),
            "tax_news": json.loads(report.tax_news),
            "calendar": json.loads(report.calendar),
            "quotes": report.quotes
        }
    finally:
        db.close()

@app.post("/api/staff/sync")
async def sync_staff():
    """API：同步更新同事資料（從環境變數或檔案）"""
    db = SessionLocal()
    try:
        # 載入同事資料（與 init_db 相同的邏輯）
        staff_list = []

        # 嘗試從環境變數載入
        staff_json_env = os.getenv("STAFF_DATA_JSON")
        if staff_json_env:
            try:
                staff_list = json.loads(staff_json_env)
                print(f"✅ 從環境變數載入同事資料：{len(staff_list)} 筆")
            except Exception as e:
                return {"error": f"解析環境變數 STAFF_DATA_JSON 失敗：{e}"}

        # 如果環境變數沒有資料，從檔案讀取
        if not staff_list:
            staff_file = "staff_data.json"
            if not os.path.exists(staff_file):
                staff_file = "staff_data.example.json"

            try:
                with open(staff_file, 'r', encoding='utf-8') as f:
                    staff_list = json.load(f)
                print(f"✅ 從檔案載入同事資料：{len(staff_list)} 筆")
            except Exception as e:
                return {"error": f"載入同事資料失敗：{e}"}

        # 刪除現有的所有同事資料
        db.query(Staff).delete()

        # 寫入新的同事資料
        for staff_data in staff_list:
            staff = Staff(
                id=staff_data["id"],
                name=staff_data["name"],
                email=staff_data.get("email", ""),
                birthday=staff_data["birthday"]
            )
            db.add(staff)

        db.commit()

        return {
            "success": True,
            "message": f"成功同步 {len(staff_list)} 筆同事資料",
            "count": len(staff_list)
        }

    except Exception as e:
        db.rollback()
        return {"error": f"同步失敗：{str(e)}"}
    finally:
        db.close()
