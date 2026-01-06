"""
郵件發送服務模組 (OAuth 2.0 版本)
使用 Gmail API + OAuth 2.0 發送郵件
"""

import os
import base64
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from jinja2 import Template

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API 權限範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class EmailServiceOAuth:
    """郵件服務類 (OAuth 2.0 版本)"""

    def __init__(self):
        """初始化郵件服務"""
        self.credentials_file = "credentials.json"
        self.token_file = "token.json"
        self.sender_name = os.getenv("SENDER_NAME", "財務處")
        self.sender_email = None
        self.service = None

        # 初始化 Gmail API 服務
        self._initialize_service()

    def _initialize_service(self):
        """初始化 Gmail API 服務"""
        creds = None

        # 優先從環境變數載入 OAuth 認證資訊（用於 Zeabur 等雲端環境）
        google_token = os.getenv("GOOGLE_OAUTH_TOKEN")
        google_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if google_refresh_token and google_client_id and google_client_secret:
            try:
                # 從環境變數建立 Credentials
                creds = Credentials(
                    token=google_token,
                    refresh_token=google_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=google_client_id,
                    client_secret=google_client_secret,
                    scopes=SCOPES
                )
                logger.info("✅ 從環境變數載入 OAuth 認證")

                # 如果 token 過期，自動刷新
                if not creds.valid:
                    if creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        logger.info("✅ 已刷新過期的 token")
            except Exception as e:
                logger.warning(f"⚠️  從環境變數載入認證失敗: {e}")
                creds = None

        # 如果環境變數沒有，檢查是否有已儲存的 token 檔案
        if not creds and os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.info("✅ 找到已儲存的認證 token 檔案")
            except Exception as e:
                logger.warning(f"⚠️  讀取 token 檔案失敗: {e}")

        # 如果沒有有效的認證，需要重新授權
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("✅ 已更新過期的 token")
                except Exception as e:
                    logger.warning(f"⚠️  更新 token 失敗: {e}")
                    creds = None

            if not creds:
                # 優先檢查環境變數中的 Client ID 和 Secret
                client_id = os.getenv("GOOGLE_CLIENT_ID")
                client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

                if client_id and client_secret:
                    # 使用環境變數建立 OAuth flow
                    logger.info("📝 使用 .env 中的 OAuth 設定")
                    try:
                        client_config = {
                            "installed": {
                                "client_id": client_id,
                                "client_secret": client_secret,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                                "redirect_uris": ["http://localhost"]
                            }
                        }

                        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                        creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
                        logger.info("✅ OAuth 認證成功（使用 .env 設定）")
                    except Exception as e:
                        logger.error(f"❌ OAuth 認證失敗: {e}")
                        return

                elif os.path.exists(self.credentials_file):
                    # 使用 credentials.json 檔案
                    logger.info("📝 使用 credentials.json 檔案")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES)
                        creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
                        logger.info("✅ OAuth 認證成功")
                    except Exception as e:
                        logger.error(f"❌ OAuth 認證失敗: {e}")
                        return
                else:
                    logger.error("❌ 找不到 OAuth 設定")
                    logger.error("   請在 .env 中設定 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET")
                    logger.error("   或從 Google Cloud Console 下載 credentials.json 檔案")
                    return

            # 儲存認證以供下次使用
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"✅ 已儲存認證至 {self.token_file}")
            except Exception as e:
                logger.warning(f"⚠️  儲存 token 失敗: {e}")

        try:
            # 建立 Gmail API 服務
            self.service = build('gmail', 'v1', credentials=creds)

            # 從環境變數讀取寄件人 Email，或使用認證的 Gmail 帳號
            self.sender_email = os.getenv("SENDER_EMAIL", "me")
            logger.info(f"✅ Gmail API 服務已初始化")
        except HttpError as error:
            logger.error(f"❌ 初始化 Gmail API 服務失敗: {error}")

    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str) -> bool:
        """
        發送郵件

        Args:
            to_email: 收件人 Email
            to_name: 收件人姓名
            subject: 郵件主旨
            html_content: HTML 郵件內容

        Returns:
            bool: 是否發送成功
        """
        if not self.service:
            logger.error("❌ Gmail API 服務未初始化")
            return False

        if not to_email:
            logger.warning(f"⚠️  {to_name} 沒有 Email，跳過")
            return False

        try:
            # 建立郵件
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.sender_name} <{self.sender_email}>"
            message['To'] = f"{to_name} <{to_email}>"

            # 加入 HTML 內容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)

            # 編碼郵件
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # 發送郵件
            send_message = {'raw': raw_message}
            self.service.users().messages().send(userId='me', body=send_message).execute()

            logger.info(f"✅ 郵件已發送：{to_name} ({to_email}) - {subject}")
            return True

        except HttpError as error:
            logger.error(f"❌ 發送郵件失敗：{to_name} ({to_email}) - {error}")
            return False
        except Exception as e:
            logger.error(f"❌ 發送郵件失敗：{to_name} ({to_email}) - {e}")
            return False

    def send_monthly_report(self, staff_list: List[Dict], report_data: Dict, month: str) -> int:
        """
        發送月報給所有同事

        Args:
            staff_list: 同事列表
            report_data: 月報資料
            month: 月份 (格式：2026-01)

        Returns:
            int: 成功發送的數量
        """
        logger.info(f"📧 開始發送 {month} 月報...")

        success_count = 0
        year, month_num = month.split('-')

        subject = f"【財務處月報】{year} 年 {int(month_num)} 月份月報"

        for staff in staff_list:
            html_content = self._generate_monthly_report_html(staff, report_data, month)
            if self.send_email(staff['email'], staff['name'], subject, html_content):
                success_count += 1

        logger.info(f"✅ 月報發送完成：成功 {success_count}/{len(staff_list)} 筆")
        return success_count

    def send_birthday_card(self, staff: Dict) -> bool:
        """
        發送生日賀卡

        Args:
            staff: 同事資料

        Returns:
            bool: 是否發送成功
        """
        logger.info(f"🎂 發送生日賀卡給 {staff['name']}...")

        subject = f"🎉 生日快樂！{staff['name']}"
        html_content = self._generate_birthday_card_html(staff)

        return self.send_email(staff['email'], staff['name'], subject, html_content)

    def send_holiday_card(self, staff_list: List[Dict], holiday_name: str) -> int:
        """
        發送節日賀卡給所有同事

        Args:
            staff_list: 同事列表
            holiday_name: 節日名稱

        Returns:
            int: 成功發送的數量
        """
        logger.info(f"🎊 開始發送{holiday_name}賀卡...")

        success_count = 0
        subject = f"🎊 {holiday_name}快樂！"

        for staff in staff_list:
            html_content = self._generate_holiday_card_html(staff, holiday_name)
            if self.send_email(staff['email'], staff['name'], subject, html_content):
                success_count += 1

        logger.info(f"✅ {holiday_name}賀卡發送完成：成功 {success_count}/{len(staff_list)} 筆")
        return success_count

    def _generate_monthly_report_html(self, staff: Dict, report_data: Dict, month: str) -> str:
        """生成月報 HTML"""
        template = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Microsoft JhengHei', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background-color: #272343; color: #ffd803; padding: 20px; text-align: center; border-radius: 5px; margin-bottom: 20px; }
                .greeting { font-size: 18px; margin-bottom: 20px; color: #333; }
                .section { margin: 20px 0; }
                .section-title { font-size: 16px; font-weight: bold; color: #272343; border-bottom: 2px solid #ffd803; padding-bottom: 5px; margin-bottom: 10px; }
                .footer { text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }
                a { color: #272343; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 財務處月報</h1>
                    <p>{{ month }} 月份</p>
                </div>

                <div class="greeting">
                    <p>親愛的 <strong>{{ name }}</strong>，您好！</p>
                    <p>{{ month }} 月份的財務處月報已出爐，請查閱。</p>
                </div>

                <div class="section">
                    <div class="section-title">📝 本月重點摘要</div>
                    <p>{{ summary }}</p>
                </div>

                <div class="section">
                    <div class="section-title">🔗 查看完整月報</div>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{{ report_url }}" style="background-color: #ffd803; color: #272343; padding: 12px 30px; border-radius: 5px; display: inline-block; font-weight: bold;">
                            點此查看完整月報
                        </a>
                    </p>
                </div>

                <div class="footer">
                    <p>財務處敬上</p>
                    <p>此郵件由系統自動發送，請勿直接回覆</p>
                </div>
            </div>
        </body>
        </html>
        """

        year, month_num = month.split('-')
        report_url = os.getenv("APP_URL", "http://localhost:8000")

        return Template(template).render(
            name=staff['name'],
            month=f"{year} 年 {int(month_num)} 月",
            summary=report_data.get('quotes', '本月財務工作已順利完成'),
            report_url=report_url
        )

    def _generate_birthday_card_html(self, staff: Dict) -> str:
        """生成生日賀卡 HTML"""
        template = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Microsoft JhengHei', Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.2); text-align: center; }
                .emoji { font-size: 80px; margin: 20px 0; }
                h1 { color: #272343; font-size: 32px; margin: 20px 0; }
                .message { font-size: 18px; color: #555; line-height: 1.8; margin: 20px 0; }
                .signature { margin-top: 40px; color: #666; font-size: 16px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">🎂🎉🎊</div>
                <h1>生日快樂！{{ name }}</h1>
                <div class="message">
                    <p>在這個特別的日子裡，</p>
                    <p>財務處全體同仁祝您：</p>
                    <p><strong>生日快樂、心想事成、工作順利！</strong></p>
                    <p>感謝您一直以來的辛勤付出與貢獻，</p>
                    <p>祝您新的一歲更加精彩！</p>
                </div>
                <div class="signature">
                    <p>財務處全體同仁 敬賀</p>
                </div>
            </div>
        </body>
        </html>
        """

        return Template(template).render(name=staff['name'])

    def _generate_holiday_card_html(self, staff: Dict, holiday_name: str) -> str:
        """生成節日賀卡 HTML"""

        # 根據不同節日設定不同樣式
        holiday_styles = {
            "聖誕節": {"emoji": "🎄🎅⛄", "color": "#c41e3a", "bg": "#165b33"},
            "新年": {"emoji": "🎆🎊✨", "color": "#ffd700", "bg": "#1a1a2e"},
            "農曆新年": {"emoji": "🧧🐉🏮", "color": "#ff0000", "bg": "#ffed4e"}
        }

        style = holiday_styles.get(holiday_name, {"emoji": "🎉🎊", "color": "#272343", "bg": "#667eea"})

        template = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Microsoft JhengHei', Arial, sans-serif; margin: 0; padding: 20px; background-color: {{ bg_color }}; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.3); text-align: center; }
                .emoji { font-size: 80px; margin: 20px 0; }
                h1 { color: {{ text_color }}; font-size: 36px; margin: 20px 0; }
                .message { font-size: 18px; color: #555; line-height: 1.8; margin: 20px 0; }
                .signature { margin-top: 40px; color: #666; font-size: 16px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">{{ emoji }}</div>
                <h1>{{ holiday }}快樂！</h1>
                <div class="message">
                    <p>親愛的 <strong>{{ name }}</strong>，</p>
                    <p>在這個美好的{{ holiday }}，</p>
                    <p>財務處全體同仁</p>
                    <p>祝您佳節愉快、闔家平安！</p>
                </div>
                <div class="signature">
                    <p>財務處全體同仁 敬賀</p>
                </div>
            </div>
        </body>
        </html>
        """

        return Template(template).render(
            name=staff['name'],
            holiday=holiday_name,
            emoji=style['emoji'],
            text_color=style['color'],
            bg_color=style['bg']
        )

# 建立全域 Email 服務實例
email_service = EmailServiceOAuth()
