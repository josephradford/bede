# Health Auto Export (HAE) Setup

HAE is an iOS app that exports Apple Health data to `bede-data` via REST API automations.
Each data type is a **separate automation** that sends its own POST to `/ingest/health`.

Reference docs:
- REST API automations: https://help.healthyapps.dev/en/health-auto-export/automations/rest-api/
- Export format overview: https://help.healthyapps.dev/en/health-auto-export/export-format/
- Per-type format docs: https://help.healthyapps.dev/en/health-auto-export/export-format/{type}/

Payload schema from real captures: [hae-payload-format.md](hae-payload-format.md)

## Automations

All automations POST to `https://data.${DOMAIN}/ingest/health` with Bearer token auth (`INGEST_WRITE_TOKEN`).

| Automation | Data Type | Key Settings | Timeout |
|------------|-----------|-------------|---------|
| Health metrics | Health Metrics | All metrics, Summarize: on, Grouping: Minute | 1,800s |
| Health metrics (day grouping) | Health Metrics | All metrics, Summarize: on, Grouping: Day | 1,800s |
| Sleep metrics | Health Metrics | 2 selected (sleep_analysis + related), Summarize: off | 1,800s |
| Workouts | Workouts | Include Route Data: on, Include Workout Metrics: on, Grouping: Minutes | 60s |
| State of mind | State of Mind | — | 60s |
| Medications | Medications | — | 60s |

**Common settings across all automations:**
- Export Format: JSON
- Export Version: v2
- Date Range: **Default**
- Batch Requests: on (except State of Mind)
- Sync Cadence: every 30 minutes

## Date Range Setting (Critical)

The date range determines what data HAE includes in each export. **This has bitten us before.**

| Setting | What it actually means |
|---------|----------------------|
| **Default** | Full previous day + data up to the current date and time |
| Today | Current date up to the current time only |
| Yesterday | Full previous day only |
| Previous 7 Days | The 7 days **before** today (does NOT include today) |
| Since Last Sync | Everything since the last successful export |

**All automations must use "Default"** to ensure today's data is included. "Previous 7 Days" sounds like it covers today but it does not -- it excludes the current day entirely.

## iOS Version Requirements

| Data Type | Minimum iOS |
|-----------|------------|
| Health Metrics | Any |
| Workouts | Any |
| State of Mind | 18.0 |
| Medications | 26.0 |

If the device is on an older iOS version, the data type simply won't appear in exports.

## How Data Flows

```
iPhone Health App
    |
    v
HAE app (30-min cadence, background refresh)
    |  separate POST per data type
    v
https://data.${DOMAIN}/ingest/health
    |  Traefik (webhook-secure middleware)
    v
bede-data container (port 8001)
    |  parse_health_payload() -> _upsert_rows()
    v
SQLite (bede.db)
    |
    v
bede-data-mcp (MCP tools) -> bede-core (Claude)
```

Each POST contains `{"data": {"<type>": [...]}}` with exactly one data type per request (when Batch Requests is on). The parser handles all types in a single function, extracting whichever keys are present.

## Reliability Notes

HAE runs as a background iOS app with inherent limitations:

- **Phone must be unlocked** for Health data access -- exports won't fire while locked
- **Background App Refresh** must be enabled for HAE
- **Low Power Mode** may delay or skip scheduled exports
- **Charging + iPhone Mirroring** is the most reliable setup (iOS relaxes background restrictions)

If data appears stale, check the HAE Activity Logs on the phone before investigating the server.

## Troubleshooting

1. **No data for today**: Check the Date Range setting -- must be "Default" or "Since Last Sync"
2. **Missing data type entirely**: Check iOS version requirements; confirm the automation is Enabled
3. **Intermittent gaps**: Background refresh limitations; check HAE Activity Logs on phone
4. **Auth failures**: Compare Bearer token in HAE with `INGEST_WRITE_TOKEN` in server `.env`
5. **All data arriving but not stored**: Check `make logs-bede-data` for parser errors
