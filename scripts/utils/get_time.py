from __future__ import annotations

from datetime import datetime, timezone


def main() -> None:
    """打印当前本地时间及 UTC 时间，供 AI 解析使用。

    输出示例：
    local: 2025-11-19 19:18:30
    utc:   2025-11-19 11:18:30
    """

    # 当前本地时间（遵循运行环境时区）
    local_now = datetime.now()
    # 当前 UTC 时间
    utc_now = datetime.now(timezone.utc)

    print("local:", local_now.strftime("%Y-%m-%d %H:%M:%S"))
    print("utc:", utc_now.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
