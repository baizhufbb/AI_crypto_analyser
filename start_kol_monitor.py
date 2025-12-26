#!/usr/bin/env python
"""KOL 监控统一启动 - 多线程同时运行"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot_service.transport.dingtalk import DingTalkClient
from bot_service.services.kol_monitor import SignalRadar, TraderRadar


def main():
    """主函数"""
    print("=" * 60)
    print("� KOL 监控系统启动")
    print("=" * 60)
    print("📡 Signal Radar - KOL 消息监控")
    print("📊 Trader Radar - 交易员信号监控")
    print("=" * 60)
    print("提示: 按 Ctrl+C 停止\n")
    
    # 创建钉钉客户端
    dingtalk = DingTalkClient()
    
    # 创建两个监控实例
    signal_radar = SignalRadar(dingtalk)
    trader_radar = TraderRadar(dingtalk)
    
    # 创建线程
    signal_thread = threading.Thread(
        target=signal_radar.monitor,
        name="SignalRadar",
        daemon=True
    )
    
    trader_thread = threading.Thread(
        target=trader_radar.monitor,
        name="TraderRadar",
        daemon=True
    )
    
    # 启动线程
    print("🚀 [Signal Radar] 启动中...")
    signal_thread.start()
    
    print("🚀 [Trader Radar] 启动中...")
    trader_thread.start()
    
    try:
        # 保持主线程运行
        signal_thread.join()
        trader_thread.join()
    except KeyboardInterrupt:
        print("\n\n⏹️  正在停止监控...")
        print("✅ 监控已停止")


if __name__ == "__main__":
    main()
