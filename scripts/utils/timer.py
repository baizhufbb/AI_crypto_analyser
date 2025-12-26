import time
import sys
import platform

def reminder(minutes):
    try:
        seconds = int(minutes * 60)
    except ValueError:
        print("无效的时间输入")
        return

    print(f"⏰ 开始倒计时 {minutes} 分钟 ({seconds} 秒)...")
    
    try:
        # 显示进度
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            remaining = seconds - elapsed
            if remaining <= 0:
                break
            
            # 简单的进度显示，每秒更新一次
            mins, secs = divmod(int(remaining), 60)
            time_str = '{:02d}:{:02d}'.format(mins, secs)
            print(f"\r剩余时间: {time_str}", end="", flush=True)
            time.sleep(1)
            
        print(f"\r剩余时间: 00:00", end="", flush=True)
        print("\n\n🔔 时间到！")
        
        # 声音提醒 (Windows)
        if platform.system() == "Windows":
            try:
                import winsound
                # 连续响几声
                for _ in range(3):
                    winsound.Beep(1000, 500) # 频率 1000Hz, 持续 500ms
                    time.sleep(0.2)
                    
                # 弹窗提醒 - 已禁用
                # import ctypes
                # ctypes.windll.user32.MessageBoxW(0, f"{minutes} 分钟倒计时结束！", "提醒", 0x40 | 0x1)
            except ImportError:
                print('\a' * 5) # fallback
        else:
            # 其他系统使用简单的 beep 字符
            print('\a' * 5)
            
    except KeyboardInterrupt:
        print("\n\n⛔ 倒计时已取消。")

if __name__ == "__main__":
    print("--- 简单倒计时提醒脚本 ---")
    try:
        if len(sys.argv) > 1:
            mins = float(sys.argv[1])
        else:
            user_input = input("请输入倒计时分钟数: ")
            mins = float(user_input)
        
        reminder(mins)
    except ValueError:
        print("❌ 请输入有效的数字。")
