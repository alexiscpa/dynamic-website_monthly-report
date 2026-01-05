"""
定時任務排程器
負責排程月報發送、生日賀卡、節日賀卡
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from lunarcalendar import Converter, Lunar
import logging
import json

# 使用 OAuth 版本的郵件服務
from email_service_oauth import email_service

logger = logging.getLogger(__name__)

class SchedulerService:
    """排程服務類"""

    def __init__(self, db_session_maker):
        """
        初始化排程服務

        Args:
            db_session_maker: SQLAlchemy Session Maker
        """
        self.scheduler = AsyncIOScheduler()
        self.SessionLocal = db_session_maker

    def start(self):
        """啟動排程器"""
        logger.info("🕐 啟動定時任務排程器...")

        # 每月第一天上午 9:00 發送月報
        self.scheduler.add_job(
            self.send_monthly_reports,
            CronTrigger(day=1, hour=9, minute=0),
            id='monthly_report',
            name='發送月報',
            replace_existing=True
        )

        # 每天上午 8:00 檢查生日
        self.scheduler.add_job(
            self.check_and_send_birthday_cards,
            CronTrigger(hour=8, minute=0),
            id='birthday_check',
            name='檢查生日',
            replace_existing=True
        )

        # 聖誕節 12/25 上午 8:00
        self.scheduler.add_job(
            self.send_christmas_cards,
            CronTrigger(month=12, day=25, hour=8, minute=0),
            id='christmas',
            name='聖誕賀卡',
            replace_existing=True
        )

        # 新年 1/1 上午 0:00
        self.scheduler.add_job(
            self.send_new_year_cards,
            CronTrigger(month=1, day=1, hour=0, minute=0),
            id='new_year',
            name='新年賀卡',
            replace_existing=True
        )

        # 每天檢查是否為農曆新年（因為日期每年不同）
        self.scheduler.add_job(
            self.check_lunar_new_year,
            CronTrigger(hour=0, minute=0),
            id='lunar_new_year_check',
            name='檢查農曆新年',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("✅ 定時任務排程器已啟動")

    def shutdown(self):
        """關閉排程器"""
        logger.info("🛑 關閉定時任務排程器...")
        self.scheduler.shutdown()

    async def send_monthly_reports(self):
        """發送月報給所有同事"""
        logger.info("📧 定時任務：發送月報")

        try:
            from main import MonthlyReport, Staff

            db = self.SessionLocal()

            # 取得上個月的月報
            today = date.today()
            last_month = (today.replace(day=1) - relativedelta(days=1))
            month_str = last_month.strftime("%Y-%m")

            # 查詢月報
            report = db.query(MonthlyReport).filter(MonthlyReport.month == month_str).first()

            if not report:
                logger.warning(f"⚠️  找不到 {month_str} 的月報")
                db.close()
                return

            # 取得所有同事
            staff_list = db.query(Staff).all()
            staff_data = [
                {"name": s.name, "email": s.email}
                for s in staff_list if s.email
            ]

            # 準備月報資料
            report_data = {
                "quotes": report.quotes,
                "completed": json.loads(report.completed),
                "focus": json.loads(report.focus)
            }

            # 發送郵件
            success_count = email_service.send_monthly_report(
                staff_data, report_data, month_str
            )

            logger.info(f"✅ 月報發送完成：{success_count}/{len(staff_data)} 筆")

            db.close()

        except Exception as e:
            logger.error(f"❌ 發送月報失敗：{e}")

    async def check_and_send_birthday_cards(self):
        """檢查今天是否有人生日並發送賀卡"""
        logger.info("🎂 定時任務：檢查生日")

        try:
            from main import Staff

            db = self.SessionLocal()
            today = date.today()

            # 取得所有同事
            all_staff = db.query(Staff).all()

            birthday_count = 0

            for staff in all_staff:
                if not staff.birthday or not staff.email:
                    continue

                try:
                    # 解析生日格式：1970.1.5
                    parts = staff.birthday.split('.')
                    if len(parts) >= 3:
                        birth_month = int(parts[1])
                        birth_day = int(parts[2])

                        # 檢查是否為今天生日
                        if birth_month == today.month and birth_day == today.day:
                            staff_data = {
                                "name": staff.name,
                                "email": staff.email
                            }

                            if email_service.send_birthday_card(staff_data):
                                birthday_count += 1

                except Exception as e:
                    logger.error(f"處理 {staff.name} 生日時發生錯誤：{e}")
                    continue

            if birthday_count > 0:
                logger.info(f"✅ 生日賀卡發送完成：{birthday_count} 筆")
            else:
                logger.info("ℹ️  今天沒有壽星")

            db.close()

        except Exception as e:
            logger.error(f"❌ 檢查生日失敗：{e}")

    async def send_christmas_cards(self):
        """發送聖誕節賀卡"""
        logger.info("🎄 定時任務：發送聖誕賀卡")
        await self._send_holiday_cards("聖誕節")

    async def send_new_year_cards(self):
        """發送新年賀卡"""
        logger.info("🎆 定時任務：發送新年賀卡")
        await self._send_holiday_cards("新年")

    async def check_lunar_new_year(self):
        """檢查是否為農曆新年"""
        try:
            today = date.today()

            # 轉換為農曆
            lunar = Converter.Solar2Lunar(today.year, today.month, today.day)

            # 檢查是否為農曆正月初一
            if lunar.month == 1 and lunar.day == 1:
                logger.info("🧧 今天是農曆新年！")
                await self._send_holiday_cards("農曆新年")

        except Exception as e:
            logger.error(f"❌ 檢查農曆新年失敗：{e}")

    async def _send_holiday_cards(self, holiday_name: str):
        """
        發送節日賀卡給所有同事

        Args:
            holiday_name: 節日名稱
        """
        try:
            from main import Staff

            db = self.SessionLocal()

            # 取得所有同事
            all_staff = db.query(Staff).all()
            staff_data = [
                {"name": s.name, "email": s.email}
                for s in all_staff if s.email
            ]

            # 發送郵件
            success_count = email_service.send_holiday_card(staff_data, holiday_name)

            logger.info(f"✅ {holiday_name}賀卡發送完成：{success_count}/{len(staff_data)} 筆")

            db.close()

        except Exception as e:
            logger.error(f"❌ 發送{holiday_name}賀卡失敗：{e}")

# 全域排程器實例（將在 main.py 中初始化）
scheduler_service = None
