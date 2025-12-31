import logging
from functools import wraps
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.error import NetworkError
from telegram.request import HTTPXRequest

from typing import Any
from bot_service.config import Config, logger
from bot_service.transport.telegram.renderer import TelegramStreamRenderer

# 关闭 httpx 的详细日志
logging.getLogger("httpx").setLevel(logging.WARNING)

def restrict_user(func):
    """限制只有特定用户可以使用机器人"""
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in Config.TELEGRAM_ALLOWED_USER_IDS:
            logger.warning(f"🚫 未授权访问: {user_id}")
            await update.message.reply_text("🚫 您无权使用此机器人。")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapped

class TelegramBot:
    """封装 Telegram Bot 的所有交互逻辑"""
    
    def __init__(self, llm_client: Any):
        self.llm = llm_client
        self.app = None

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理并记录错误，避免刷屏"""
        if isinstance(context.error, NetworkError):
            logger.warning(f"🌐 网络连接不稳定: {context.error} (正在重试...)")
        else:
            logger.error(f"⚠️ 发生未捕获错误: {context.error}")

    @restrict_user
    async def handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 和 /help 命令"""
        help_text = (
            "🤖 **加密货币分析助手**\n\n"
            "直接发送指令如：'分析 BTC'、'找找机会'\n\n"
            "**/clear** - 清除会话记忆\n"
            "**/start** - 显示此帮助"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    @restrict_user
    async def handle_clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /clear 命令"""
        user_id = update.effective_user.id
        
        if self.llm.user_sessions.get(user_id):
            old_session = self.llm.user_sessions[user_id]
            self.llm.clear_session(user_id)
            await update.message.reply_text(f"✅ 已清除会话 {old_session}\n下次对话将开始新会话。")
        else:
            await update.message.reply_text("ℹ️ 当前没有活跃会话。")

    @restrict_user
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理用户发送的文本消息"""
        user_text = update.message.text
        user_id = update.effective_user.id
        
        # 1. 准备渲染器
        has_session = self.llm.user_sessions.get(user_id)
        initial_text = "🤖 收到，正在分析..." if has_session else "🤖 开始分析..."
        
        renderer = TelegramStreamRenderer(update, initial_text)
        await renderer.initialize()
        
        # 2. 定义回调
        async def on_update(full_content: str):
            await renderer.render(full_content)
        
        # 3. 执行分析
        try:
            result = await self.llm.run_analysis_streaming(user_text, user_id, on_update)
            await renderer.finalize(result)
        
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            await renderer.show_error(str(e))

    def run(self):
        """启动机器人"""
        if not Config.validate_telegram():
            return
            
        print(f"🚀 机器人启动中...")
        print(f"只响应用户 ID: {Config.TELEGRAM_ALLOWED_USER_IDS}")
        
        application_builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)
        
        if Config.HTTPS_PROXY:
            proxy_url = Config.HTTPS_PROXY
            if not proxy_url.startswith("http"):
                proxy_url = f"http://{proxy_url}"

            print(f"🌐 使用代理: {proxy_url}")

            import httpx

            request = HTTPXRequest(
                connect_timeout=10.0,
                read_timeout=30.0,
                write_timeout=30.0,
                pool_timeout=30.0,
                connection_pool_size=10,  # 小连接池
                httpx_kwargs={
                    "proxy": proxy_url,
                    "limits": httpx.Limits(
                        max_connections=10,  # 最大连接数
                        max_keepalive_connections=5  # 允许 keep-alive
                    )
                }
            )
            application_builder.request(request)
            
        self.app = application_builder.build()
        
        # 注册处理器
        self.app.add_error_handler(self.error_handler)
        self.app.add_handler(CommandHandler("start", self.handle_start_command))
        self.app.add_handler(CommandHandler("help", self.handle_start_command))
        self.app.add_handler(CommandHandler("clear", self.handle_clear_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
        print("✅ 正在监听 Telegram 消息...")
        self.app.run_polling()
