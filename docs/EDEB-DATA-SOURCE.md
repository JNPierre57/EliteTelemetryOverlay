# EDEB data source — discovery status

**The real EDEB reader is not implemented or validated.** Initially no Shadow data was available. A user-supplied inspection report now confirms the database schema below; database rows and executable are still unavailable here. Production sender therefore exits with an explicit error before sending anything. This is a deliberate boundary, not a working EDEB integration. The demo exercises the rest of the system.

## What is verified

The [official EDEB page](https://www.panostrede.de/EDEB/) describes separate current-trip and overall-history data, an estimated total including Vista Genomics, and a native trip-reset command. Its download link names version 2.7.9.

The [official changelog](https://www.panostrede.de/EDEB/changelog.html) records historical changes to cartographic valuation and database compatibility. It does not document a usable schema or total-value query. Public documentation is insufficient to establish the persistence semantics of the current trip. Consulted 2026-09-06.

The data root was supplied by the owner; the subsequent Shadow report confirms `db\EDEB.db` beneath it:

```text
%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\
%LOCALAPPDATA%\Elite Dangerous Exploration Buddy\db\
```

| Required finding | Current evidence |
| --- | --- |
| Exact database engine | SQLite 3, confirmed by the Shadow diagnostic signature |
| Useful files | `db\EDEB.db`; observed `PRAGMA user_version = 279` |
| Start/reset marker | `StarSystem.IsTripHistory INTEGER NOT NULL DEFAULT 0` exists; actual reset behavior still unverified |
| Stored total versus recalculated total | Per-body `CartographicValue` and per-genus `VistaGenomicsValue` exist; no dedicated total table in reported schema |
| Table/field/query matching EDEB | Candidate sums documented below; row totals still need comparison to EDEB |
| EDEB version tested against real data | Report inspected with schema version 279; no production value read validated |

## Targeted value comparison after the first report

The observed schema contains `Body` (key: system + body), `Genus` (key: system + body + name), `StarSystem`, and `Ring`. `tests/fixtures/edeb-schema-279.json` retains only the table definitions from the report; it contains no user rows, travel history or displayed totals. The first report contains **schema only**, so the two totals supplied alongside it cannot yet validate any SQL sum.

The updated inspector now aggregates the existing EDEB value columns on its temporary copy. It does not recalculate bonus formulas. It reports three scopes: systems with `IsTripHistory = 1`, all systems, and systems with `IsTripHistory = 0`. For each scope it reports:

- Cartography: all bodies, and separately only `WasReadFromJournal = 1` bodies.
- Biology: all genera, and separately only `AnalysisComplete = 1` genera.
- The four combinations of these component sums, with differences against the displayed totals if supplied.
- NULL/invalid values, orphan row counts and trip-flag distribution to expose assumptions rather than silently hide inconsistencies.

Body and genus sums are **separate**. Joining bodies directly to multiple genera would multiply cartographic values. Stored total columns are used without adding their bonus component columns a second time. NULL values contribute zero for this diagnostic only and their counts are retained; the intended production semantics still need validation.

On Shadow, update with `git pull --ff-only`. Then supply the two **current** displayed totals as integer arguments, without spaces or separators:

```powershell
$trip = Read-Host 'Current Exploration Trip, digits only'
$history = Read-Host 'Entire Exploration History, digits only'
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\inspect-edeb.ps1 -TripValue $trip -HistoryValue $history -OutputPath .\reports\edeb-values.json
```

Keep EDEB/game activity still while recording the displayed totals and running the comparison. If the values have changed since the earlier report, use the newer values. Send `reports/edeb-values.json` after local review. No `-IncludeSamples` is needed: the new section `edeb_value_comparison` contains aggregate numbers, not names or coordinates.

`matching_pairs` lists candidate filters that reproduce **both** the trip-flag-1 total and the all-systems history total. An empty list means no exact match; several entries mean the sample does not distinguish the filters. Even one match is evidence for one snapshot, not proof of the underlying reset or scan semantics. The production sender stays disabled while those semantics are unverified.

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
