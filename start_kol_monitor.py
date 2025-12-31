#!/usr/bin/env python
"""KOL 监控统一启动 - 多线程同时运行"""

import sys
import os
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot_service.transport.dingtalk import DingTalkClient
from bot_service.services.kol_monitor import SignalRadar, TraderRadar
from bot_service.config import Config


def main():
    """主函数"""
    print("=" * 60)
    print(" KOL 监控系统启动")
    print("=" * 60)
    print("📡 Signal Radar - KOL 消息监控")
    print("📊 Trader Radar - 交易员信号监控")
    print("=" * 60)
    print("提示: 按 Ctrl+C 停止\n")

    # 验证配置（对称验证）
    if not Config.validate_kol():
        print("❌ KOL 配置验证失败")
        return

    if not Config.validate_trader():
        print("❌ 交易员配置验证失败")
        return

    print("✅ 配置验证通过\n")

    # 创建两个钉钉客户端实例（对称配置）
    kol_dingtalk = DingTalkClient(
        webhook=os.getenv("DINGTALK_KOL_WEBHOOK"),
        secret=os.getenv("DINGTALK_KOL_SECRET")
    )

    trader_dingtalk = DingTalkClient(
        webhook=os.getenv("DINGTALK_TRADER_WEBHOOK"),
        secret=os.getenv("DINGTALK_TRADER_SECRET")
    )

    print(f"✅ KOL 推送配置已加载")
    print(f"✅ 交易员推送配置已加载\n")

    # 创建两个监控实例
    signal_radar = SignalRadar(kol_dingtalk)
    trader_radar = TraderRadar(trader_dingtalk)

    # 创建线程
    signal_thread = threading.Thread(
        target=signal_radar.monitor,
        name="[KOL消息]",
        daemon=True
    )

    trader_thread = threading.Thread(
        target=trader_radar.monitor,
        name="[交易员信号]",
        daemon=True
    )

    # 启动线程
    print("🚀 [KOL消息] Signal Radar 启动中...")
    signal_thread.start()

    print("🚀 [交易员信号] Trader Radar 启动中...")
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
