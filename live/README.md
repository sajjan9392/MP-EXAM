# live/ — Pariksha Sarthi online updates

App (v with live updates) checks `live/manifest.json` every few hours when online and downloads
any file whose hash changed. No new APK needed for these:

- `ca-index.json` — months list `{months:[{m,n,q}], updated}` (merged over the bundled one)
- `ca-YYYY-MM.json` — month's current-affairs entries (replaces the bundled month)
- `qpatch.json` — `{ver, upd:[full question objects], del:[ids]}`; `upd` adds/replaces by `id`
  (new CA questions, Doubt-Desk fixes). PYQ ids (P…) are never deleted.

Pushes that touch only `live/**` do NOT trigger the Android build (paths-ignore in android.yml).
Never put keystore / secrets here — this folder is public.
