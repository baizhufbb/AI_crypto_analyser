from bot_service.agent.claude_client import ClaudeClient
from bot_service.transport.telegram.bot import TelegramBot

def main():
    # 初始化 Claude 客户端
    claude = ClaudeClient()
    
    # 初始化并启动 Telegram 机器人
    bot = TelegramBot(claude)
    bot.run()

if __name__ == '__main__':
    main()
