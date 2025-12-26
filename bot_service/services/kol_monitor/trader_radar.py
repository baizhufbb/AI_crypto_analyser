import os
import requests
from datetime import datetime
from bot_service.services.kol_monitor.base import BaseRadar


class TraderRadar(BaseRadar):
    """交易员信号监控"""
    
    def __init__(self, dingtalk_client):
        super().__init__('trader_monitor_state.json', dingtalk_client)
        self.api_url = os.getenv("TRADER_API_URL")
    
    def get_initial_state(self):
        return {'last_timestamps': {}}
    
    def get_api_url(self):
        return self.api_url
    
    def fetch_data(self):
        """获取交易员列表"""
        try:
            params = {
                'page': 1,
                'pageSize': 50,
                'platform': 'all',
                'filterEmpty': 'true',
                'hours': 24
            }
            response = requests.get(self.api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # API 返回结构: {"code": 0, "data": [...], ...}
                if isinstance(data, dict) and 'data' in data:
                    return data['data']
                print(f"⚠️ API 返回结构未知: {data.keys() if isinstance(data, dict) else type(data)}")
                return []
            print(f"❌ API 请求失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取交易员数据异常: {e}")
        return []
    
    def format_signal(self, trader, signal):
        """格式化单个信号为 Markdown"""
        trader_name = trader.get('name', '未知交易员')
        platform = trader.get('platform', '')
        win_rate = trader.get('winRate', 0)
        roi = trader.get('roi', 0)
        
        # 信号数据
        signal_type = signal.get('signalType', '')
        symbol = signal.get('symbol', '')
        side = signal.get('side', '')
        avg_price = signal.get('avgPrice', 0)
        quantity = signal.get('quantity', 0)
        timestamp_ms = signal.get('timestamp', 0)
        pnl = signal.get('pnl', 0)
        
        # 转换时间戳
        if timestamp_ms:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = '--:--'
        
        # 确定信号类型的emoji (使用小图标)
        if signal_type == 'OPEN':
            type_icon = '⚡'
            action_text = '开仓'
        elif signal_type == 'CLOSE':
            type_icon = '🏁'
            action_text = '平仓'
        else:
            type_icon = '📢'
            action_text = signal_type
        
        # 方向emoji
        if '多' in side:
            side_icon = '🟢' # 绿色代表多
        elif '空' in side:
            side_icon = '🔴' # 红色代表空
        else:
            side_icon = '⚪'
        
        # 构建消息
        msg = f"### {type_icon} {action_text}: {trader_name}\n\n"
        
        # 核心信息列表
        info_lines = [
            f"- **标的**: {symbol}",
            f"- **方向**: {side_icon} {side}",
            f"- **价格**: {avg_price}",
            f"- **数量**: {quantity}"
        ]
        
        # 如果是平仓，显示盈亏
        if signal_type == 'CLOSE' and pnl != 0:
            pnl_icon = '💰' if pnl > 0 else '💸'
            info_lines.append(f"- **盈亏**: {pnl_icon} {pnl:+.2f}%")
            
        info_lines.append(f"- **时间**: {time_str}")
        
        msg += "\n".join(info_lines)
        msg += "\n\n---\n"
        
        # 底部小字
        footer_parts = [f"胜率 {win_rate}%", f"ROI {roi}%"]
        if platform:
            footer_parts.append(platform)
            
        msg += f"> {' | '.join(footer_parts)}"
        
        return msg
    
    def process_new_items(self, state):
        """处理新信号"""
        last_timestamps = state.get('last_timestamps', {})
        print(f"💓 正在检查更新... (已跟踪 {len(last_timestamps)} 个交易员)")
        
        traders = self.fetch_data()
        
        if not traders:
            print("⚠️ 未获取到交易员数据")
            return False, state
        
        has_new = False
        
        for trader in traders:
            trader_id = str(trader.get('id', ''))
            trader_name = trader.get('name', '未知')
            recent_signals = trader.get('recentSignals', [])
            
            if not recent_signals:
                continue
            
            # 获取该交易员最新的信号时间戳
            latest_signal = recent_signals[0]
            latest_timestamp = latest_signal.get('timestamp', 0)
            
            # 检查是否是新信号
            last_timestamp = last_timestamps.get(trader_id, 0)
            
            if latest_timestamp > last_timestamp:
                # 找出所有新信号
                new_signals = [s for s in recent_signals if s.get('timestamp', 0) > last_timestamp]
                
                # 按时间戳排序（旧的先发）
                new_signals.sort(key=lambda x: x.get('timestamp', 0))
                
                for signal in new_signals:
                    content = self.format_signal(trader, signal)
                    signal_type = signal.get('signalType', '')
                    symbol = signal.get('symbol', '')
                    title = f"【{trader_name}】{signal_type} {symbol}"
                    
                    print(f"🔔 发现新信号: {trader_name} - {signal_type} {symbol}")
                    self.dingtalk.send(content, title=title)
                    has_new = True
                
                # 更新该交易员的最新时间戳
                last_timestamps[trader_id] = latest_timestamp
        
        state['last_timestamps'] = last_timestamps
        return has_new, state


def main():
    """入口函数"""
    from bot_service.transport.dingtalk import DingTalkClient
    
    dingtalk = DingTalkClient()
    radar = TraderRadar(dingtalk)
    radar.monitor()


if __name__ == "__main__":
    main()
