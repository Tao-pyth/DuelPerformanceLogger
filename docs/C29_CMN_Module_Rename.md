# CMN モジュールリネーム影響調査

## 1. `cmn_` 参照影響範囲
`rg "cmn_"` で検出した、旧接頭辞 `cmn_` を参照している主なファイルを下表に整理した。

| 区分 | ファイル | 参照内容の概要 |
| --- | --- | --- |
| テスト | `tests/test_cmn_database.py` | `app.function.cmn_database` のインポート |
| ドキュメント | `docs/A06_Logging_Strategy.md` | ロギング関連で `cmn_logger` を参照 |
|  | `docs/C28_Wiki_Overview.md` | `cmn_app_state`・`cmn_resources`・`cmn_config`・`cmn_database` の紹介 |
|  | `docs/B11_Security_Standards.md` | `function.cmn_logger.sanitize` への言及 |
|  | `docs/A09_Naming_Conventions.md` | `cmn_database.py` の命名説明 |
|  | `docs/A01_Coding_Guidelines.md` | `cmn_error`・`cmn_logger` 等の利用規約 |
| アプリ本体 | `app/function/cmn_app_state.py` | `cmn_config` と `cmn_database` の相互参照 |
|  | `app/function/cmn_database.py` | `cmn_logger` の利用 |
|  | `app/function/__init__.py` | `cmn_app_state` と `cmn_database` を公開 |
|  | `app/function/cmn_logger.py` | ドキュメント文字列内で `cmn_database` を参照 |
|  | `app/function/core/recorder.py` | 遅延インポートで `cmn_database` を参照 |
|  | `app/function/core/migration_runner.py` | 遅延インポートで `cmn_database` を参照 |
|  | `app/main.py` | `cmn_config`・`cmn_logger`・`cmn_resources` をインポート |
| マイグレーション | `resource/db/migrations/V0.3.3__checks_only.py` | `cmn_database` を参照 |
|  | `resource/db/migrations/V0.4.0__checks_only.py` | `cmn_database` を参照 |

※その他、`cmn_` を含まないドキュメントでは接頭辞に依存する表記は見当たらなかった。

## 2. PyInstaller 設定および補助スクリプトの確認
- リポジトリ直下や `build/`・`scripts/pyinstaller/` といった既定ディレクトリに PyInstaller 用 spec ファイルは存在しない。
- `docs/C23_Rebuild_Policies_Script.py` を確認したが、`cmn_` 接頭辞のモジュール参照は含まれていないため、リネーム後の修正は不要と判断できる。

## 3. 一括リネーム実施チェックリスト
1. **ブランチ作成** – `git checkout -b feature/rename-cmn-modules` など専用ブランチを用意する。
2. **ファイルリネーム** – 旧ファイルを `git mv app/function/cmn_database.py app/function/db_manager.py` のように順次移動する。関連モジュール (`cmn_logger.py` → `logger.py` 等) も同様に対応する。
3. **インポート修正** – `rg "cmn_"` で検出した箇所を中心に、新しいモジュール名へ書き換える。特に遅延インポートや `__init__.py` の公開リスト、マイグレーションスクリプトを見落とさない。
4. **ドキュメント更新** – 上記一覧のドキュメントを新名称に合わせて更新する。ナレッジベースの整合性を保つため、該当箇所の文章も併せて点検する。
5. **テスト実行** – `pytest` やその他 CI コマンドを実行し、リネーム後もアプリケーションが動作することを確認する。
6. **最終確認** – `git status` や `pytest` ログを確認し、不要なファイルが残っていないかチェックした上で PR を作成する。

このチェックリストを順番に適用することで、`cmn_` 接頭辞を廃止するリネーム作業を安全に進められる。
