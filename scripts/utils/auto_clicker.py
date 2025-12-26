"""
自动输入和点击脚本
功能：遍历0000-9999的四位数字，每次输入后点击指定位置
"""

import pyautogui
import time
import sys


def get_screen_position(position_name):
    """
    获取屏幕上的位置坐标
    
    Args:
        position_name: 位置名称（用于提示）
    
    Returns:
        tuple: (x, y) 坐标
    """
    print(f"\n请将鼠标移动到【{position_name}】位置")
    print("5秒后将记录当前鼠标位置...")
    
    for i in range(5, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        time.sleep(1)
    
    position = pyautogui.position()
    print(f"\n已记录位置: {position}")
    return position


def auto_input_and_click(input_position, click_position, start_num=0, end_num=9999, delay=0.1, check_position=None):
    """
    自动输入四位数字并点击（平衡模式 + 成功检测）
    
    Args:
        input_position: 输入框位置 (x, y)
        click_position: 点击按钮位置 (x, y)
        start_num: 起始数字（默认0）
        end_num: 结束数字（默认9999）
        delay: 每次操作后的延迟时间（秒，默认0.1秒）
        check_position: 可选，检测成功的屏幕位置 (x, y)，用于检测界面变化
    """
    print(f"\n开始遍历 {start_num:04d} 到 {end_num:04d}")
    print("按 Ctrl+C 可随时停止\n")
    
    # 设置合理的pyautogui延迟
    pyautogui.PAUSE = 0.01
    
    # 如果设置了检测位置，记录初始颜色
    initial_color = None
    if check_position:
        initial_color = pyautogui.pixel(check_position[0], check_position[1])
        print(f"检测位置: {check_position}, 初始颜色: {initial_color}")
        print("当该位置颜色变化时，将自动停止\n")
    
    try:
        for num in range(start_num, end_num + 1):
            # 格式化为四位数字
            num_str = f"{num:04d}"
            
            # 点击输入框位置
            pyautogui.click(input_position[0], input_position[1])
            
            # 清空并输入
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.02)  # 等待清空完成
            pyautogui.write(num_str, interval=0.01)  # 快速输入
            
            # 点击确认按钮
            pyautogui.click(click_position[0], click_position[1])
            
            # 可选延迟
            if delay > 0:
                time.sleep(delay)
            
            # 检测是否成功（界面是否变化）
            if check_position:
                current_color = pyautogui.pixel(check_position[0], check_position[1])
                if current_color != initial_color:
                    print(f"\n🎉 成功！密码是: {num_str}")
                    print(f"检测位置颜色从 {initial_color} 变为 {current_color}")
                    return num_str
            
            # 打印进度（减少打印频率以提高速度）
            if num % 500 == 0:
                print(f"进度: {num:04d} / {end_num:04d}")
            
    except KeyboardInterrupt:
        print(f"\n\n用户中断，已处理到: {num:04d}")
        sys.exit(0)
    
    print(f"\n完成！共处理 {end_num - start_num + 1} 个数字，未找到匹配")
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("自动输入和点击脚本")
    print("=" * 60)
    
    # 安全提示
    print("\n注意：")
    print("1. 请确保目标窗口已打开并可见")
    print("2. 脚本运行时请勿移动鼠标")
    print("3. 按 Ctrl+C 可随时停止脚本")
    print("4. 建议先用小范围测试（如0-10）")
    
    input("\n按回车键继续...")
    
    # 获取输入框位置
    input_position = get_screen_position("输入框")
    
    # 获取点击按钮位置
    click_position = get_screen_position("确认按钮")
    
    # 询问是否需要成功检测
    print("\n" + "=" * 60)
    use_detection = input("是否启用成功检测？(y/n，默认y): ").lower() or "y"
    check_position = None
    
    if use_detection == 'y':
        print("\n成功检测说明：")
        print("当密码正确时，界面会发生变化（如弹窗、颜色变化等）")
        print("请选择一个会发生变化的屏幕位置进行监测")
        check_position = get_screen_position("成功检测位置（如弹窗的某个点）")
    
    # 确认位置
    print("\n" + "=" * 60)
    print(f"输入框位置: {input_position}")
    print(f"确认按钮位置: {click_position}")
    if check_position:
        print(f"检测位置: {check_position}")
    print("=" * 60)
    
    # 设置范围
    print("\n请设置遍历范围：")
    try:
        start_num = int(input("起始数字 (0-9999，默认0): ") or "0")
        end_num = int(input("结束数字 (0-9999，默认9999): ") or "9999")
        delay = float(input("每次操作延迟（秒，默认0.1）: ") or "0.1")
        
        # 验证范围
        if not (0 <= start_num <= 9999 and 0 <= end_num <= 9999):
            print("错误：数字必须在 0-9999 范围内")
            sys.exit(1)
        
        if start_num > end_num:
            print("错误：起始数字不能大于结束数字")
            sys.exit(1)
            
    except ValueError:
        print("错误：输入无效")
        sys.exit(1)
    
    # 最后确认
    print(f"\n将遍历 {start_num:04d} 到 {end_num:04d}，共 {end_num - start_num + 1} 个数字")
    confirm = input("确认开始？(y/n): ")
    
    if confirm.lower() != 'y':
        print("已取消")
        sys.exit(0)
    
    # 倒计时
    print("\n3秒后开始...")
    for i in range(3, 0, -1):
        print(f"{i}...", flush=True)
        time.sleep(1)
    
    # 开始执行
    result = auto_input_and_click(input_position, click_position, start_num, end_num, delay, check_position)
    
    if result:
        print(f"\n✅ 找到密码: {result}")
    else:
        print("\n❌ 未找到匹配的密码")


if __name__ == "__main__":
    main()
