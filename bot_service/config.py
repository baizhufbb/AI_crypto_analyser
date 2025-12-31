import os
import logging
from typing import Optional

# 配置日志
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "bot.log")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """统一配置管理类"""
    
    # Telegram 配置
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USER_IDS: list[int] = [
        int(uid.strip()) 
        for uid in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",") 
        if uid.strip().isdigit()
    ]
    
    # 钉钉配置
    DINGTALK_KOL_WEBHOOK: str = os.getenv("DINGTALK_KOL_WEBHOOK", "")
    DINGTALK_KOL_SECRET: str = os.getenv("DINGTALK_KOL_SECRET", "")
    DINGTALK_TRADER_WEBHOOK: str = os.getenv("DINGTALK_TRADER_WEBHOOK", "")
    DINGTALK_TRADER_SECRET: str = os.getenv("DINGTALK_TRADER_SECRET", "")

    # API 配置
    KOL_API_URL: str = os.getenv("KOL_API_URL", "")
    TRADER_API_URL: str = os.getenv("TRADER_API_URL", "")
    
    # 代理配置 (httpx/requests 会自动读取，这里仅做检查)
    HTTPS_PROXY: Optional[str] = os.getenv("HTTPS_PROXY")
    
    @classmethod
    def validate_telegram(cls):
        """检查 Telegram 必要配置"""
        if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_ALLOWED_USER_IDS:
            logger.error("❌ 未找到 TELEGRAM_BOT_TOKEN 或 TELEGRAM_ALLOWED_USER_IDS")
            return False
        return True

    @classmethod
    def validate_kol(cls):
        """检查 KOL 监控必要配置"""
        if not cls.DINGTALK_KOL_WEBHOOK or not cls.KOL_API_URL:
            logger.error("❌ 未找到 DINGTALK_KOL_WEBHOOK 或 KOL_API_URL")
            return False
        return True

    @classmethod
    def validate_trader(cls):
        """检查交易员监控必要配置"""
        if not cls.DINGTALK_TRADER_WEBHOOK or not cls.TRADER_API_URL:
            logger.error("❌ 未找到 DINGTALK_TRADER_WEBHOOK 或 TRADER_API_URL")
            return False
        return True
