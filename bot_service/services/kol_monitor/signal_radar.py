import os
import requests
from bot_service.services.kol_monitor.base import BaseRadar
from bot_service.config import Config


class SignalRadar(BaseRadar):
    """KOL消息监控"""

    def __init__(self, dingtalk_client):
        super().__init__('signal_monitor_state.json', dingtalk_client, "[KOL消息]")
        self.api_url = Config.KOL_API_URL

    def get_initial_state(self):
        return {'last_id': 0}

    def get_api_url(self):
        return self.api_url
    
    def fetch_data(self):
        """获取KOL消息"""
        try:
            response = requests.get(self.api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # 正确的解析逻辑: 提取 'messages' 字段
                if isinstance(data, dict) and 'messages' in data:
                    return data['messages']
                
                # 兼容性处理: 万一它有时候直接返回列表
                if isinstance(data, list):
                    return data
                    
                print(f"{self.log_prefix} ⚠️ API 返回结构未知: {data.keys() if isinstance(data, dict) else type(data)}")
                return []

            print(f"{self.log_prefix} ❌ API 请求失败: {response.status_code}")
        except Exception as e:
            print(f"{self.log_prefix} ❌ 获取消息异常: {e}")
        return []
    
    def format_message(self, item):
        """格式化消息内容 (Markdown)"""
        # 基础信息
        author_nickname = item.get('author_nickname', '')
        author_username = item.get('author_username', '')
        content = item.get('message_content', '').strip()
        analysis = item.get('analysis', '')
        signal = item.get('signal', '')
        images = item.get('images') or []
        msg_time = item.get('message_time', '')
        
        # 来源信息
        channel = item.get('channel_name', '')
        platform = item.get('platform', '')
        guild_name = item.get('guild_name', '')
        
        # 作者显示名称
        author_display = author_nickname if author_nickname else (author_username if author_username else '未知作者')
        
        # 1. 标题
        msg = f"### 📢 {author_display}\n\n"
        
        # 2. 时间引用
        if msg_time:
            msg += f"> 🕒 {msg_time}\n\n"
        
        # 3. 正文内容
        if content:
            msg += f"{content}\n\n"
        
        # 4. 图片展示
        if images:
            for img in images:
                msg += f"![image]({img})\n"
            msg += "\n"
        
        # 5. 关键信息区 (使用列表)
        info_lines = []
        if signal:
            info_lines.append(f"- **信号**: {signal}")
        if analysis:
            info_lines.append(f"- **分析**: {analysis}")
            
        # 来源组合
        source_parts = []
        if platform: source_parts.append(platform)
        if guild_name: source_parts.append(guild_name)
        if channel: source_parts.append(channel)
        
        if source_parts:
            info_lines.append(f"- **来源**: {' | '.join(source_parts)}")
            
        if info_lines:
            msg += "---\n" + "\n".join(info_lines)
            
        return msg
    
    def process_new_items(self, state):
        """处理新消息"""
        last_id = state.get('last_id', 0)
        print(f"{self.log_prefix} 💓 正在检查更新... (上次 ID: {last_id})")

        messages = self.fetch_data()

        # 按 ID 排序 (旧 -> 新)
        messages.sort(key=lambda x: x.get('id', 0))

        new_last_id = last_id
        has_new = False

        for item in messages:
            msg_id = item.get('id')
            if msg_id > last_id:
                content = self.format_message(item)
                print(f"{self.log_prefix} 🔔 发现新消息 ID: {msg_id}")
                
                # 优先使用昵称，无昵称时使用用户名
                author_nickname = item.get('author_nickname', '')
                author_username = item.get('author_username', '')
                author_display = author_nickname if author_nickname else (author_username if author_username else 'KOL')
                
                title = f"【{author_display}】新消息"
                self.dingtalk.send(content, title=title)
                new_last_id = msg_id
                has_new = True
        
        if new_last_id > last_id:
            state['last_id'] = new_last_id
        
        return has_new, state


def main():
    """入口函数"""
    from bot_service.transport.dingtalk import DingTalkClient
    
    dingtalk = DingTalkClient()
    radar = SignalRadar(dingtalk)
    radar.monitor()


if __name__ == "__main__":
    main()
