# EDEB data source

**A guarded reader is now implemented.** Two user-supplied Shadow reports established the schema and showed that the candidate sums reproduce both the displayed Current Exploration Trip and Entire Exploration History exactly. This is a real-data comparison for one observed state, not a claim that every EDEB scan/reset scenario has been validated.

## Observed evidence

| Finding | Evidence |
| --- | --- |
| Engine | SQLite 3, file header identified on Shadow |
| File | `%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\db\EDEB.db` |
| Database version | `PRAGMA user_version = 279` (target application: EDEB 2.7.9) |
| Tables | `StarSystem`, `Body`, `Genus`, `Ring` |
| Current-trip selection | `StarSystem.IsTripHistory = 1` selects data whose sums match the displayed current trip |
| Cartography | `Body.CartographicValue`, related by `Body.StarSystemId = StarSystem.Id` |
| Exobiology | `Genus.VistaGenomicsValue`, related by `Genus.StarSystemId = StarSystem.Id` |
| Overall history | The same component sums across all systems match the displayed entire history |
| Total storage | No dedicated total table appears in the schema; the reader sums stored component values |
| Actual EDEB reset implementation | Not observed; do not reset the user's expedition merely to test it |

Schema fingerprint observed:

```text
baab7ca412995e8f91c36f2baa8b51b50206e1ff8368335758ad0cc450e4fdf5
```

The report showed no NULL/invalid monetary values or orphan rows. All-body versus journal-only cartography totals were equal. All-genus versus completed-only biology totals were also equal, including across overall history. Incomplete biology rows and non-journal bodies contributed zero in this sample. Hence **all four candidate filter combinations matched**: these reports cannot prove which optional filters EDEB itself applies.

`tests/fixtures/edeb-schema-279.json` contains only the observed table definitions. Test rows are invented. Private reports and the user's numeric totals are not committed.

## Implemented formula and safeguards

`telemetry/source.py` uses the equivalent of these two separate queries and adds their results:

```sql
SELECT COALESCE(SUM(b.CartographicValue), 0)
FROM Body b
WHERE EXISTS (
    SELECT 1 FROM StarSystem s
    WHERE s.Id = b.StarSystemId AND s.IsTripHistory = 1
);

SELECT COALESCE(SUM(g.VistaGenomicsValue), 0)
FROM Genus g
WHERE EXISTS (
    SELECT 1 FROM StarSystem s
    WHERE s.Id = g.StarSystemId AND s.IsTripHistory = 1
);
```

No direct Body-to-Genus join: multiple genera on a body must not multiply its cartographic value. No maximum-value columns, extra system rewards or separate bonus columns are added. The reader uses the actual value columns already calculated by EDEB. It reads the existing expedition in full at first startup, without subtracting an installation-time baseline.

To avoid silently resolving the filter ambiguity, the reader refuses a reading if any selected body has nonzero value without `WasReadFromJournal = 1`, or if any selected genus has nonzero value without `AnalysisComplete = 1`. Under the observed conditions, filtered and unfiltered formulas agree. A future disagreement produces `filters no longer agree`; run the comparison diagnostic and investigate instead of choosing a filter arbitrarily.

The reader checks the exact observed schema fingerprint and database version, SQLite `quick_check`, integer/nonnegative selected values, valid 0/1 trip flags and orphan rows. NULL monetary values in the current trip are refused (the diagnostic merely counted them and treated them as zero). New schema/version combinations require renewed verification and an entry in `SUPPORTED_SCHEMAS`; there is no silent fallback after an EDEB upgrade.

## Non-destructive production reads

`telemetry/sqlite_snapshot.py` opens original DB/WAL files only as binary read streams. It does **not** open the original database using SQLite, even in `mode=ro`, because WAL shared-memory sidecars can otherwise be created or changed by SQLite. The original database is never migrated, checkpointed or repaired.

For each read:

