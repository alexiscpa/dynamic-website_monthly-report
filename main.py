from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai

# 載入環境變數
load_dotenv()

# JWT 設定
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# 預設管理員帳號
ADMIN_DEFAULT_USERNAME = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")

# Gemini AI 設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API 已設定")
else:
    print("⚠️  未設定 GEMINI_API_KEY,自動生成功能將無法使用")

# 密碼雜湊設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 安全性相關
security = HTTPBearer(auto_error=False)

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

class AdminUser(Base):
    """管理員帳號資料表"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==================== Pydantic 資料模型 ====================

class LoginRequest(BaseModel):
    username: str
    password: str

class ReportItem(BaseModel):
    title: str
    content: str

class CalendarItem(BaseModel):
    date: str
    event: str
    detail: str

class ReportUpdate(BaseModel):
    quotes: Optional[str] = None
    completed: Optional[List[ReportItem]] = None
    focus: Optional[List[ReportItem]] = None
    tax_news: Optional[List[ReportItem]] = None
    calendar: Optional[List[CalendarItem]] = None

class ReportCreate(BaseModel):
    month: str
    quotes: str = ""
    completed: List[ReportItem] = []
    focus: List[ReportItem] = []
    tax_news: List[ReportItem] = []
    calendar: List[CalendarItem] = []

# ==================== 認證相關函數 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    # 使用與 get_password_hash 相同的截斷邏輯
    if not plain_password:
        return False
    
    password_bytes = plain_password.encode('utf-8')
    
    if len(password_bytes) > 72:
        truncate_at = 72
        while truncate_at > 0:
            try:
                truncated_password = password_bytes[:truncate_at].decode('utf-8')
                break
            except UnicodeDecodeError:
                truncate_at -= 1
        if truncate_at == 0:
            truncated_password = plain_password[:72]
    else:
        truncated_password = plain_password
    
    return pwd_context.verify(truncated_password, hashed_password)


def get_password_hash(password: str) -> str:
    """產生密碼雜湊"""
    # bcrypt 限制密碼最長 72 bytes
    # 安全地截斷密碼，避免在 UTF-8 字元中間切斷
    if not password:
        password = "default_password"
    
    # 將密碼編碼為 UTF-8
    password_bytes = password.encode('utf-8')
    
    # 如果超過 72 bytes，需要截斷
    if len(password_bytes) > 72:
        # 從 72 bytes 往前找，確保不會在 UTF-8 字元中間切斷
        truncate_at = 72
        while truncate_at > 0:
            try:
                truncated_password = password_bytes[:truncate_at].decode('utf-8')
                break
            except UnicodeDecodeError:
                truncate_at -= 1
        if truncate_at == 0:
            # 如果都失敗，使用前 72 個字元（字元而非 bytes）
            truncated_password = password[:72]
    else:
        truncated_password = password
    
    return pwd_context.hash(truncated_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """產生 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """解碼 JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """取得當前登入用戶（認證依賴）"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認證失敗或 Token 已過期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶不存在或已停用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"id": user.id, "username": user.username}
    finally:
        db.close()

# 建立 FastAPI 應用
app = FastAPI(title="財務處月報系統")

