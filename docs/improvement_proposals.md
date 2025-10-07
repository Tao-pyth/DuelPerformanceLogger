# 改善課題の提案リスト

以下は今後の改善課題として検討できるテーマと、その背景・作業内容・受け入れ条件を整理したものです。各項目は独立した PR として対応することを想定しています。

## 1. Ensure KV loading order and resource path setup; add guard comments

**Background**

`resource_add_path(...)` を `Builder.load_file(app.kv)` より先に呼ぶ前提となっている。取り違え防止のため、コードコメントや README で明示し、誤った順序を検出する軽いガードを入れる。

**Tasks**

- `main.py` に「`resource_add_path` は `Builder` より前」とコメントを追加する。
- ローダを関数化し、順序を内部で強制する。
- README に順序ルールを 1 行追記する。

**Acceptance Criteria**

- 既存起動経路で順序が確実に守られる。
- コメントと README に順序が明記されている。

## 2. Add CI check to ensure `<ClassName>:` in KV matches Python screen classes

**Background**

`<FooScreen>:` と Python 側の `class FooScreen(MDScreen)` の不一致は事故の原因になる。

**Tasks**

- `screens/*.kv` から `<ClassName>:` を抽出するスクリプトを追加する。
- `function/screen/*.py` から `class .*Screen` を抽出するスクリプトを追加する。
- 差分があれば CI を失敗させる。

**Acceptance Criteria**

- CI で不一致が検出される。
- 既存の構成では CI がグリーンになる。

## 3. Add headless smoke test to parse `app.kv` in CI

**Background**

KV ファイルの文法や依存関係の崩れを早期に検知したい。

**Tasks**

- CI で `Builder.load_file("resource/theme/gui/app.kv")` を 1 回実行する。
- 例外時に失敗させる。

**Acceptance Criteria**

- Windows と Ubuntu でテストがグリーンになる。
- KV パースエラーを即時に検知できる。

## 4. Introduce style tokens (Spacing/Typo/Radius/Color) and seed usage

**Background**

余白・角丸・フォントサイズをトークン化して一貫性と変更容易性を確保する。

**Tasks**

- `styles/Spacing.kv` に `#:set GAP_S/M/L` 等を定義する。
- `styles/Typography.kv` に H1/H2/Body 系の推奨スタイルを定義する。
- 代表スクリーンやコンポーネントで 1 箇所以上使用例を追加する。

**Acceptance Criteria**

- トークン定義が存在し、最低 1 画面で使用されている。
- トークン変更が全体に波及することを確認できる。

## 5. Standardize common components: Toolbar, Dialogs, Buttons in `components/`

**Background**

画面間の重複実装を削減し、変更の波及を容易にする。

**Tasks**

- `<AppToolbar@MDToolbar>` や `<ConfirmDialog@MDDialog>`、`<PrimaryButton@...>` 等の定義を追加する。
- 2〜3 画面で置き換え例を追加する。
- ガイドとして簡易コメントや README の断片を追記する。

**Acceptance Criteria**

- 共通化された定義があり、複数画面で利用されている。
- 新規画面が共通部品を再利用できる。

## 6. Create mixin/behavior for form validation and save-button enablement

**Background**

各画面でバラつく「必須入力が揃うまで保存無効」を共通化する。

**Tasks**

- Python 側に `FormValidationMixin` を作成し、値監視から `can_save()` を算出する。
- KV 側で `on_text` や選択変更に応じて `btn_save.disabled = not root.can_save()` のパターンを統一する。
- 代表画面に適用する。

**Acceptance Criteria**

- 代表画面で必須項目が揃うまで保存不可になる。
- ロジックが共通化され、他画面へ横展開可能になる。

## 7. Improve focus order, default focus, and keyboard shortcuts

**Background**

入力効率向上と使い勝手の改善を目的とする。

**Tasks**

- `on_pre_enter` で最初のフィールドへ `focus=True` を設定する。
- Tab 順を KV の並び順や `tab_width` で調整する。
- Enter で保存、Esc で戻る等のショートカットを追加する（Windows 運用に配慮）。

**Acceptance Criteria**

- 代表画面でキーボードだけでスムーズに入力から保存まで行える。
- フォーカスの初期位置が適切に設定されている。

## 8. Enforce i18n: centralize strings and detect missing keys in CI

**Background**

ラベルやボタン文言をすべて `strings.json` 経由にし、未翻訳や欠落を CI で検出する。

**Tasks**

- KV のハードコード文言を削減し、可能な限り `get_text("...")` を使用する。
- KV 内の `text:` からハードコードを検出するスクリプトを追加する（簡易で可）。
- `strings.json` のキー整合性をチェックする。

**Acceptance Criteria**

- 代表画面の文言が `strings.json` 経由で取得される。
- CI で未翻訳や欠落を検出できる。

## 9. Add minimal tests for screen creation and binding

**Background**

画面の import / 生成 / 基本バインドが壊れないことを担保する。

**Tasks**

- `pytest` で代表スクリーンの `build → add → remove` を試行するテストを追加する。
- `ids` の主要要素が存在することを検査する。
- 可能なら `can_save()` の真偽も 1 ケース検証する。

**Acceptance Criteria**

- CI でテストがグリーンになる。
- 代表画面の基本動作が担保される。

## 10. Update README and developer docs: flow, rules, troubleshooting

**Background**

新規参加者が迷わず追加・修正できるようルールを明文化する。

**Tasks**

- 画面追加手順（Python クラス + `screens/<ClassName>.kv` + ScreenManager 登録）を記載する。
- include 順・トークンの使い方・共通部品の呼び出し方を追記する。
- トラブルシュートとして KV パースエラー / クラス名不一致 / リソースパスの対処を書き加える。

**Acceptance Criteria**

- README や `docs/` から手順に沿って新画面が追加できる。
- 代表的なエラーの対処が明記されている。