1. Inspect database/WAL/rollback-journal sizes and modification times. Refuse a missing DB, a nonempty rollback journal or a total above 512 MiB.
2. Copy database and existing WAL to a private temporary directory while hashing their bytes. Do not copy SHM; SQLite can rebuild it only in the temporary directory.
3. Compare original metadata, re-read/hash original bytes and compare metadata again. Refuse any change, with a two-second cooperative copy deadline.
4. Open only the private copy in SQLite, set `query_only`, validate schema/integrity and sum values with a two-second SQL deadline.
5. Close the SQLite connection and delete the temporary directory.

This double-checked raw copy is **not an application-level atomic snapshot guarantee**. It detects observed byte/metadata changes and malformed copies, but cannot prove semantic consistency across separate EDEB transactions. It may refuse readings during intensive activity and recover once a stable copy is available. The deadlines are checked between file blocks/SQL operations, not a hard interruption of an OS disk read. No persistent source locks are taken. Large databases can impose I/O load at the default 0.5-second interval; increase `read_interval` if necessary.

A failed read sends nothing, retains the last receiver value and retries after two seconds. Warnings are limited to one every 30 seconds during a continuous failure; recovery is logged. An old cached value is not proof that EDEB is currently running.

## First real-reader check on Shadow

Leave EDEB open with the correct commander, pause exploration activity briefly, then run from the updated repository:

```powershell
git pull --ff-only
py -3 -m telemetry.source
```

No token, receiver, Tailscale, virtual environment or config is required for this one-shot check beyond Python 3.11+. It prints the current trip and its cartographic/biological components and exits. Compare to EDEB. A custom database path can be checked with:

```powershell
py -3 -m telemetry.source --database 'D:\Custom EDEB\db\EDEB.db'
```

For the continuous sender, optional `edeb_db_path` in `config.local.json` overrides the default. Leave it empty for automatic `%LOCALAPPDATA%` detection; existing configurations without the key remain valid. See [INSTALL.md](INSTALL.md) for token/network setup.

## Diagnostic and value comparison

The original diagnostic remains available, using disposable copies. It inventories file signatures and schema; `-IncludeSamples` is optional and may include private data. For ordinary aggregate comparison no samples are needed:

```powershell
$trip = Read-Host 'Current Exploration Trip, digits only'
$history = Read-Host 'Entire Exploration History, digits only'
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\inspect-edeb.ps1 -TripValue $trip -HistoryValue $history -OutputPath .\reports\edeb-values.json
```

Use values displayed at the time of inspection. Review the resulting report locally before sharing it. Aggregate comparisons do not export names or coordinates. The inspector shows trip/all/non-trip scopes, four candidate combinations, NULL/invalid counts, orphans and differences; `matching_pairs` is evidence for that snapshot only.

The general inspector uses a simpler metadata-stable copy of DB/WAL/SHM/journal files, SQL query-only mode, a three-second SQL deadline, a 512 MiB snapshot limit and a 2,000-file inventory limit. Its copies likewise are not a guaranteed atomic snapshot. Unknown formats are reported as unknown. Neither tool ever writes to original EDEB data.

## Remaining real-environment acceptance checks

- Run the new reader on Shadow and compare its initial result to EDEB.
- Compare again after a normal cartographic scan, DSS mapping, completed exobiology and a system revisit. Watch for temporary read refusals while EDEB updates.
- Confirm network delivery and OBS behavior on the actual machines.
- When the owner actually starts a new expedition, verify the native EDEB reset and resulting zero/lower value. Do not sacrifice the current trip for development. Synthetic tests already verify behavior when trip flags change; this does not establish the implementation of EDEB's reset.
- Multi-commander semantics have not been established: run one EDEB/commander/sender at a time and compare totals after changing commander.

## Public references and journal fallback

The [official EDEB page](https://www.panostrede.de/EDEB/) describes separate current-trip/overall-history values, Vista Genomics inclusion and the native trip-reset command. The [changelog](https://www.panostrede.de/EDEB/changelog.html) records database and valuation changes. Consulted 2026-09-06. Neither documents the exact SQL; the local schema and aggregate reports are the evidence for this adapter.

Journals typically live at `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\Journal.*.log`. No journal fallback is implemented: using only post-installation events would lose the ongoing expedition, and a faithful reconstruction would require the actual EDEB boundary and matching bonus rules. Stored EDEB values are the preferred source.
