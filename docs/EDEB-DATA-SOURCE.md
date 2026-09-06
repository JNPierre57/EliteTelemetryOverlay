# EDEB data source — discovery status

**The real EDEB reader is not implemented or validated.** No Shadow files or EDEB executable were accessible in this workspace on 2026-09-06. The repository initially contained no files. Production sender therefore exits with an explicit error before sending anything. This is a deliberate boundary, not a working EDEB integration. The demo exercises the rest of the system.

## What is verified

The [official EDEB page](https://www.panostrede.de/EDEB/) describes separate current-trip and overall-history data, an estimated total including Vista Genomics, and a native trip-reset command. Its download link names version 2.7.9.

The [official changelog](https://www.panostrede.de/EDEB/changelog.html) records historical changes to cartographic valuation and database compatibility. It does not document a usable schema or total-value query. Public documentation is insufficient to establish the persistence semantics of the current trip. Consulted 2026-09-06.

The paths below were supplied by the project owner, not observed on this Mac:

```text
%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\
%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\db\
```

| Required finding | Current evidence |
| --- | --- |
| Exact database engine | Unknown; do not assume SQLite from the `.db` directory |
| Useful files | Unknown; diagnostic inventories relative names and signatures |
| Start/reset marker | Unknown; no installation-time baseline is created |
| Stored total versus recalculated total | Unknown |
| Table/field/query matching EDEB | Unknown; no invented SQL adapter shipped |
| EDEB version tested against real data | None; target requested: 2.7.9 |

## Run discovery on Shadow

Leave EDEB operating normally. Do **not** reset your two-week expedition for a test. Install Python 3.11+ with the Windows `py` launcher, then from this repository:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\inspect-edeb.ps1
Get-Content .\reports\edeb-inspection.json
```

Record, at the same time, the exact **Current Exploration Trip** total shown in EDEB and, if displayed separately, cartographic and biological components. Also record the EDEB version and time. Repeat after a known in-game scan with a different report filename:

```powershell
.\tools\inspect-edeb.ps1 -OutputPath .\reports\edeb-after-scan.json
```

The report contains relative file names, sizes, signature identification, and SQLite schema/fingerprint where recognized. It does not read row contents by default. If the schema report alone is insufficient, an explicit opt-in collects up to three rows per table from private copies:

```powershell
.\tools\inspect-edeb.ps1 -IncludeSamples -OutputPath .\reports\edeb-private-samples.json
```

These samples may contain commander names, travel history or other private data. Review locally and share only relevant redacted portions; reports are gitignored. Three sample rows cannot establish a complete expedition value.

## Non-destructive behavior and limitations

The diagnostic opens original files only as byte streams for reading. It never opens the original with a database engine, never migrates it, and never invokes EDEB. For recognized SQLite files it copies the database and any WAL, SHM and rollback-journal companions into an automatically deleted temporary directory. It compares file sizes and modification times before/after copying and refuses to inspect a changing copy. It never changes permissions on original files.

SQLite runs only against the copies, with `query_only`, a short busy timeout and a three-second SQL execution deadline. Snapshots above 512 MiB are refused; inventory stops at 2,000 files. No persistent source locks are held. Copying large files can still cause short disk I/O load. A size/mtime check is **not** a transaction-consistent snapshot guarantee. Inconclusive or locked copies require a later retry; if necessary close EDEB normally, inspect, then reopen it. A hot rollback journal may prevent inspection rather than produce a reliable report. Unknown formats are reported as unknown, never decoded speculatively.

## Completing the production adapter

1. Establish the engine and file set from the report; investigate unknown signatures using format-specific tooling on copies.
2. Identify the current-trip boundary and the exact EDEB total or calculation, distinct from overall history. Schema names alone are insufficient evidence.
3. Compare against the existing expedition before any reset, then after mapping, completed exobiology and revisiting a system. Verify the commander's identity if the store supports multiple commanders.
4. Only when the owner actually starts a new expedition, compare before/after the native EDEB reset. Never reset the current expedition for development.
5. Implement `telemetry/source.py` with read-only or consistent snapshot access appropriate to the verified engine, bounded lock/retry behavior, version/schema checks and explicit errors on incompatibility. Add sanitized representative fixtures, including reset and schema mismatch cases.
6. Document files, fields, boundary, equations, rounding, evidence and observed version here. A matching number on one sample alone does not validate the adapter.

The existing sender already sends the first successful read in full, without subtracting a baseline. No artificial “new system” bonus is applied anywhere.

## Journals fallback

Typical journals live at `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\Journal.*.log`. They have not been available for inspection here. A faithful fallback needs complete historical journals, the actual EDEB trip boundary, the same valuation/bonus rules, and comparison to the displayed current trip. Reconstructing only post-installation events would lose the ongoing expedition. Therefore no journal approximation is labelled as the EDEB total or used as a silent fallback.
