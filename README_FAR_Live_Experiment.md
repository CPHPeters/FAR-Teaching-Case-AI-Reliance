# Livestock Counting Review — FAR/Deloitte Live Training Experiment

## Overview

This oTree app implements a short live experiment for Deloitte/FAR training on **calibrated reliance on technology in auditing**. Participants review drone photographs of cattle and verify counts, with the counting source framed as either an AI tool (DroneCount AI) or a human team member (J. de Vries).

The experiment includes a **facilitator dashboard** that shows live aggregate results by condition, enabling immediate group discussion about over-reliance, under-reliance, and calibrated judgment.

## Quick Start

### Run Locally

```bash
cd otree_experiment
pip install otree  # if not already installed (requires oTree 5.x)
otree devserver 8060
```

Open [http://localhost:8060](http://localhost:8060) in your browser.

### Create a Session

1. Go to **Demo** page: [http://localhost:8060/demo/](http://localhost:8060/demo/)
2. Click **"Livestock Counting Review — Training Demo"**
3. This creates a session with 20 demo participants

For live training sessions:

1. Go to [http://localhost:8060/create_session/](http://localhost:8060/create_session/) (requires admin login)
2. Select the desired configuration
3. Set the number of participants
4. Click **Create**

### Admin Login

- **URL**: [http://localhost:8060/sessions/](http://localhost:8060/sessions/)
- **Username**: `admin`
- **Password**: `far2026admin`

### Participant Link

After creating a session, share the **session-wide link** with participants. They can also join via:

- **Room link**: [http://localhost:8060/room/training_room](http://localhost:8060/room/training_room) (create session in the room first)

Participants are randomly assigned to AI or Human condition (or forced to one condition using the `_ai_only` / `_human_only` configs).

### Facilitator Dashboard

**URL**: [http://localhost:8060/facilitator/?password=far2026](http://localhost:8060/facilitator/?password=far2026)

Features:
- Auto-refreshes every 10 seconds
- Shows 6 panels: Correct Counts, Agreement, Confidence, Assessment, Reliability, Training Indicators
- All panels split by AI vs Human condition
- **Session selector** to filter by specific session
- CSV export button
- Print-friendly layout

### Participant Live Results Page

After completing the experiment, participants automatically see a **live-updating results page**. The page updates every 5 seconds using oTree's built-in live-page functionality (`live_method`). No facilitator action is required. The answer key is shown automatically on the participant results page.

Features:
- Shows aggregate group results by condition (agreement rates, error detection, review time, confidence, reliability)
- Highlights differences between AI and Human conditions
- Updates automatically as other participants complete the experiment
- Answer key always visible — no facilitator release needed
- Uses oTree's native WebSocket-based live pages (works with `otree devserver`)

### Data Export

**Option 1 — Dashboard CSV**: Click the **📥 Export CSV** button on the facilitator dashboard.

**Option 2 — oTree built-in export**: Go to [http://localhost:8060/export/](http://localhost:8060/export/) and download the app-specific data. The custom export includes all computed fields.

The CSV includes: participant code, condition, all photo-level responses, agreement, corrected counts, effective counts, error metrics, post-task measures, timestamps, computed scores (total_correct, overreliance_score, underreliance_score, mean_abs_error), and process tracking fields.

## Experimental Design

### Conditions

- **AI condition**: Counts attributed to DroneCount AI (automated computer vision tool)
- **Human condition**: Counts attributed to J. de Vries (team member, 2 years experience)

### Photo Data

| Photo | Image | Displayed Count | Actual Count | Error | Status |
|-------|-------|----------------|--------------|-------|--------|
| 1 | Cows_1.jpg | 30 | 30 | 0 | ✅ Correct |
| 2 | Cows_2.jpg | 42 | 42 | 0 | ✅ Correct |
| 3 | Cows_3.jpg | 79 | 74 | +5 | ❌ Overcount |
| 4 | Cows_4.jpg | 65 | 57 | +8 | ❌ Overcount |

### Interpretation Notes

- **Photos 1 & 2** are correct — disagreement indicates **under-reliance** (unnecessary skepticism)
- **Photos 3 & 4** are wrong (overcounts of +5 and +8) — agreement indicates **over-reliance** (insufficient challenge)
- Comparing AI vs Human conditions reveals whether the same evidence is evaluated differently based solely on the source label
- High confidence + missed errors = **miscalibrated reliance**
- The pattern of responses maps directly to the CALIBRATE framework discussion points

## Process Tracking (Time & Engagement Variables)

The experiment captures detailed process tracking for each photograph to measure verification effort:

### Per-Photo Variables (X = 1, 2, 3, 4)

| Variable | Type | Description |
|----------|------|-------------|
| `photo_X_time_spent` | float | Total seconds from page load to submission |
| `photo_X_active_time` | float | Seconds the browser tab was in the foreground (excludes tab-away time) |
| `photo_X_image_focus_time` | float | Seconds the participant's viewport was scrolled to or focused on the photograph |
| `photo_X_zoom_opened` | bool | Whether the participant opened the zoom/enlarge view at least once |
| `photo_X_zoom_count` | int | Number of times the zoom view was opened |
| `photo_X_recount_started` | bool | Whether the participant began entering a corrected count (even if later deleted) |

### Aggregate Variables

| Variable | Computation |
|----------|-------------|
| `total_time_spent` | Sum of `photo_X_time_spent` across all 4 photos |
| `total_active_time` | Sum of `photo_X_active_time` across all 4 photos |
| `total_image_focus_time` | Sum of `photo_X_image_focus_time` across all 4 photos |
| `total_zoom_count` | Sum of `photo_X_zoom_count` across all 4 photos |
| `any_zoom_opened` | True if any `photo_X_zoom_opened` is True |

### Interpretation Cautions

Time spent is a process indicator of verification effort, not a standalone performance measure. Longer time may indicate more careful recounting, but it can also reflect difficulty or distraction. Interpret time together with agreement, corrected counts, and post-task confidence/reliability.

## Dashboard Panels

The facilitator dashboard displays six main panels:

1. **Correct Counts** — How many of the 4 photos each participant got right, by condition
2. **Agreement Rates** — Per-photo agreement percentages, split by AI vs Human
3. **Confidence** — Distribution of confidence ratings (0–100), by condition
4. **Overall Assessment** — Distribution across the 3 assessment options, by condition
5. **Perceived Reliability** — Distribution of reliability ratings (0–100), by condition
6. **Training Indicators** — Over-reliance score, under-reliance score, mean absolute error, by condition

## Configuration

### Session Configs

| Config | Description |
|--------|-------------|
| `livestock_training_demo` | Random AI/Human assignment, 20 participants |
| `livestock_training_ai_only` | All participants in AI condition |
| `livestock_training_human_only` | All participants in Human condition |
| `livestock_training_test` | Small test config (4 participants) |

### Change Facilitator Password

Edit `register_routes.py` — change the `DASHBOARD_PASSWORD` variable at the top of the file.

### Change Admin Password

Edit `settings.py` — change the `ADMIN_PASSWORD` variable (or set the `OTREE_ADMIN_PASSWORD` environment variable).

## Deployment

### Heroku

```bash
cd otree_experiment
pip freeze > requirements.txt  # ensure otree is listed
echo "web: otree prodserver 8000" > Procfile
heroku create your-app-name
git init && git add . && git commit -m "initial"
git push heroku main
heroku run otree resetdb
```

Set environment variables:
```bash
heroku config:set OTREE_ADMIN_PASSWORD=your_secure_password
heroku config:set OTREE_PRODUCTION=1
```

### Other Servers

Run with production settings:
```bash
export OTREE_PRODUCTION=1
export OTREE_ADMIN_PASSWORD=your_secure_password
otree prodserver 8000
```

Or use the ASGI wrapper for custom middleware support:
```bash
pip install uvicorn
uvicorn asgi_wrapper:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Images Don't Load

- Verify the images exist in `_static/livestock_counting_review/`:
  - `Cows_1.jpg`, `Cows_2.jpg`, `Cows_3.jpg`, `Cows_4.jpg`
- Check file permissions
- In production, ensure static files are being served (oTree handles this automatically in devserver)

### Facilitator Dashboard Shows No Data

- Participants must complete the entire experiment (all 4 photos + post-review) to appear
- Check the password parameter: `?password=far2026`
- Refresh the page or click the refresh button

### Database Reset

```bash
rm db.sqlite3
otree resetdb --noinput
```
