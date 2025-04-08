if not filtered_sets:
    print("⚠️ イベント時間に一致するファイルセットが見つかりませんでした。")
    print("👉 イベントの時間範囲と、ファイルの記録時間が重なっているか確認してください。")
    print("📂 処理対象フォルダ:", user_input.target_folder)
    print("📅 指定イベント:")
    for ev in user_input.events:
        print(f"   - {ev.event}: {ev.start_time} ～ {ev.end_time}")