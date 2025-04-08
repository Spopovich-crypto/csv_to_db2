import json
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel

# --- 入力スキーマ定義 ---


class EventInfo(BaseModel):
    event: str
    description: str
    start_time: datetime
    end_time: datetime


class UserInput(BaseModel):
    target_folder: str
    name_patterns: List[str]
    encoding: str
    db_path: str
    plant_name: str
    machine_no: str
    label: str
    label_description: str
    events: List[EventInfo]


# --- ファイル名からメタ情報を抽出 ---


def extract_metadata_from_filename(file: Path) -> dict:
    # 元のパターン
    pattern = r"(?P<plant_code>[A-Z]+)#(?P<machine_code>\d+)(?P<datestr>\d{6})(?P<timestr>\d{6})_(?P<sensor_type>[^.]+)"
    match = re.match(pattern, file.name)
    if not match:
        print(f"⚠️ ファイル名の形式が不正です: {file.name}")
        return None
    date_str = match.group("datestr")
    time_str = match.group("timestr")
    dt = datetime.strptime(date_str + time_str, "%d%m%y%H%M%S")

    max_end_time = dt + timedelta(hours=2)

    file_mtime = None
    if file.exists():
        file_mtime = datetime.fromtimestamp(file.stat().st_mtime)

    end_time = min(max_end_time, file_mtime) if file_mtime else max_end_time

    return {
        "plant_name_from_file": match.group("plant_code"),
        "machine_code": match.group("machine_code"),
        "sensor_type": match.group("sensor_type"),
        "start_time": dt,
        "end_time": end_time,
        "source_file": str(file),
    }


# --- 指定フォルダからファイルを収集 ---


def collect_sensor_files(user_input: UserInput) -> List[Dict]:
    all_files = list(Path(user_input.target_folder).rglob("*"))
    collected = []

    for file in all_files:
        if file.suffix.lower() == ".csv" or file.suffix.lower() == ".zip":
            if any(pat in file.name for pat in user_input.name_patterns):
                if file.suffix.lower() == ".zip":
                    try:
                        with zipfile.ZipFile(file, "r") as zipf:
                            for zip_info in zipf.infolist():
                                if any(
                                    pat in zip_info.filename
                                    for pat in user_input.name_patterns
                                ):
                                    metadata = extract_metadata_from_filename(
                                        Path(zip_info.filename)
                                    )
                                    if metadata:
                                        metadata["source_zip"] = str(file)
                                        collected.append(metadata)
                    except zipfile.BadZipFile:
                        print(f"⚠️ ZIPファイルが壊れています: {file}")
                        continue
                else:
                    metadata = extract_metadata_from_filename(file)
                    if metadata:
                        collected.append(metadata)

    return collected


# --- datetimeをJSON変換するためのカスタムエンコーダ ---
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# --- サンプル実行用 ---

if __name__ == "__main__":
    import json

    # JSONファイルまたは文字列から読み込む例
    sample_input = {
        "target_folder": "data",
        "name_patterns": ["Cond", "Vib", "Tmp"],
        "encoding": "shift_jis",
        "db_path": "./sensor_data.duckdb",
        "plant_name": "東京工場",
        "machine_no": "No.101",
        "label": "2024年定期点検",
        "label_description": "負荷試験含む",
        "events": [
            {
                "event": "起動試験",
                "description": "冷間始動",
                "start_time": "2024-11-21T00:00:00",
                "end_time": "2024-11-21T00:30:00",
            }
        ],
    }

    user_input = UserInput(**sample_input)
    results = collect_sensor_files(user_input)

    # デバッグ情報を表示
    print(f"検索フォルダ: {user_input.target_folder}")
    print(f"検索パターン: {user_input.name_patterns}")
    print(f"見つかったファイル数: {len(results)}")

    # カスタムエンコーダを使用してJSONに変換
    print(json.dumps(results, indent=2, ensure_ascii=False, cls=DateTimeEncoder))
