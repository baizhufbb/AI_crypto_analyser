import time
import logging
from typing import List, Dict, Any
from telegram import Message
from telegram.error import BadRequest

from bot_service.transport.telegram.formatter import format_for_telegram

logger = logging.getLogger(__name__)

class TelegramStreamRenderer:
    """
    负责将流式文本渲染到 Telegram 消息中。
    处理了消息分片、Markdown/HTML 格式化、防抖动更新等复杂逻辑。
    """
    
    def __init__(self, update_obj, initial_text: str = "..."):
        self.update = update_obj
        self.message_chain: List[Dict[str, Any]] = []
        self.last_update_time = 0
        self.update_interval = 1.5 # Telegram 限制频率
        self.initial_text = initial_text
        self.is_initialized = False

    async def initialize(self):
        """发送初始消息"""
        if not self.is_initialized:
            msg = await self.update.message.reply_text(self.initial_text)
            self.message_chain.append({'message': msg, 'content': ""})
            self.is_initialized = True

    async def render(self, full_content: str, force: bool = False):
        """
        渲染内容到 Telegram
        :param full_content: 当前完整的文本内容
        :param force: 是否强制更新（忽略频率限制）
        """
        if not self.is_initialized:
            await self.initialize()

        # 1. 频率限制检查
        current_time = time.time()
        if not force and (current_time - self.last_update_time < self.update_interval):
            return

        self.last_update_time = current_time
        
        try:
            await self._update_message_chain(full_content)
        except Exception as e:
            logger.debug(f"渲染消息失败: {e}")

    async def _update_message_chain(self, content: str):
        MAX_LENGTH = 3800 # 预留缓冲
        
        # 1. 智能切分
        chunks = []
        remaining_text = content
        
        while remaining_text:
            if len(remaining_text) <= MAX_LENGTH:
                chunks.append(remaining_text)
                break
            
            # 寻找最佳分割点
            split_idx = remaining_text.rfind('\n', 0, MAX_LENGTH)
            if split_idx == -1:
                split_idx = MAX_LENGTH
                
            chunks.append(remaining_text[:split_idx])
            remaining_text = remaining_text[split_idx:]
        
        # 2. 同步更新消息链
        for i, chunk_text in enumerate(chunks):
            # 如果需要新消息气泡
            if i >= len(self.message_chain):
                new_msg = await self.update.message.reply_text("...")
                self.message_chain.append({'message': new_msg, 'content': ""})
            
            # 检查内容变化
            current_msg_data = self.message_chain[i]
            display_text = chunk_text
            
            if current_msg_data['content'] != display_text:
                try:
                    # 格式化并发送
                    formatted_text = format_for_telegram(display_text)
                    await current_msg_data['message'].edit_text(formatted_text, parse_mode='HTML')
                except BadRequest as e:
                    # 忽略 "Message is not modified" 错误
                    if "Message is not modified" in str(e):
                        pass
                    else:
                        # 格式化失败回退
                        logger.warning(f"HTML 渲染失败，回退纯文本: {e}")
                        await current_msg_data['message'].edit_text(display_text)
                except Exception as e:
                    logger.error(f"消息编辑异常: {e}")
                
                current_msg_data['content'] = display_text

    async def finalize(self, final_content: str):
        """最终确认更新，确保最后状态一致"""
        if final_content:
            await self.render(final_content, force=True)
        elif self.message_chain:
            await self.message_chain[0]['message'].edit_text("⚠️ AI 未返回任何内容。")
    
    async def show_error(self, error_msg: str):
        """显示错误信息"""
        if not self.is_initialized:
            await self.initialize()
        await self.message_chain[0]['message'].edit_text(f"⚠️ 处理出错: {error_msg}")
