# Data Sources

Reference for all data ingested by bede-data: where it comes from, which devices it covers, and how often it arrives.

## Health Data (iPhone → HAE → bede-data)

Source: Apple Health Auto Export (HAE) iOS app. Six separate automations, all firing every 30 minutes via background refresh. Endpoint: `POST /ingest/health`.

| Source | Data | Notes |
|--------|------|-------|
| health_metrics | Steps, active energy, HRV, resting HR, etc. | Minute grouping |
| health_metrics_day | Daily aggregates | Day grouping |
| sleep | Sleep analysis + related metrics | Summarize off |
| workouts | Type, duration, calories, route data | Minute grouping |
| state_of_mind | Mood/wellbeing entries | No batching |
| medications | Medication log | iOS 26.0+ required |

All automations fire regardless of whether there's new data (Date Range: Default = full previous day + today). A stale source reliably means the pipeline is broken.

Expected freshness interval: **30 minutes** (all sources).

Setup details: [hae-setup.md](hae-setup.md)

## Usage Data (Mac → usage-collect.sh → bede-data)

Source: `usage-collect.sh` launchd agent on the Mac. Runs 13 times daily (8am–11pm, irregular intervals, worst-case gap 3h). Endpoint: `POST /ingest/usage`.

| Source | File | Devices | Underlying DB | Always present? |
|--------|------|---------|---------------|-----------------|
| screen_time_mac | `screentime.csv` | Mac only | knowledgeC.db | Yes |
| screen_time_iphone | `iphone-screentime.csv` | iPhone only | Biome App.InFocus SEGB | Yes |
| safari_history | `safari-pages.csv` | Mac + iPhone | History.db (iCloud sync) | Yes |
| youtube_history | `youtube.csv` | Mac + iPhone | History.db (subset of Safari) | No — only if YouTube was visited |
| podcasts | `podcasts.csv` | Mac + iPhone | MTLibrary.sqlite (iCloud sync) | No — only if podcasts were played |
| claude_sessions | `claude-sessions.md` | Mac only | Claude Code projects dir | No — only if Claude was used |
| bede_sessions | `bede-sessions.json` | Mac only | Bede conversation logs | No — only if Bede was used |

Expected freshness interval: **3 hours** (worst-case gap between scheduled runs).

### iCloud sync pattern

Safari, YouTube, and Podcasts include iPhone activity because their underlying macOS databases sync from iPhone via iCloud:

- **History.db** — Safari's SQLite database. iPhone visits appear with `origin = 1`. Sync is near-realtime (forced via `SafariHistoryServiceAgent`).
- **MTLibrary.sqlite** — Apple Podcasts database. iPhone-played episodes sync via iCloud. Reliable same-day sync.

Screen time does NOT benefit from this pattern — it requires two separate collection pipelines because the Mac database (knowledgeC.db) and iPhone data (Biome SEGB files) are completely independent sources.

### "Always present" distinction

Sources marked "Yes" are always collected regardless of user activity — if the file is missing from an upload, the pipeline is broken. Sources marked "No" are only included when there's activity to report — absence means no activity, not a failure.

## Location Data (iPhone → OwnTracks → owntracks-recorder)

Source: OwnTracks iOS app publishing to the owntracks-recorder container. Not stored in bede-data's SQLite — queried live via HTTP API (`/api/0/last`).

Expected freshness: **1 hour** (OwnTracks publishes on significant location changes and periodic pings).

The `tst` field in the recorder's `last` endpoint response is the authoritative freshness timestamp.

## Music Listens (not yet implemented)

Planned approach: Last.fm scrobbling API. See `dotfiles/docs/apple-music-play-history.md` for research and decision rationale. Will cover Mac + iPhone via Last.fm's own device-agnostic collection.
