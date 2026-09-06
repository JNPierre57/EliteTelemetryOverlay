# Validation

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
node tests/format.test.cjs
sh -n scripts/install-mac.sh scripts/start-mac.sh
```

Python tests cover strict integer/source/time validation, hundreds of billions and the exact JS maximum, authenticated HTTP updates, bad token, decreases/zero, duplicate update, persistence/restart, corrupt state, disk write failure, real loopback sender HTTP, static assets, secret omission, retry/backoff/latest value, forbidden network addresses, unknown database formats, and synthetic SQLite inspection without changes to source files. The schema-only fixture now comes from the Shadow report; all inserted row values remain synthetic.

The JavaScript test covers credit grouping, cosmetic decimals, separator literals, invalid values and safe-integer boundaries. Node is a development-only prerequisite. The workflow in `.github/workflows/tests.yml` defines Windows/macOS/Linux runs; adding a workflow does not mean those remote jobs have already executed.

## Manual integration checklist

1. Run receiver and sender with `--demo`; open OBS before starting sender.
2. Check direct initial display, increases with independent reels, unchanged total without animation, decreases and zero without reverse animation.
3. Start the demo sender before the receiver; observe backoff then recovery.
4. Restart the receiver; observe persisted value. Reload OBS; no animation from zero.
5. Reduce Browser Source width; verify fit, transparency over actual stream video, and readability.
6. Enable reduced motion; verify immediate updates. Test rapid successive updates during animation.
7. Repeat on Shadow → Mac Tailscale with the shared token, then compare the real EDEB reader to the displayed current trip.

Not validated by synthetic tests: production reading of EDEB values, trip boundary, total calculation, real lock behavior, OBS embedded-browser behavior, Windows installation on Shadow, or the actual tailnet/firewall. These need the user's environment. See EDEB-DATA-SOURCE.md before claiming production readiness.

## Executed in this workspace (2026-09-06)

- 15 Python unittest cases passed on the local Mac, including a live WAL fixture whose source database/WAL/SHM byte hashes remain unchanged.
- Node credit-formatting tests passed; JavaScript, shell and PowerShell syntax checked.
- Mac installer created a virtual environment and local configuration; the then-disabled sender exited with its intended error (superseded by the real reader below).
- Full localhost demo sender/receiver sequence ran. In-app browser visibly showed 12 847 563 420 Cr, then 0 Cr with DEMO; computed background alpha was zero. This is not an OBS integration test.
- Local secret and cache excluded from Git; repository content checked without printing the secret.

## Follow-up after the Shadow schema report

20 Python tests pass locally, including five new cases using the reported table definitions with synthetic rows: independent cartography/biology sums (multiple genera per body), matching both displayed totals, explicit mismatch, invalid/orphan rows, missing schema columns, and a synthetic trip-flag reset without changing the original file. This flag test does not establish what EDEB itself does on reset. Aggregate reports are checked to omit synthetic system/genus names. The JavaScript tests and PowerShell parser also pass.

## Reader implementation after exact aggregate matches

30 Python tests pass locally. Ten new source tests exercise the observed schema with synthetic rows: existing trip versus lifetime, first read without a baseline, increases, trip-flag reset, new selection, unknown schema/version, filter ambiguity, invalid/NULL/fractional values, orphan rows, invalid flags, WAL reads without changes to source hashes, active journals, changing bytes and sender recovery without publishing stale pending values or zero. JavaScript tests still pass.

The user's second report reproduces both displayed totals exactly with stored-value aggregates. The reader's new process has not yet been executed on Shadow, and native EDEB reset/scan transitions, live OBS and Tailscale still require real-environment acceptance. No personal totals or raw reports are stored as test fixtures.

The Mac receiver LaunchAgent was installed and loaded locally during the 2026-09-06 session. `launchctl print gui/501/local.EliteTelemetryOverlay.receiver` reported `state = running`; `/health` returned 200 and listeners were present on loopback and `100.90.75.102:8765`. The Windows scheduled task still needs to be installed from Shadow with `scripts/install-shadow-task.ps1`.

## Live stream and animation follow-up

The user confirmed the real source command, Shadow-to-Mac delivery, display in OBS and subsequent live value changes. They reported no animation and updates after system changes. The Mac in-app browser was observed reporting reduced motion; this is evidence for the likely animation cause, not a direct measurement inside OBS. Added explicit `motion=always`/`never` overrides and a page-local preview. Thirty Python tests and the JS formatting/animation-policy assertions pass; the in-app preview was captured with nonzero vertical reel transforms while reduced motion was enabled. Actual EDEB write timing and the override inside OBS remain to be confirmed by the user.
