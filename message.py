    if not filtered_sets:
        print("⚠️ イベント時間に一致するファイルセットが見つかりませんでした。")
        print("📂 対象フォルダ:", user_input.target_folder)

        if grouped_sets:
            all_start_times = [g.start for g in grouped_sets]
            all_end_times = [g.end for g in grouped_sets]
            min_time = min(all_start_times)
            max_time = max(all_end_times)
            print(f"📊 処理対象フォルダのデータ範囲: {min_time} ～ {max_time}")
        else:
            print("📁 フォルダ内に有効なセンサーデータが見つかりませんでした。")

        print("📅 指定イベント:")
        for ev in user_input.events:
            print(f"   - {ev.event}: {ev.start_time} ～ {ev.end_time}")
    else:
        for g in filtered_sets:
            print(f"📦 {g.prefix}（{g.start}～{g.end}） → {len(g.files)}ファイル")
