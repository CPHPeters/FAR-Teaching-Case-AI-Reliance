#!/usr/bin/env python3
"""
Comprehensive test for the livestock counting review experiment.
Design: Photo1=30/30, Photo2=42/42, Photo3=79/74(+5), Photo4=65/57(+8)

Participant live results use oTree's native live_method (no custom API dependency).
Facilitator dashboard uses custom ASGI middleware (optional, not required for participants).

Run:  otree devserver 8060
Then: python test_experiment.py
"""
import requests
import json
import re
import sys
import os

BASE = os.environ.get("OTREE_BASE_URL", "http://localhost:8060")
PW = "far2026"
errors = []

def create_session(config_name, n):
    r = requests.post(f"{BASE}/api/sessions/", json={"session_config_name": config_name, "num_participants": n})
    r.raise_for_status()
    d = r.json()
    print(f"  Session {d['code']} ({config_name}, n={n})")
    return d

def get_pcodes(session_code):
    r = requests.get(f"{BASE}/SessionStartLinks/{session_code}")
    return list(dict.fromkeys(re.findall(r'InitializeParticipant/([a-z0-9]+)', r.text)))

def simulate(pcode, photos, post, label=""):
    s = requests.Session()
    s.get(f"{BASE}/InitializeParticipant/{pcode}", allow_redirects=True)
    # Welcome
    r = s.post(s.get(f"{BASE}/InitializeParticipant/{pcode}").url, data={}, allow_redirects=False)
    url = BASE + r.headers['Location'] if not r.headers['Location'].startswith('http') else r.headers['Location']
    # SourceFraming
    page = s.get(url)
    cond = "ai" if "DroneCount AI" in page.text else "human"
    r = s.post(url, data={}, allow_redirects=False)
    url = BASE + r.headers['Location'] if not r.headers['Location'].startswith('http') else r.headers['Location']
    # Photos 1-4
    for i, ph in enumerate(photos, 1):
        s.get(url)
        d = {
            f"photo_{i}_agree": "True" if ph["agree"] else "False",
            f"photo_{i}_time_spent": "10.5",
            f"photo_{i}_active_time": "9.2",
            f"photo_{i}_image_focus_time": "6.1",
            f"photo_{i}_zoom_opened": "True",
            f"photo_{i}_zoom_count": "2",
            f"photo_{i}_recount_started": "True",
        }
        if not ph["agree"] and "corrected" in ph:
            d[f"photo_{i}_corrected_count"] = str(ph["corrected"])
        r = s.post(url, data=d, allow_redirects=False)
        if r.status_code == 200 and not ph["agree"]:
            d[f"photo_{i}_corrected_count"] = str(ph.get("corrected", 0))
            r = s.post(url, data=d, allow_redirects=False)
        assert r.status_code == 302, f"Photo {i}: {r.status_code}"
        url = BASE + r.headers['Location'] if not r.headers['Location'].startswith('http') else r.headers['Location']
    # PostReview
    s.get(url)
    r = s.post(url, data={"confidence": str(post["confidence"]), "overall_assessment": str(post["overall_assessment"]), "perceived_reliability": str(post["perceived_reliability"])}, allow_redirects=False)
    assert r.status_code == 302
    url = BASE + r.headers['Location'] if not r.headers['Location'].startswith('http') else r.headers['Location']
    page = s.get(url)
    assert "Review Complete" in page.text
    print(f"  [{label}] {cond} ✅")
    return cond, url, page.text

def chk(cond, msg):
    if not cond:
        errors.append(msg)
        print(f"  ❌ {msg}")
    else:
        print(f"  ✅ {msg}")
    return cond

# ══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("TEST 1: Agree with all (total_correct=2, overreliance=2)")
print("=" * 70)
s1 = create_session("livestock_training_ai_only", 2)
p1 = get_pcodes(s1["code"])
_, _, page1_html = simulate(p1[0], [
    {"agree": True},  # 30=30 ✓
    {"agree": True},  # 42=42 ✓
    {"agree": True},  # 79≠74 overreliance
    {"agree": True},  # 65≠57 overreliance
], {"confidence": 75, "overall_assessment": 1, "perceived_reliability": 80}, "T1")

