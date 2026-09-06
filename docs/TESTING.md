# Validation

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
node tests/format.test.cjs
sh -n scripts/install-mac.sh scripts/start-mac.sh
```

Python tests cover strict integer/source/time validation, hundreds of billions and the exact JS maximum, authenticated HTTP updates, bad token, decreases/zero, duplicate update, persistence/restart, corrupt state, disk write failure, real loopback sender HTTP, static assets, secret omission, retry/backoff/latest value, forbidden network addresses, unknown database formats, and synthetic SQLite inspection without changes to source files. No synthetic fixture is presented as an EDEB schema.

The JavaScript test covers credit grouping, cosmetic decimals, separator literals, invalid values and safe-integer boundaries. Node is a development-only prerequisite. The workflow in `.github/workflows/tests.yml` defines Windows/macOS/Linux runs; adding a workflow does not mean those remote jobs have already executed.

## Manual integration checklist

1. Run receiver and sender with `--demo`; open OBS before starting sender.
2. Check direct initial display, increases with independent reels, unchanged total without animation, decreases and zero without reverse animation.
3. Start the demo sender before the receiver; observe backoff then recovery.
4. Restart the receiver; observe persisted value. Reload OBS; no animation from zero.
5. Reduce Browser Source width; verify fit, transparency over actual stream video, and readability.
6. Enable reduced motion; verify immediate updates. Test rapid successive updates during animation.
7. Repeat on Shadow → Mac Tailscale with the shared token, then validate the real EDEB adapter when implemented.

Not validated by synthetic tests: exact EDEB 2.7.9 file format, trip boundary, total calculation, real lock behavior, OBS embedded-browser behavior, Windows installation on Shadow, or the actual tailnet/firewall. These need the user's environment. See EDEB-DATA-SOURCE.md before claiming production readiness.

## Executed in this workspace (2026-09-06)

- 15 Python unittest cases passed on the local Mac, including a live WAL fixture whose source database/WAL/SHM byte hashes remain unchanged.
- Node credit-formatting tests passed; JavaScript, shell and PowerShell syntax checked.
- Mac installer created a virtual environment and local configuration; normal sender exited with the intended unverified-source error.
- Full localhost demo sender/receiver sequence ran. In-app browser visibly showed 12 847 563 420 Cr, then 0 Cr with DEMO; computed background alpha was zero. This is not an OBS integration test.
- Local secret and cache excluded from Git; repository content checked without printing the secret.
