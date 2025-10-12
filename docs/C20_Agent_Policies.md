# C20. Agent Policies
This guide standardises how automation agents and contributors manage documentation under `/docs`.

## Table of Contents
- [Writing Style](#writing-style)
- [Content Expectations](#content-expectations)
- [Change Management](#change-management)
- [Metadata](#metadata)

## <a id="writing-style"></a>Writing Style
- Start every document with a level-1 heading.
- Use ordered lists for step-by-step procedures and unordered lists for reference points.
- Wrap executables, directories, and configuration keys in backticks.
- Represent product versions with the `DPL.<MAJOR>.<MINOR>.<PATCH>` scheme.
- When localisation is required, present Japanese first followed by the English gloss in parentheses.

## <a id="content-expectations"></a>Content Expectations
- Keep PyInstaller one-folder packaging, `Updater.exe`, and migration policies aligned across manuals.
- Include tables for environment matrices, error mappings, and release channels.
- Cross-link related documents using the new relative paths (e.g., [`B10_Release_Management.md`](B10_Release_Management.md)).
- Reference Codex workflow templates (`C24`–`C26`) when documenting automation routines.

## <a id="change-management"></a>Change Management
- Update the "Last Updated" metadata at the bottom of every edited document.
- Any procedural document must provide a "Checklist" section summarising required actions.
- Migrate legacy content into the new structure instead of deleting sections outright.

## <a id="metadata"></a>Metadata
- **Maintainer:** DPL Documentation Team
- **Last Updated:** 2025-10-12