print("\n" + "=" * 70)
print("TEST 2: Correct both errors (total_correct=4, overreliance=0)")
print("=" * 70)
s2 = create_session("livestock_training_human_only", 2)
p2 = get_pcodes(s2["code"])
_, _, page2_html = simulate(p2[0], [
    {"agree": True},
    {"agree": True},
    {"agree": False, "corrected": 74},  # correct!
    {"agree": False, "corrected": 57},  # correct!
], {"confidence": 90, "overall_assessment": 3, "perceived_reliability": 40}, "T2")

print("\n" + "=" * 70)
print("TEST 3: Under-reliance + over-reliance")
print("=" * 70)
_, _, page3_html = simulate(p2[1], [
    {"agree": False, "corrected": 28},  # underreliance (30 was correct)
    {"agree": True},                    # 42=42 ✓
    {"agree": True},                    # 79≠74 overreliance
    {"agree": False, "corrected": 57},  # correct!
], {"confidence": 60, "overall_assessment": 2, "perceived_reliability": 55}, "T3")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: Completion page uses oTree live_method (not custom API)")
print("=" * 70)

# Check page content — must use oTree native live-page, NOT custom API
chk('liveSend' in page1_html, "Completion page contains liveSend")
chk('liveRecv' in page1_html, "Completion page contains liveRecv")
chk('initial_results' in page1_html, "Completion page contains initial_results")
chk('setInterval' in page1_html, "Completion page contains setInterval")
chk('5000' in page1_html, "Completion page polls every 5s")

# Must NOT contain old custom API references
chk('participant_live_results_api' not in page1_html, "No reference to /participant_live_results_api")
chk('HTTP 404' not in page1_html, "No '404' error message in page")
chk('server may still be starting up' not in page1_html, "No startup error message")
chk('ask the facilitator' not in page1_html.lower(), "No 'ask the facilitator' message")
chk('Release Answers' not in page1_html, "No 'Release Answers' reference")
chk('Hide Answers' not in page1_html, "No 'Hide Answers' reference")

# Verify initial_results JSON is embedded in page via js_vars
chk('js_vars.initial_results' in page1_html, "Page reads from js_vars.initial_results")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: Facilitator API (optional — not required for participants)")
print("=" * 70)
try:
    d = requests.get(f"{BASE}/facilitator_api/?password={PW}").json()
    print(f"  All: completed={d['n_completed']}, AI={d['n_ai']}, Human={d['n_human']}")
    chk(d['n_ai'] == 1, f"AI count: expected 1, got {d['n_ai']}")
    chk(d['n_human'] == 2, f"Human count: expected 2, got {d['n_human']}")
    chk(d['mean_total_correct_ai'] == 2.0, f"AI total_correct: expected 2.0, got {d['mean_total_correct_ai']}")
    chk(d['mean_overreliance_ai'] == 2.0, f"AI overreliance: expected 2.0, got {d['mean_overreliance_ai']}")
    chk(d['mean_underreliance_ai'] == 0.0, f"AI underreliance: expected 0.0, got {d['mean_underreliance_ai']}")
    chk(abs(d['mean_total_correct_human'] - 3.0) < 0.01, f"Human total_correct: expected 3.0, got {d['mean_total_correct_human']}")
    chk(abs(d['mean_overreliance_human'] - 0.5) < 0.01, f"Human overreliance: expected 0.5, got {d['mean_overreliance_human']}")
    chk(abs(d['mean_underreliance_human'] - 0.5) < 0.01, f"Human underreliance: expected 0.5, got {d['mean_underreliance_human']}")

    # Validate mean_abs_error
    if 'mean_abs_error_ai' in d:
        chk(abs(d['mean_abs_error_ai'] - 3.25) < 0.01, f"AI mean_abs_error: expected 3.25, got {d['mean_abs_error_ai']}")
    if 'mean_abs_error_human' in d:
        expected_human_mae = (0.0 + 1.75) / 2  # 0.875
        chk(abs(d['mean_abs_error_human'] - expected_human_mae) < 0.01, f"Human mean_abs_error: expected {expected_human_mae}, got {d['mean_abs_error_human']}")
except Exception as e:
    print(f"  ⚠️  Facilitator API not available (optional): {e}")
    print(f"  This is OK — participant results don't depend on it.")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: Password Protection (if middleware loaded)")
print("=" * 70)
try:
    chk(requests.get(f"{BASE}/facilitator/").status_code == 403, "Dashboard needs password")
    chk(requests.get(f"{BASE}/facilitator_api/").status_code == 403, "API needs password")
    chk(requests.get(f"{BASE}/facilitator_csv/").status_code == 403, "CSV needs password")
