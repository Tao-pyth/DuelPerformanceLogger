# Documentation Guidelines (Duel Performance Logger)

This file defines documentation rules for everything under `/docs`.

---

## Writing Style

- Use Markdown with level-1 headings at the top of each document.
- Prefer ordered lists for sequential procedures and unordered lists for reference information.
- When referencing executables, directories, or config keys, wrap them in backticks.
- Mention version identifiers using the `DPL.<MAJOR>.<MINOR>.<PATCH>` scheme.
- Localized terms should follow Japanese first, English in parentheses when clarification is required (例: "更新 (update)").

## Content Expectations

- Keep PyInstaller one-folder packaging, `Updater.exe`, and migration policies consistent across documents.
- Include tables when documenting environment matrices, error mappings, or release channels.
- Cross-link related documents using relative Markdown links (e.g., `[Release Guide](08_release.md)`).
- Reference Codex workflow templates in `/docs/codex_templates/` when describing automation tasks.

## Change Management

- Update the "Last Updated" metadata at the bottom of each document you edit.
- Documents describing procedures must include a "Checklist" section summarizing actions.
- Do not remove legacy sections without migrating the information into the new structure.

**Maintainer:** DPL Documentation Team
**Last Updated:** 2025-10-12
