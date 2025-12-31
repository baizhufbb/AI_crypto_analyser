#!/usr/bin/env python3
import json
import sys
import re

# 禁止的文件扩展名
BANNED_EXTS = ['.py', '.sh', '.bat', '.cmd', '.tmp']
# 允许的目录
ALLOWED_DIRS = ['scripts', 'crypto_analyzer', 'data']

def check_file_allowed(file_path: str) -> bool:
    """检查文件路径是否允许操作"""
    for ext in BANNED_EXTS:
        if file_path.endswith(ext):
            # 检查是否在允许的目录中
            if any(f'{dir}/' in file_path or f'{dir}\\' in file_path for dir in ALLOWED_DIRS):
                return True
            return False
    return True

def check_command_allowed(cmd: str) -> bool:
    """检查命令是否允许执行"""
    # 禁止安装包
    if re.search(r'\b(pip|npm|yarn)\s+install', cmd, re.I):
        return False
    # 禁止直接运行 python 脚本（除非在允许目录）
    if re.search(r'python\s+\S+\.py', cmd, re.I):
        if not any(dir in cmd for dir in ALLOWED_DIRS):
            return False
    return True

def main():
    # 从 stdin 读取 JSON
    try:
        input_data = json.load(sys.stdin)
    except:
        sys.exit(0)  # 无法解析则放行

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    allowed = True

    if tool_name in ['Write', 'Edit']:
        file_path = tool_input.get('file_path', '')
        allowed = check_file_allowed(file_path)
        if not allowed:
            print(f"❌ 禁止操作脚本文件: {file_path}", file=sys.stderr)
    elif tool_name == 'Bash':
        command = tool_input.get('command', '')
        allowed = check_command_allowed(command)
        if not allowed:
            print(f"❌ 禁止运行命令: {command}", file=sys.stderr)

    sys.exit(0 if allowed else 2)

if __name__ == '__main__':
    main()