# 添加 CORS 中間件（允許測試工具訪問 API）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源（生產環境建議限制特定網域）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        # 檢查並建立預設管理員帳號
        existing_admin = db.query(AdminUser).filter(AdminUser.username == ADMIN_DEFAULT_USERNAME).first()
        if not existing_admin:
            admin_user = AdminUser(
                username=ADMIN_DEFAULT_USERNAME,
                password_hash=get_password_hash(ADMIN_DEFAULT_PASSWORD),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ 預設管理員帳號已建立：{ADMIN_DEFAULT_USERNAME}")
        else:
            print(f"ℹ️  管理員帳號已存在：{ADMIN_DEFAULT_USERNAME}")

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

def generate_calendar_html(year: int, month: int, event_dates: list = None):
    """生成月曆 HTML
    
    Args:
        year: 年份
        month: 月份 (1-12)
        event_dates: 有事件的日期列表，例如 [10, 25, 31]
    
    Returns:
        月曆的 HTML 字串
    """
    import calendar
    from datetime import datetime
    
    if event_dates is None:
        event_dates = []
    
    # 取得當月的日曆
    cal = calendar.monthcalendar(year, month)
    
    # 取得今天的日期
    today = datetime.now()
    is_current_month = (today.year == year and today.month == month)
    today_day = today.day if is_current_month else None
    
    # 生成月曆 HTML
    html = f'<div class="month-calendar">\n'
    html += f'    <div class="month-calendar-header">{year} 年 {month} 月</div>\n'
    html += '    <div class="calendar-weekdays">\n'
    html += '        <div>日</div>\n'
    html += '        <div>一</div>\n'
    html += '        <div>二</div>\n'
    html += '        <div>三</div>\n'
    html += '        <div>四</div>\n'
    html += '        <div>五</div>\n'
    html += '        <div>六</div>\n'
    html += '    </div>\n'
    html += '    <div class="calendar-days">\n'
    
    # 生成日期格子
    for week in cal:
        for day in week:
            if day == 0:
                # 空白格子
                html += '        <div class="empty"></div>\n'
            else:
                # 判斷是否為今天、事件日
                classes = []
                if day == today_day:
                    classes.append('today')
                if day in event_dates:
                    classes.append('event-day')
                
                class_str = f' class="{" ".join(classes)}"' if classes else ''
                html += f'        <div{class_str}>{day}</div>\n'
    
    html += '    </div>\n'
    html += '</div>\n'
    
    return html

# ==================== 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def read_root(month: Optional[str] = None):
    """首頁 - 顯示月報"""
    db = SessionLocal()

    try:
        # 如果沒有指定月份，取得最新的月報
        if not month:
            latest_report = db.query(MonthlyReport).order_by(MonthlyReport.month.desc()).first()
            if latest_report:
                month = latest_report.month
            else:
                return HTMLResponse("<h1>找不到月報資料</h1><p>請確認資料庫是否正確初始化</p>")
        
        # 取得指定月份的月報
        report = db.query(MonthlyReport).filter(MonthlyReport.month == month).first()

        if not report:
            return HTMLResponse(f"<h1>找不到月報資料</h1><p>找不到 {month} 的月報</p>")

        # 解析 JSON 資料
        completed = json.loads(report.completed)
        focus = json.loads(report.focus)
        tax_news = json.loads(report.tax_news)
        calendar = json.loads(report.calendar)

        # 取得所有同事
        all_staff = db.query(Staff).all()

        # 取得當月壽星
        try:
            month_num = int(month.split('-')[1])
        except:
            month_num = 1
        birthdays = get_current_month_birthdays(all_staff, month=month_num)
        
        # 取得所有可用月份（用於下拉選單）
        all_months = db.query(MonthlyReport.month).order_by(MonthlyReport.month.desc()).all()
        available_months = [m.month for m in all_months]
        
        # 解析年份和月份，生成動態月曆
        try:
            year = int(month.split('-')[0])
            month_num = int(month.split('-')[1])
        except:
            year = 2026
            month_num = 1
        
        # 從行事曆資料中提取有事件的日期
        # 從行事曆資料中提取有事件的日期
        event_dates = []
        for cal_item in calendar:
            try:
                date_str = cal_item.get('date', '')
                # 處理日期範圍，例如 "2/14-2/22" 或 "2/14~2/22"
                if '-' in date_str or '~' in date_str:
                    separator = '-' if '-' in date_str else '~'
                    start_str, end_str = date_str.split(separator)
                    
                    # 解析開始日期
                    if '/' in start_str:
                        start_day = int(start_str.split('/')[1])
                    else:
                        start_day = int(start_str)
                        
                    # 解析結束日期
                    if '/' in end_str:
                        end_day = int(end_str.split('/')[1])
                    else:
                        end_day = int(end_str)
                    
                    # 將範圍內的所有日期加入列表
                    event_dates.extend(range(start_day, end_day + 1))
                
                # 處理單一日期，例如 "1/10"
                elif '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) >= 2:
                        day = int(parts[1])
                        event_dates.append(day)
            except:
                continue
        
        # 生成月曆 HTML
        calendar_html = generate_calendar_html(year, month_num, event_dates)

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

            .month-selector {{
                margin-top: 24px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
            }}

            .month-selector label {{
                color: var(--accent-color);
                font-size: 16px;
                font-weight: bold;
            }}

            .month-selector select {{
                background-color: var(--accent-color);
                color: var(--dark-color);
                border: 2px solid var(--dark-color);
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                font-family: 'Arial', 'Microsoft JhengHei', sans-serif;
                transition: all 0.3s ease;
            }}

            .month-selector select:hover {{
                background-color: var(--dark-color);
                color: var(--accent-color);
                transform: translateY(-2px);
            }}

            .month-selector select:focus {{
                outline: 3px solid var(--accent-color);
                outline-offset: 2px;
            }}

            .loading {{
                opacity: 0.5;
                pointer-events: none;
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

            .month-selector {{
                margin-top: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}

            .month-selector label {{
                color: var(--accent-color); /* Yellow text for label */
                font-weight: bold;
            }}

            #month-select {{
                padding: 8px 16px;
                background-color: var(--accent-color); /* Yellow background */
                color: var(--dark-color); /* Dark text */
                border: none;
                font-weight: bold;
                font-size: 16px;
                cursor: pointer;
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
                <p id="report-subtitle">財務處 {month.split('-')[0]} 年 {int(month.split('-')[1])} 月份月報</p>
                <div class="month-selector">
                    <label for="month-select">選擇月份：</label>
                    <select id="month-select">
                        {''.join([f'<option value="{m}" {"selected" if m == month else ""}>{m.split("-")[0]} 年 {int(m.split("-")[1])} 月</option>' for m in available_months])}
                    </select>
                </div>
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
                <h2 class="section-title">稅務快訊 Tax News</h2>
                <div class="highlight-box">
                    <ul>
                        {"".join([f'<li><h3>{item["title"]}</h3><p>{item["content"]}</p></li>' for item in tax_news])}
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

                    {calendar_html}
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

        <script>
            // 月份選擇器事件監聽
            document.getElementById('month-select').addEventListener('change', function() {{
                const selectedMonth = this.value;
                // 使用 URL 參數重新載入頁面
                window.location.href = '/?month=' + selectedMonth;
            }});
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """管理頁面"""
    admin_html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>月報管理系統</title>
        <style>
            :root {
                --bg-color: #fffffe;
                --dark-color: #272343;
                --accent-color: #ffd803;
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                background-color: var(--bg-color);
                font-family: 'Arial', 'Microsoft JhengHei', sans-serif;
                line-height: 1.6;
                color: var(--dark-color);
                min-height: 100vh;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 24px;
            }

            .header {
                background-color: var(--dark-color);
                padding: 24px;
                text-align: center;
                border: 2px solid var(--dark-color);
                margin-bottom: 24px;
            }

            .header h1 {
                color: var(--accent-color);
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 2px;
            }

            .header p {
                color: var(--accent-color);
                font-size: 14px;
                margin-top: 8px;
            }

            /* Login Form */
            .login-section {
                max-width: 400px;
                margin: 100px auto;
                padding: 32px;
                border: 2px solid var(--dark-color);
                background-color: var(--bg-color);
            }

            .login-section h2 {
                text-align: center;
                margin-bottom: 24px;
                color: var(--dark-color);
            }

            .form-group {
                margin-bottom: 16px;
            }

            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }

            .form-group input {
                width: 100%;
                padding: 12px;
                border: 2px solid var(--dark-color);
                font-size: 16px;
            }

            .form-group input:focus {
                outline: none;
                border-color: var(--accent-color);
            }

            .btn {
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid var(--dark-color);
                cursor: pointer;
                transition: all 0.2s;
            }

            .btn-primary {
                background-color: var(--accent-color);
                color: var(--dark-color);
            }

            .btn-primary:hover {
                background-color: var(--dark-color);
                color: var(--accent-color);
            }

            .btn-secondary {
                background-color: var(--bg-color);
                color: var(--dark-color);
            }

            .btn-secondary:hover {
                background-color: var(--dark-color);
                color: var(--accent-color);
            }

            .btn-danger {
                background-color: #ff6b6b;
                color: white;
                border-color: #ff6b6b;
            }

            .btn-danger:hover {
                background-color: #ee5a5a;
            }

            .btn-block {
                width: 100%;
            }

            .error-message {
                color: #ff6b6b;
                text-align: center;
                margin-top: 16px;
            }

            .back-link {
                text-align: center;
                margin-top: 24px;
            }

            .back-link a {
                color: var(--dark-color);
            }

            /* Dashboard */
            .dashboard {
                display: none;
            }

            .dashboard.active {
                display: block;
            }

            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }

            .dashboard-header h2 {
                font-size: 24px;
            }

            .user-info {
                display: flex;
                align-items: center;
                gap: 16px;
            }

            .card {
                background-color: var(--bg-color);
                border: 2px solid var(--dark-color);
                padding: 24px;
                margin-bottom: 24px;
            }

            .card-header {
                background-color: var(--dark-color);
                color: var(--accent-color);
                padding: 16px;
                margin: -24px -24px 24px -24px;
                font-weight: bold;
                font-size: 18px;
            }

            .report-list {
                list-style: none;
            }

            .report-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 0;
                border-bottom: 1px solid var(--dark-color);
            }

            .report-item:last-child {
                border-bottom: none;
            }

            .report-info h3 {
                font-size: 18px;
                margin-bottom: 4px;
            }

            .report-info p {
                font-size: 14px;
                opacity: 0.7;
            }

            .report-actions {
                display: flex;
                gap: 8px;
            }

            .btn-small {
                padding: 8px 16px;
                font-size: 14px;
            }

            /* Editor */
            .editor {
                display: none;
            }

            .editor.active {
                display: block;
            }

            .editor-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }

            .section-card {
                margin-bottom: 24px;
            }

            .section-title {
                background-color: var(--dark-color);
                color: var(--accent-color);
                padding: 12px 16px;
                font-weight: bold;
            }

            .section-content {
                border: 2px solid var(--dark-color);
                border-top: none;
                padding: 16px;
            }

            .item-row {
                display: grid;
                grid-template-columns: 1fr 2fr auto;
                gap: 12px;
                margin-bottom: 12px;
                align-items: start;
            }

            .item-row input, .item-row textarea {
                padding: 10px;
                border: 2px solid var(--dark-color);
                font-size: 14px;
                font-family: inherit;
            }

            .item-row textarea {
                min-height: 60px;
                resize: vertical;
            }

            .item-row input:focus, .item-row textarea:focus {
                outline: none;
                border-color: var(--accent-color);
            }

            .calendar-row {
                display: grid;
                grid-template-columns: 100px 1fr 2fr auto;
                gap: 12px;
                margin-bottom: 12px;
                align-items: start;
            }

            .quotes-input {
                width: 100%;
                padding: 12px;
                border: 2px solid var(--dark-color);
                font-size: 16px;
                min-height: 80px;
                resize: vertical;
                font-family: inherit;
            }

            .quotes-input:focus {
                outline: none;
                border-color: var(--accent-color);
            }

            .add-item-btn {
                margin-top: 12px;
            }

            .btn-icon {
                width: 36px;
                height: 36px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
            }

            .editor-actions {
                display: flex;
                gap: 12px;
                justify-content: flex-end;
                margin-top: 24px;
            }

            .loading {
                text-align: center;
                padding: 24px;
                color: var(--dark-color);
                opacity: 0.7;
            }

            .success-message {
                background-color: #d4edda;
                border: 2px solid #28a745;
                color: #155724;
                padding: 12px;
                margin-bottom: 16px;
                text-align: center;
            }

            /* New Report Form */
            .new-report-form {
                display: none;
            }

            .new-report-form.active {
                display: block;
            }

            .month-input-group {
                display: flex;
                gap: 12px;
                align-items: center;
            }

            .month-input-group select {
                padding: 12px;
                border: 2px solid var(--dark-color);
                font-size: 16px;
                background: var(--bg-color);
            }

            .quick-actions {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
            }

            @media (max-width: 768px) {
                .item-row {
                    grid-template-columns: 1fr;
                }

                .calendar-row {
                    grid-template-columns: 1fr;
                }

                .dashboard-header {
                    flex-direction: column;
                    gap: 16px;
                }

                .user-info {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>月報管理系統</h1>
                <p id="headerSubtitle">財務處月報編輯系統</p>
            </div>

            <!-- Login Section -->
            <div id="loginSection" class="login-section">
                <h2>管理員登入</h2>
                <form id="loginForm" onsubmit="event.preventDefault(); handleLogin();">
                    <div class="form-group">
                        <label for="username">帳號</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">密碼</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">登入</button>
                </form>
                <p id="loginError" class="error-message"></p>
                <div class="back-link">
                    <a href="/">← 返回首頁</a>
                </div>
            </div>

            <!-- Dashboard -->
            <div id="dashboard" class="dashboard">
                <div class="dashboard-header">
                    <h2>儀表板</h2>
                    <div class="user-info">
                        <span>歡迎，<strong id="currentUser"></strong></span>
                        <button onclick="logout()" class="btn btn-secondary btn-small">登出</button>
                    </div>
                </div>

                <div id="successMessage" class="success-message" style="display: none;"></div>

                <div class="card">
                    <div class="card-header">快速操作</div>
                    <div class="quick-actions">
                        <button onclick="showNewReportForm()" class="btn btn-primary">新增月報</button>
                        <button onclick="syncStaff()" class="btn btn-secondary">同步同仁資料</button>
                        <a href="/" class="btn btn-secondary">查看首頁</a>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">月報列表</div>
                    <ul id="reportList" class="report-list">
                        <li class="loading">載入中...</li>
                    </ul>
                </div>
            </div>

            <!-- New Report Form -->
            <div id="newReportForm" class="new-report-form">
                <div class="editor-header">
                    <h2>新增月報</h2>
                    <button onclick="showDashboard()" class="btn btn-secondary">返回</button>
                </div>
                <div class="card">
                    <div class="card-header">選擇月份</div>
                    <div class="section-content">
                        <div class="month-input-group">
                            <select id="newYear">
                                <option value="2025">2025</option>
                                <option value="2026" selected>2026</option>
                                <option value="2027">2027</option>
                            </select>
                            <span>年</span>
                            <select id="newMonth">
                                <option value="01">1 月</option>
                                <option value="02">2 月</option>
                                <option value="03">3 月</option>
                                <option value="04">4 月</option>
                                <option value="05">5 月</option>
                                <option value="06">6 月</option>
                                <option value="07">7 月</option>
                                <option value="08">8 月</option>
                                <option value="09">9 月</option>
                                <option value="10">10 月</option>
                                <option value="11">11 月</option>
                                <option value="12">12 月</option>
                            </select>
                            <button onclick="createNewReport()" class="btn btn-primary">建立月報</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Editor -->
            <div id="editor" class="editor">
                <div class="editor-header">
                    <h2>編輯月報：<span id="editingMonth"></span></h2>
                    <button onclick="showDashboard()" class="btn btn-secondary">返回</button>
                </div>

                <div class="section-card">
                    <div class="section-title">激勵金句 <button onclick="generateQuote()" class="btn btn-secondary btn-small" style="float: right; margin-top: -4px;">🤖 自動生成</button></div>
                    <div class="section-content">
                        <textarea id="quotesInput" class="quotes-input" placeholder="輸入本月激勵金句..."></textarea>
                    </div>
                </div>

                <div class="section-card">
                    <div class="section-title">上月完成工作</div>
                    <div class="section-content" id="completedSection">
                        <!-- Items will be added here -->
                    </div>
                    <button onclick="addItem('completed')" class="btn btn-secondary btn-small add-item-btn">+ 新增項目</button>
                </div>

                <div class="section-card">
                    <div class="section-title">本月工作重點</div>
                    <div class="section-content" id="focusSection">
                        <!-- Items will be added here -->
                    </div>
                    <button onclick="addItem('focus')" class="btn btn-secondary btn-small add-item-btn">+ 新增項目</button>
                </div>

                <div class="section-card">
                    <div class="section-title">稅務快訊 <button onclick="generateTaxNews()" class="btn btn-secondary btn-small" style="float: right; margin-top: -4px;">🤖 自動生成 5 則</button></div>
                    <div class="section-content" id="taxNewsSection">
                        <!-- Items will be added here -->
                    </div>
                    <button onclick="addItem('taxNews')" class="btn btn-secondary btn-small add-item-btn">+ 新增項目</button>
                </div>

                <div class="section-card">
                    <div class="section-title">本月行事曆</div>
                    <div class="section-content" id="calendarSection">
                        <!-- Items will be added here -->
                    </div>
                    <button onclick="addCalendarItem()" class="btn btn-secondary btn-small add-item-btn">+ 新增項目</button>
                </div>

                <div class="editor-actions">
                    <button onclick="showDashboard()" class="btn btn-secondary">取消</button>
                    <button onclick="saveReport()" class="btn btn-primary">儲存變更</button>
                </div>
            </div>
        </div>

        <script>
            // State
            let token = localStorage.getItem('adminToken');
            let currentUser = localStorage.getItem('adminUser');
            let editingMonth = null;
            let reportData = {};

            // Check login on load
            document.addEventListener('DOMContentLoaded', () => {
                if (token) {
                    verifyToken();
                }
            });

            // Login
            // Login
            async function handleLogin() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;

                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        token = data.access_token;
                        currentUser = data.username;
                        localStorage.setItem('adminToken', token);
                        localStorage.setItem('adminUser', currentUser);
                        showDashboard();
                    } else {
                        document.getElementById('loginError').textContent = data.detail || '登入失敗';
                    }
                } catch (error) {
                    document.getElementById('loginError').textContent = '連線失敗，請稍後再試';
                }
            }

            // Verify token
            async function verifyToken() {
                try {
                    const response = await fetch('/api/auth/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (response.ok) {
                        showDashboard();
                    } else {
                        logout();
                    }
                } catch {
                    logout();
                }
            }

            // Logout
            function logout() {
                token = null;
                currentUser = null;
                localStorage.removeItem('adminToken');
                localStorage.removeItem('adminUser');
                document.getElementById('loginSection').style.display = 'block';
                document.getElementById('dashboard').classList.remove('active');
                document.getElementById('editor').classList.remove('active');
                document.getElementById('newReportForm').classList.remove('active');
            }

            // Show dashboard
            function showDashboard() {
                document.getElementById('loginSection').style.display = 'none';
                document.getElementById('dashboard').classList.add('active');
                document.getElementById('editor').classList.remove('active');
                document.getElementById('newReportForm').classList.remove('active');
                document.getElementById('currentUser').textContent = currentUser;
                loadReports();
            }

            // Show new report form
            function showNewReportForm() {
                document.getElementById('dashboard').classList.remove('active');
                document.getElementById('newReportForm').classList.add('active');
            }

            // Load reports
            async function loadReports() {
                try {
                    const response = await fetch('/api/reports');
                    const data = await response.json();

                    const list = document.getElementById('reportList');
                    if (data.reports && data.reports.length > 0) {
                        list.innerHTML = data.reports.map(r => `
                            <li class="report-item">
                                <div class="report-info">
                                    <h3>${formatMonth(r.month)}</h3>
                                    <p>${r.quotes || '無金句'}</p>
                                </div>
                                <div class="report-actions">
                                    <button onclick="editReport('${r.month}')" class="btn btn-primary btn-small">編輯</button>
                                </div>
                            </li>
                        `).join('');
                    } else {
                        list.innerHTML = '<li class="loading">尚無月報資料</li>';
                    }
                } catch (error) {
                    document.getElementById('reportList').innerHTML = '<li class="loading">載入失敗</li>';
                }
            }

            // Format month
            function formatMonth(month) {
                const [year, m] = month.split('-');
                return `${year} 年 ${parseInt(m)} 月`;
            }

            // Create new report
            async function createNewReport() {
                const year = document.getElementById('newYear').value;
                const month = document.getElementById('newMonth').value;
                const monthStr = `${year}-${month}`;

                try {
                    const response = await fetch('/api/report', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            month: monthStr,
                            quotes: '',
                            completed: [],
                            focus: [],
                            tax_news: [],
                            calendar: []
                        })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        showSuccessMessage(`成功建立 ${formatMonth(monthStr)} 月報`);
                        showDashboard();
                    } else {
                        alert(data.detail || '建立失敗');
                    }
                } catch (error) {
                    alert('連線失敗');
                }
            }

            // Edit report
            async function editReport(month) {
                editingMonth = month;
                document.getElementById('editingMonth').textContent = formatMonth(month);

                try {
                    const response = await fetch(`/api/report/${month}`);
                    const data = await response.json();

                    if (data.error) {
                        alert(data.error);
                        return;
                    }

                    reportData = data;

                    // Fill form
                    document.getElementById('quotesInput').value = data.quotes || '';

                    renderItems('completed', data.completed || []);
                    renderItems('focus', data.focus || []);
                    renderItems('taxNews', data.tax_news || []);
                    renderCalendarItems(data.calendar || []);

                    document.getElementById('dashboard').classList.remove('active');
                    document.getElementById('editor').classList.add('active');
                } catch (error) {
                    alert('載入失敗');
                }
            }

            // Render items
            function renderItems(section, items) {
                const container = document.getElementById(`${section}Section`);
                container.innerHTML = items.map((item, index) => `
                    <div class="item-row" data-index="${index}">
                        <input type="text" value="${escapeHtml(item.title)}" placeholder="標題" onchange="updateItem('${section}', ${index}, 'title', this.value)">
                        <textarea placeholder="內容" onchange="updateItem('${section}', ${index}, 'content', this.value)">${escapeHtml(item.content)}</textarea>
                        <button onclick="removeItem('${section}', ${index})" class="btn btn-danger btn-icon">×</button>
                    </div>
                `).join('');
            }

            // Render calendar items
            function renderCalendarItems(items) {
                const container = document.getElementById('calendarSection');
                container.innerHTML = items.map((item, index) => `
                    <div class="calendar-row" data-index="${index}">
                        <input type="text" value="${escapeHtml(item.date)}" placeholder="日期 (如 1/15 或 2/14-2/22)" onchange="updateCalendarItem(${index}, 'date', this.value)">
                        <input type="text" value="${escapeHtml(item.event)}" placeholder="事項" onchange="updateCalendarItem(${index}, 'event', this.value)">
                        <input type="text" value="${escapeHtml(item.detail)}" placeholder="說明" onchange="updateCalendarItem(${index}, 'detail', this.value)">
                        <button onclick="removeCalendarItem(${index})" class="btn btn-danger btn-icon">×</button>
                    </div>
                `).join('');
            }

            // Escape HTML
            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Update item
            function updateItem(section, index, field, value) {
                const key = section === 'taxNews' ? 'tax_news' : section;
                if (!reportData[key]) reportData[key] = [];
                if (!reportData[key][index]) reportData[key][index] = {};
                reportData[key][index][field] = value;
            }

            // Update calendar item
            function updateCalendarItem(index, field, value) {
                if (!reportData.calendar) reportData.calendar = [];
                if (!reportData.calendar[index]) reportData.calendar[index] = {};
                reportData.calendar[index][field] = value;
            }

            // Add item
            function addItem(section) {
                const key = section === 'taxNews' ? 'tax_news' : section;
                if (!reportData[key]) reportData[key] = [];
                reportData[key].push({ title: '', content: '' });
                renderItems(section, reportData[key]);
            }

            // Add calendar item
            function addCalendarItem() {
                if (!reportData.calendar) reportData.calendar = [];
                reportData.calendar.push({ date: '', event: '', detail: '' });
                renderCalendarItems(reportData.calendar);
            }

            // Remove item
            function removeItem(section, index) {
                const key = section === 'taxNews' ? 'tax_news' : section;
                if (reportData[key]) {
                    reportData[key].splice(index, 1);
                    renderItems(section, reportData[key]);
                }
            }

            // Remove calendar item
            function removeCalendarItem(index) {
                if (reportData.calendar) {
                    reportData.calendar.splice(index, 1);
                    renderCalendarItems(reportData.calendar);
                }
            }

            // Save report
            async function saveReport() {
                const quotes = document.getElementById('quotesInput').value;

                try {
                    const response = await fetch(`/api/report/${editingMonth}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            quotes: quotes,
                            completed: reportData.completed || [],
                            focus: reportData.focus || [],
                            tax_news: reportData.tax_news || [],
                            calendar: reportData.calendar || []
                        })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        showSuccessMessage(`成功更新 ${formatMonth(editingMonth)} 月報`);
                        showDashboard();
                    } else {
                        alert(data.detail || '儲存失敗');
                    }
                } catch (error) {
                    alert('連線失敗');
                }
            }

            // Sync staff
            async function syncStaff() {
                try {
                    const response = await fetch('/api/staff/sync', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    const data = await response.json();

                    if (data.success) {
                        showSuccessMessage(data.message);
                    } else {
                        alert(data.error || '同步失敗');
                    }
                } catch (error) {
                    alert('連線失敗');
                }
            }

            // Show success message
            function showSuccessMessage(message) {
                const el = document.getElementById('successMessage');
                el.textContent = message;
                el.style.display = 'block';
                setTimeout(() => {
                    el.style.display = 'none';
                }, 3000);
            }

            // Generate quote using AI
            async function generateQuote() {
                if (!confirm('確定要使用 AI 自動生成激勵金句嗎?')) {
                    return;
                }

                try {
                    const response = await fetch('/api/generate/quote', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        document.getElementById('quotesInput').value = data.quote;
                        alert('✅ 成功生成激勵金句!');
                    } else {
                        alert(data.detail || '生成失敗');
                    }
                } catch (error) {
                    alert('連線失敗: ' + error.message);
                }
            }

            // Generate tax news using AI
            async function generateTaxNews() {
                if (!confirm(`確定要使用 AI 自動生成 5 則稅務快訊嗎?

這將會替換現有的稅務快訊內容。`)) {
                    return;
                }

                try {
                    const response = await fetch('/api/generate/tax-news', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        // Clear existing tax news
                        reportData.tax_news = data.tax_news;
                        renderItems('taxNews', reportData.tax_news);
                        alert('✅ 成功生成 5 則稅務快訊!');
                    } else {
                        alert(data.detail || '生成失敗');
                    }
                } catch (error) {
                    alert('連線失敗: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=admin_html)

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "database": "connected"}

# ==================== 認證 API ====================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """登入並取得 JWT Token"""
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == request.username).first()

        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="此帳號已停用"
            )

        access_token = create_access_token(data={"sub": user.username})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username
        }
    finally:
        db.close()

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """取得當前登入用戶資訊"""
    return current_user

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

@app.get("/api/reports")
async def get_all_reports():
    """API：列出所有月報（供歷史瀏覽用）"""
    db = SessionLocal()
    try:
        reports = db.query(MonthlyReport).order_by(MonthlyReport.month.desc()).all()
        return {
            "total": len(reports),
            "reports": [
                {
                    "month": r.month,
                    "quotes": r.quotes[:50] + "..." if r.quotes and len(r.quotes) > 50 else r.quotes
                }
                for r in reports
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

@app.post("/api/report")
async def create_report(report_data: ReportCreate, current_user: dict = Depends(get_current_user)):
    """API：新增月報（需認證）"""
    db = SessionLocal()
    try:
        # 檢查月份是否已存在
        existing = db.query(MonthlyReport).filter(MonthlyReport.month == report_data.month).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"月份 {report_data.month} 的月報已存在"
            )

        new_report = MonthlyReport(
            month=report_data.month,
            quotes=report_data.quotes,
            completed=json.dumps([item.dict() for item in report_data.completed], ensure_ascii=False),
            focus=json.dumps([item.dict() for item in report_data.focus], ensure_ascii=False),
            tax_news=json.dumps([item.dict() for item in report_data.tax_news], ensure_ascii=False),
            calendar=json.dumps([item.dict() for item in report_data.calendar], ensure_ascii=False)
        )
        db.add(new_report)
        db.commit()

        return {
            "success": True,
            "message": f"成功建立 {report_data.month} 月報",
            "month": report_data.month
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立月報失敗：{str(e)}"
        )
    finally:
        db.close()

@app.put("/api/report/{month}")
async def update_report(month: str, report_data: ReportUpdate, current_user: dict = Depends(get_current_user)):
    """API：更新月報（需認證）"""
    db = SessionLocal()
    try:
        report = db.query(MonthlyReport).filter(MonthlyReport.month == month).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到 {month} 的月報"
            )

        # 更新非空欄位
        if report_data.quotes is not None:
            report.quotes = report_data.quotes
        if report_data.completed is not None:
            report.completed = json.dumps([item.dict() for item in report_data.completed], ensure_ascii=False)
        if report_data.focus is not None:
            report.focus = json.dumps([item.dict() for item in report_data.focus], ensure_ascii=False)
        if report_data.tax_news is not None:
            report.tax_news = json.dumps([item.dict() for item in report_data.tax_news], ensure_ascii=False)
        if report_data.calendar is not None:
            report.calendar = json.dumps([item.dict() for item in report_data.calendar], ensure_ascii=False)

        db.commit()

        return {
            "success": True,
            "message": f"成功更新 {month} 月報",
            "month": month
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新月報失敗：{str(e)}"
        )
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

@app.post("/api/birthday/send")
async def send_birthday_cards_now():
    """API：立即發送今天的生日賀卡"""
    from email_service_oauth import EmailServiceOAuth
    from datetime import date

    db = SessionLocal()
    try:
        today = date.today()
        email_service = EmailServiceOAuth()

        # 取得所有同事
        all_staff = db.query(Staff).all()

        birthday_list = []
        success_count = 0

        for staff in all_staff:
            if not staff.birthday:
                continue

            try:
                # 解析生日格式：1970.1.5
                parts = staff.birthday.split('.')
                if len(parts) >= 3:
                    birth_month = int(parts[1])
                    birth_day = int(parts[2])

                    # 檢查是否為今天生日
                    if birth_month == today.month and birth_day == today.day:
                        birthday_list.append({
                            "name": staff.name,
                            "email": staff.email,
                            "birthday": staff.birthday
                        })

                        # 如果有 email，發送賀卡
                        if staff.email:
                            staff_data = {
                                "name": staff.name,
                                "email": staff.email
                            }
                            if email_service.send_birthday_card(staff_data):
                                success_count += 1

            except Exception as e:
                print(f"處理 {staff.name} 生日時發生錯誤：{e}")
                continue

        return {
            "success": True,
            "date": today.strftime("%Y-%m-%d"),
            "birthday_count": len(birthday_list),
            "email_sent": success_count,
            "birthdays": birthday_list
        }

    except Exception as e:
        return {"error": f"發送生日賀卡失敗：{str(e)}"}
    finally:
        db.close()

# ==================== AI 內容生成 API ====================

@app.post("/api/generate/quote")
async def generate_quote_api(current_user: dict = Depends(get_current_user)):
    """API：使用 AI 生成激勵金句（需認證）"""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API 未設定,請在環境變數中設定 GEMINI_API_KEY"
        )
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = """你是一位專業的財務主管,請為財務處月報生成一句激勵人心的金句。

要求:
- 繁體中文
- 20-30 字
- 與財務工作相關
- 正向、專業、有深度
- 只回傳金句本身,不要有其他說明

範例風格:
- 細緻的數字背後,是財務人對公司價值的守護。
- 精準的帳目,是企業穩健前行的基石。
"""
        
        response = model.generate_content(prompt)
        quote = response.text.strip()
        
        # 移除可能的引號
        quote = quote.strip('"').strip('"').strip('"')
        
        return {
            "success": True,
            "quote": quote
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成金句失敗: {str(e)}"
        )

@app.post("/api/generate/tax-news")
async def generate_tax_news_api(current_user: dict = Depends(get_current_user)):
    """API：使用 AI 生成 5 則稅務快訊（需認證）"""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API 未設定,請在環境變數中設定 GEMINI_API_KEY"
        )
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        current_month = datetime.now().strftime("%Y 年 %m 月")
        
        prompt = f"""你是一位台灣稅務專家,請生成 5 則 {current_month} 的稅務快訊。

要求:
- 繁體中文
- 每則包含「title」(10-15字) 和「content」(30-50字)
- 涵蓋台灣最新稅務法規、政策變動、申報提醒等
- 實用且專業
- 必須以 JSON 格式輸出,格式如下:
[
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}},
  {{"title": "標題", "content": "內容"}}
]

只回傳 JSON 陣列,不要有其他說明文字。
"""
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # 移除可能的 markdown 程式碼區塊標記
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        
        # 解析 JSON
        news_list = json.loads(content)
        
        # 驗證格式
        if not isinstance(news_list, list) or len(news_list) != 5:
            raise ValueError("生成的稅務快訊格式不正確")
        
        for item in news_list:
            if 'title' not in item or 'content' not in item:
                raise ValueError("稅務快訊項目缺少必要欄位")
        
        return {
            "success": True,
            "tax_news": news_list
        }
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析 AI 回應失敗: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ==================== 月份選擇 API ====================

@app.get("/api/reports/months")
async def get_available_months():
    """取得所有可用的月報月份列表"""
    db = SessionLocal()
    try:
        reports = db.query(MonthlyReport.month).order_by(MonthlyReport.month.desc()).all()
        months = [report.month for report in reports]
        return {"months": months}
    finally:
        db.close()


@app.get("/api/reports/{month}")
async def get_report_by_month(month: str):
    """取得指定月份的月報資料（JSON 格式）"""
    db = SessionLocal()
    try:
        # 驗證月份格式
        try:
            year, month_num = month.split('-')
            year = int(year)
            month_num = int(month_num)
            if month_num < 1 or month_num > 12:
                raise ValueError("月份必須在 1-12 之間")
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="月份格式錯誤，應為 YYYY-MM 格式"
            )
        
        # 查詢月報
        report = db.query(MonthlyReport).filter(MonthlyReport.month == month).first()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到 {month} 的月報資料"
            )
        
        # 解析 JSON 資料
        completed = json.loads(report.completed)
        focus = json.loads(report.focus)
        tax_news = json.loads(report.tax_news)
        calendar = json.loads(report.calendar)
        
        # 取得所有同事
        all_staff = db.query(Staff).all()
        
        # 取得當月壽星
        birthdays = get_current_month_birthdays(all_staff, month=month_num)
        
        return {
            "month": month,
            "quotes": report.quotes,
            "completed": completed,
            "focus": focus,
            "tax_news": tax_news,
            "calendar": calendar,
            "birthdays": birthdays
        }
    finally:
        db.close()
