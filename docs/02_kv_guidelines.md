# 02. Web UI Layout Guidelines / Web UI レイアウト指針

This guide defines the conventions for HTML/CSS/JavaScript assets that power the
Eel-based interface of Duel Performance Logger.

## File Organization / ファイル構成
- HTML entry points live in `resource/web/` (e.g., `index.html`).
- Static assets reside under `resource/web/static/` and are grouped by type
  (`css/`, `js/`, `img/`).
- Python-side bridge helpers belong to `app/function/web/` and expose
  functionality through `app/main.py`.

## Naming Conventions / 命名規則
| Element | Convention | Example |
|---------|------------|---------|
| CSS classes | BEM-style (`block__element--modifier`) | `app-header__status` |
| JavaScript modules | `kebab-case.js` | `app.js` |
| Data attributes | `data-*` kebab case | `data-visible` |
| Translation keys | `strings.<context>.<key>` | `strings.menu.start` |

## Styling Rules / スタイリングルール
- Declare palette tokens in `:root` CSS variables and reuse throughout the UI.
- Prefer modern layout primitives (CSS Grid / Flexbox) over manual pixel math.
- Keep responsive breakpoints at 720px and 1280px to match desktop layouts.
- Register custom fonts through CSS `@font-face`; do not manipulate fonts in
  Python.

## Scripting & Data Flow / スクリプトとデータフロー
1. All calls from JavaScript to Python go through `eel.<function>()`. Wrap the
   promise with `await` and handle errors with `try/await/catch`.
2. Python sends notifications via `app/function/core/ui_notify.notify`; the
   front-end must expose `show_notification` through `eel.expose`.
3. Keep DOM mutations in dedicated render helpers (e.g., `renderMatches`) and
   avoid inline `onclick` attributes.
4. Store transient UI state in module-scoped variables; persistent data remains
   in SQLite and is served via `fetch_snapshot`.

## Accessibility / アクセシビリティ
- Provide `aria-live` regions for real-time updates (e.g., toast component).
- Ensure color contrast meets WCAG AA (4.5:1) using the shared palette.
- Maintain keyboard focus order with semantic HTML elements and `tabindex` only
  when necessary.

## Testing / テスト
- Lint JavaScript with `npx eslint --ext .js resource/web/static/js`.
- Format HTML/CSS/JS using `npx prettier --check resource/web`.
- Use Playwright smoke tests (planned) to assert critical flows once automated
  coverage is available.

## Checklist / チェックリスト
- [ ] New assets placed under the correct `static/` subfolder.
- [ ] CSS variables reused instead of hard-coded colors.
- [ ] Eel bridge function exposed in both Python and JavaScript.
- [ ] Lint/format tools executed before submission.

**Last Updated:** 2025-11-05
