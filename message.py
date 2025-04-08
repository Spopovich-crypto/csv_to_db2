
import pandas as pd
import zipfile
import io
from pathlib import Path
from typing import Optional


def read_csv_cleaned(file: "FileMetadata", encoding: str) -> pd.DataFrame:
    if file.source_zip:
        with zipfile.ZipFile(file.source_zip, "r") as zipf:
            raw_bytes = zipf.read(file.internal_path)
            raw_str = raw_bytes.decode(encoding)
    else:
        with open(file.source_file, "r", encoding=encoding) as f:
            raw_str = f.read()

    cleaned_lines = [line.rstrip(",") for line in raw_str.splitlines()]
    cleaned_str = "\n".join(cleaned_lines)

    return pd.read_csv(io.StringIO(cleaned_str), header=[0, 1, 2], dtype=str)


def convert_csv_to_long_format(file: "FileMetadata", encoding: str) -> pd.DataFrame:
    print(f"   ├─ 処理中: {Path(file.source_file).name} [{file.sensor_type}]")

    df = read_csv_cleaned(file, encoding=encoding)
    df = df.loc[:, ~df.columns.duplicated()]

    valid_cols = []
    time_col = df.columns[0]
    for col in df.columns:
        if col == time_col:
            valid_cols.append(col)
            continue
        param_id, param_name, unit = map(str.strip, col)
        if param_name != "－" or unit != "－":
            valid_cols.append(col)

    df = df.loc[:, valid_cols]
    df.columns = ['|'.join(filter(None, map(str, col))).strip() for col in df.columns]

    time_col = df.columns[0]
    df_long = df.melt(id_vars=[time_col], var_name="parameter_full", value_name="value")

    df_long.rename(columns={time_col: "timestamp"}, inplace=True)
    df_long["timestamp"] = pd.to_datetime(df_long["timestamp"], errors="coerce")

    df_long[["parameter_id", "parameter_name", "unit"]] = df_long["parameter_full"].str.split("|", expand=True)
    df_long["parameter_id"] = df_long["parameter_id"].str.strip()
    df_long["parameter_name"] = df_long["parameter_name"].str.strip()
    df_long["unit"] = df_long["unit"].str.strip()

    df_long["source_file"] = file.source_file
    df_long["sensor_type"] = file.sensor_type

    return df_long[[
        "timestamp", "parameter_id", "parameter_name", "unit",
        "value", "source_file", "sensor_type"
    ]]


def convert_group_to_long_df(group: "GroupedSensorFileSet", encoding: str) -> pd.DataFrame:
    print(f"\n📦 セット処理開始: {group.prefix}")
    print(f"├─ ファイル数: {len(group.files)}")

    dfs = []
    seen_params = set()

    for f in group.files:
        try:
            df = convert_csv_to_long_format(f, encoding)
            df = df[~df["parameter_id"].isin(seen_params)]
            seen_params.update(df["parameter_id"].unique())
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ {f.source_file} の読み込みに失敗: {e}")

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def register_to_duckdb(db_path: str, df: pd.DataFrame):
    import duckdb

    con = duckdb.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            timestamp TIMESTAMP,
            parameter_id TEXT,
            parameter_name TEXT,
            unit TEXT,
            value TEXT,
            source_file TEXT,
            sensor_type TEXT
        )
    """)

    con.register("temp_df", df)
    con.execute("""
        INSERT INTO sensor_data
        SELECT * FROM temp_df
        EXCEPT
        SELECT * FROM sensor_data
    """)
    con.unregister("temp_df")
    con.close()
    print(f"✅ DuckDB登録: {len(df)} 行追加しました")
