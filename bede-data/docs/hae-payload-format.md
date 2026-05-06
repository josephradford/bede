# Health Auto Export (HAE) Payload Format

Captured from real HAE payloads on 2026-05-05. Each export type arrives as a separate POST to `/ingest/health`.

For automation setup, date range gotchas, and troubleshooting: [hae-setup.md](hae-setup.md)

Reference docs: https://help.healthyapps.dev/en/health-auto-export/export-format/

## Workouts

```json
{
  "data": {
    "workouts": [
      {
        "id": "1C78329D-E5D1-4F1D-8CF5-72AFEDACFF5B",
        "name": "Hiking",
        "start": "2026-05-05 14:40:52 +1000",
        "end": "2026-05-05 16:11:06 +1000",
        "duration": 4528.114738106728,

        "activeEnergyBurned": {"qty": 2197.07, "units": "kJ"},
        "activeEnergy": [{"date": "...", "qty": 17.83, "source": "...", "units": "kJ"}, "...time-series..."],

        "heartRate": {"max": {"units": "bpm", "qty": 159}, "avg": {"qty": 127.7, "units": "bpm"}, "min": {"qty": 84, "units": "bpm"}},
        "avgHeartRate": {"units": "bpm", "qty": 127.7},
        "maxHeartRate": {"units": "bpm", "qty": 159},
        "heartRateData": [{"date": "...", "Min": 90, "Avg": 96.9, "Max": 104, "source": "...", "units": "bpm"}, "..."],

        "distance": {"qty": 6.71, "units": "km"},
        "speed": {"units": "km/hr", "qty": 5.33},
        "elevationUp": {"qty": 151.7, "units": "m"},
        "stepCadence": {"units": "count/min", "qty": 91.79},
        "stepCount": [{"units": "steps", "source": "...", "date": "...", "qty": 38.5}, "...time-series..."],

        "temperature": {"qty": 23.59, "units": "degC"},
        "humidity": {"qty": 35, "units": "%"},
        "intensity": {"units": "kcal/hr·kg", "qty": 6.02},
        "route": [{"latitude": -33.79, "longitude": 151.00, "altitude": 26.03, "speed": 0.42, "course": 49.08, "timestamp": "...", "horizontalAccuracy": 6.42, "verticalAccuracy": 1.34, "speedAccuracy": 1.52, "courseAccuracy": 205.27}, "..."],
        "metadata": {}
      }
    ]
  }
}
```

### Key distinctions

| Field | Type | Description |
|-------|------|-------------|
| `activeEnergyBurned` | `{qty, units}` | **Total** active energy for the workout |
| `activeEnergy` | `[{date, qty, ...}]` | **Time-series** per-minute energy data |
| `duration` | `float` | Duration in **seconds** |
| `heartRate` | `{min, avg, max}` | Summary object (each sub-field is `{qty, units}`) |
| `avgHeartRate` / `maxHeartRate` | `{qty, units}` | Redundant top-level summary fields |
| `heartRateData` | `[{date, Min, Avg, Max, ...}]` | Time-series heart rate samples |
| `route` | `[{latitude, longitude, ...}]` | GPS track points |

All quantity fields use `{qty, units}` format. Time-series arrays contain per-interval snapshots.

## State of Mind

```json
{
  "data": {
    "stateOfMind": [
      {
        "id": "4E6EB438-FE4B-47AC-BB60-06228FC9E293",
        "start": "2026-05-05T02:35:56Z",
        "end": "2026-05-05T02:35:56Z",
        "kind": "momentary_emotion",
        "valence": -0.8289922199235115,
        "valenceClassification": "very_unpleasant",
        "labels": ["anxious", "overwhelmed"],
        "associations": ["family", "work"]
      }
    ]
  }
}
```

### Notes

- **Timestamps** are ISO8601 (unlike other HAE types which use `YYYY-MM-DD HH:MM:SS +HHMM`)
- `kind`: `"momentary_emotion"` or `"daily_mood"`
- `valence`: float from -1.0 (very unpleasant) to 1.0 (very pleasant)
- `valenceClassification`: string — `"very_unpleasant"`, `"unpleasant"`, `"slightly_unpleasant"`, `"neutral"`, `"slightly_pleasant"`, `"pleasant"`, `"very_pleasant"`
- `labels` and `associations` can be empty arrays `[]`
- No `context` field exists (despite some documentation suggesting it)

## Medications

```json
{
  "data": {
    "medications": [
      {
        "displayText": "Desvenlafaxine",
        "start": "2026-04-29 06:57:56 +1000",
        "end": "2026-04-29 06:57:56 +1000",
        "scheduledDate": "2026-04-29 07:00:00 +1000",
        "scheduledDosage": 1,
        "dosage": 1,
        "units": "count",
        "form": null,
        "status": "Taken",
        "isArchived": false,
        "codings": []
      }
    ]
  }
}
```