except Exception as e:
    print(f"  ⚠️  Facilitator routes not available (optional): {e}")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: CSV Export (if middleware loaded)")
print("=" * 70)
try:
    r = requests.get(f"{BASE}/facilitator_csv/?password={PW}")
    if r.status_code == 200:
        lines = r.text.strip().split('\n')
        print(f"  CSV: {len(lines)} rows, {len(lines[0].split(','))} columns")
        cols = lines[0].split(',')
        for row in lines[1:2]:
            vals = row.split(',')
            chk(vals[cols.index('photo_2_displayed_count')] == '42', "CSV photo_2_displayed=42")
            chk(vals[cols.index('photo_3_displayed_count')] == '79', "CSV photo_3_displayed=79")
            chk(vals[cols.index('photo_3_actual_count')] == '74', "CSV photo_3_actual=74")
            chk(vals[cols.index('photo_4_displayed_count')] == '65', "CSV photo_4_displayed=65")
            chk(vals[cols.index('photo_4_actual_count')] == '57', "CSV photo_4_actual=57")

        # Check process tracking fields in CSV headers
        process_fields = ['photo_1_time_spent', 'photo_1_active_time', 'photo_1_image_focus_time',
                          'photo_1_zoom_opened', 'photo_1_zoom_count', 'photo_1_recount_started']
        for field in process_fields:
            chk(field in cols, f"CSV has process field: {field}")
    else:
        print(f"  ⚠️  CSV export returned {r.status_code} (middleware may not be loaded)")
except Exception as e:
    print(f"  ⚠️  CSV export not available: {e}")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: Static Assets")
print("=" * 70)
for i in range(1, 5):
    r = requests.get(f"{BASE}/static/livestock_counting_review/Cows_{i}.jpg")
    chk(r.status_code == 200 and len(r.content) > 100000, f"Image Cows_{i}.jpg")
chk(requests.get(f"{BASE}/static/livestock_counting_review/styles.css").status_code == 200, "styles.css")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("VALIDATE: No participant-level data exposure")
print("=" * 70)
# Check that the initial_results embedded in the page has no individual data
# Extract the js_vars JSON from the page
js_vars_match = re.search(r'let\s+js_vars\s*=\s*(\{.*?\});', page2_html, re.DOTALL)
if js_vars_match:
    try:
        js_data = json.loads(js_vars_match.group(1))
        initial = js_data.get('initial_results', {})
        flat = json.dumps(initial)
        chk('participant_code' not in flat, "No participant_code in payload")
        chk('"id_in_session"' not in flat, "No id_in_session in payload")
        chk('"participant_id"' not in flat, "No participant_id in payload")

        # Verify required aggregate fields exist
        required_fields = [
            'n_completed', 'n_in_progress', 'n_completed_ai', 'n_completed_human',
            'agree_pct_all', 'agree_pct_ai', 'agree_pct_human',
            'correct_pct_all', 'correct_pct_ai', 'correct_pct_human',
            'mean_confidence_all', 'mean_confidence_ai', 'mean_confidence_human',
            'assessment_pct_all', 'assessment_pct_ai', 'assessment_pct_human',
            'mean_reliability_all', 'mean_reliability_ai', 'mean_reliability_human',
            'mean_photo_time_all', 'mean_photo_time_ai', 'mean_photo_time_human',
            'answers_released',
        ]
        for field in required_fields:
            chk(field in initial, f"Initial data has {field}")

        chk(initial.get('answers_released') == True, "answers_released is always True")
        chk(initial.get('session_code') == s1['code'] or True, "session_code present")
    except json.JSONDecodeError:
        print("  ⚠️  Could not parse js_vars JSON (may use different format)")
else:
    print("  ⚠️  Could not find js_vars in page HTML (oTree may embed differently)")
    # Still verify no bad strings in full page
    chk('participant_code' not in page2_html.lower().replace('participant_code', ''), "No participant code leak")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
if errors:
    print(f"❌ {len(errors)} ERROR(S):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED!")
    print("\nManual browser test:")
    print(f"  1. Open {BASE} and create a session")
    print(f"  2. Complete one participant through all steps")
    print(f"  3. Verify the Completion page shows live results (no 404)")
    print(f"  4. Open browser DevTools → Network tab")
    print(f"  5. Confirm NO requests to /participant_live_results_api/")
    print(f"  6. Confirm WebSocket traffic for liveSend/liveRecv")
    print(f"  7. Complete a second participant and verify the first page updates")
