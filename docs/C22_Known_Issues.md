# C22. Known Issues
This register lists active and historical issues affecting Duel Performance Logger builds. Update it alongside every release note.

## Table of Contents
- [Highlights](#highlights)
- [Tracking Method](#tracking)
- [Update Procedure](#update-procedure)
- [Checklist](#known-issues-checklist)

## <a id="highlights"></a>Highlights
| ID | Version | Description | Workaround | Status |
|----|---------|-------------|------------|--------|
| KI-001 | DPL.1.4.0 | Buttons appear compressed on high-DPI menus | Adjust Windows scaling below 150% until the next patch | Open |
| KI-002 | DPL.1.4.0 | Firewall prompt appears after running Updater | Instruct users to accept the first-run firewall dialog | Monitoring |
| KI-003 | DPL.1.3.x | DSL migration logs are excessively verbose | Increase `app.log` rotation retention | Resolved in DPL.1.4.0 |
| KI-MIG-001 | Legacy builds | Migrating `matches.deck_name` to `deck_id` fails when duplicate deck names exist | Deduplicate deck names before running migration 001 or map manually via `decks` table IDs | Monitoring |

## <a id="tracking"></a>Tracking Method
- Manage items in Jira project `DPLBUG` with the `Known Issue` label.
- Record the fix version in the "Resolved in" column when closing items.

### Migration Advisory
- When applying migration `001_deck_id_fk.sql`, verify that every `deck_name` in `matches` resolves to a unique `decks.id`. Duplicate deck names or orphaned records will abort the transaction with `deck_id resolution failed`.
- Back up the original database before executing the migration and keep the dump until deck mappings are verified. 手作業でのリカバリを可能にします。

## <a id="update-procedure"></a>Update Procedure
1. Assign a new identifier (`KI-###`) for each issue.
2. Choose a status from `Open`, `Monitoring`, or `Resolved`.
3. After a fix ships, update the workaround and set the status to `Resolved`.

## <a id="known-issues-checklist"></a>Checklist
- [ ] Review the table before every release.
- [ ] Document the fix version for resolved issues.
- [ ] Ensure workarounds are actionable for support teams.

**Last Updated:** 2025-10-12