### Notes

- `units` is the dosage unit (e.g. `"count"`). The docs mention `form` (Tablet, Capsule) but it was not present in real payloads.
- `status`: `"Taken"`, `"Skipped"`, `"Snoozed"`, `"Not Logged"`, etc.
- `scheduledDate` is the planned intake time; `start` is the actual time
- `isArchived`: if true, the medication is no longer tracked
- HAE sends one payload per date range, with multiple medication entries per payload

## Health Metrics

```json
{
  "data": {
    "metrics": [
      {
        "name": "heart_rate",
        "units": "count/min",
        "data": [
          {"date": "2026-05-04 00:00:00 +1000", "Avg": 72.83, "Min": 54, "Max": 126, "source": "Apple Watch"}
        ]
      },
      {
        "name": "active_energy",
        "units": "kJ",
        "data": [
          {"date": "2026-05-04 00:00:00 +1000", "qty": 2152.36, "source": "Apple Watch"}
        ]
      }
    ]
  }
}
```

### Metric types observed

| Metric | Units | Value field |
|--------|-------|-------------|
| `step_count` | count | `qty` |
| `active_energy` | kJ | `qty` |
| `apple_exercise_time` | min | `qty` |
| `apple_stand_time` | min | `qty` |
| `apple_stand_hour` | count | `qty` |
| `mindful_minutes` | min | `qty` |
| `heart_rate` | count/min | `Avg`, `Min`, `Max` |
| `resting_heart_rate` | count/min | `Avg`, `Min`, `Max` |
| `heart_rate_variability` | ms | `Avg`, `Min`, `Max` |
| `respiratory_rate` | count/min | `Avg`, `Min`, `Max` |
| `blood_oxygen_saturation` | % | `Avg`, `Min`, `Max` |
| `vo2_max` | ml/(kg·min) | `Avg`, `Min`, `Max` |
| `walking_heart_rate_average` | count/min | `Avg`, `Min`, `Max` |
| `walking_speed` | km/hr | `Avg`, `Min`, `Max` |
| `walking_step_length` | cm | `Avg`, `Min`, `Max` |
| `walking_double_support_percentage` | % | `Avg`, `Min`, `Max` |
| `walking_asymmetry_percentage` | % | `Avg`, `Min`, `Max` |
| `stair_speed_up` | m/s | `Avg`, `Min`, `Max` |
| `stair_speed_down` | m/s | `Avg`, `Min`, `Max` |
| `walking_running_distance` | km | `qty` |
| `flights_climbed` | count | `qty` |
| `basal_energy_burned` | kJ | `qty` |
| `headphone_audio_exposure` | dBASPL | `Avg`, `Min`, `Max` |
| `environmental_audio_exposure` | dBASPL | `Avg`, `Min`, `Max` |
| `apple_sleeping_wrist_temperature` | degC | `Avg`, `Min`, `Max` |
| `time_in_daylight` | min | `qty` |
| `handwashing` | s | `qty` |
| `physical_effort` | kcal/hr·kg | `Avg`, `Min`, `Max` |
| `cardio_recovery` | count/min | `Avg`, `Min`, `Max` |
| `breathing_disturbances` | count | `qty` |

### Value field logic

- **Cumulative metrics** (step_count, active_energy, etc.): use `qty` — it's the daily total
- **Rate/average metrics** (heart_rate, walking_speed, etc.): use `Avg` — `qty` is not meaningful for these

## Sleep (within metrics)

```json
{
  "name": "sleep_analysis",
  "units": "hr",
  "data": [
    {
      "date": "2026-05-04 00:00:00 +1000",
      "source": "Apple Watch",
      "sleepStart": "2026-05-03 23:04:17 +1000",
      "sleepEnd": "2026-05-04 07:36:58 +1000",
      "inBedStart": "2026-05-03 23:04:17 +1000",
      "inBedEnd": "2026-05-04 07:36:58 +1000",
      "totalSleep": 7.356405125955742,
      "core": 5.272491835421987,
      "deep": 0.6360737863845295,
      "rem": 1.4478395041492251,
      "awake": 1.1883792419234913,
      "asleep": 0,
      "inBed": 0
    }
  ]
}
```

### Notes

- Stage values are in **hours**
- `totalSleep` = core + deep + rem + asleep (excludes awake)
- `asleep` and `inBed` are legacy/unclassified stages (often 0 with modern Apple Watch)
- HAE also supports `aggregatedSleepAnalyses` and `sleepAnalyses` top-level formats (see parser for handling)

## Common patterns

- **Timestamps**: `YYYY-MM-DD HH:MM:SS +HHMM` (except State of Mind which uses ISO8601)
- **Quantity objects**: `{qty: number, units: string}`
- **Each export type arrives as a separate POST** with `{data: {<type>: [...]}}` structure
- **Source strings** include non-breaking spaces (e.g. `"Joseph’s Apple Watch"`)
