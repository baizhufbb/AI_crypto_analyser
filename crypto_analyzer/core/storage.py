import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import OUTPUT_DIR


def build_output_path(
    exchange: str, symbol: str, interval: str, records: List[Dict[str, Any]]
) -> Path:
    """
    构建输出文件路径，格式：data/{exchange}/{symbol}/{interval}/{timestamp}_{count}.json

    使用当前时间作为文件名时间戳，更准确反映数据拉取时间。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    interval_token = interval.replace("/", "-")
    folder = OUTPUT_DIR / exchange.lower() / symbol.upper() / interval_token
    count = len(records) if records else 0
    filename = f"{timestamp}_{count}.json"
    return folder / filename


def save_json(data: Any, output_path: Path) -> None:
    """保存数据为 JSON 文件，并删除同目录下的旧文件（只保留最新的一个）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    cleanup_old_files(output_path)


def cleanup_old_files(keep_file: Path) -> None:
    """删除同目录下的其他 JSON 文件，只保留指定的文件。"""
    directory = keep_file.parent
    if not directory.exists():
        return

    json_files = list(directory.glob("*.json"))
    if len(json_files) <= 1:
        return

    for json_file in json_files:
        if json_file == keep_file:
            continue
        try:
            json_file.unlink()
        except Exception as exc:  # pragma: no cover - best effort cleanup
            print(f"警告：删除旧文件 {json_file} 失败：{exc}", file=sys.stderr)



def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)
