"""
Register facilitator dashboard routes by wrapping the oTree ASGI app.
Uses a deferred import hook to avoid circular import issues.

Endpoints:
  /facilitator/?password=...                  Facilitator dashboard (password-protected)
  /facilitator_api/?password=...              Facilitator JSON API (password-protected)
  /facilitator_csv/?password=...              CSV export (password-protected)
  /facilitator_action/?password=...&action=.. Facilitator release controls (password-protected)
  /participant_live_results_api/?session=...   Participant-facing aggregate results (no password)
"""
import sys
import importlib
import csv
import io
import json
from pathlib import Path
from urllib.parse import parse_qs

from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

DASHBOARD_PASSWORD = 'far2026'

# ─── In-memory session flags (persisted per-process, reset on restart) ───────
# Maps session_code -> dict of flags
_session_flags = {}


def get_session_flags(session_code):
    if session_code not in _session_flags:
        _session_flags[session_code] = {
            'answers_released': True,
        }
    return _session_flags[session_code]


def check_password(query_string):
    params = parse_qs(query_string.decode('utf-8', errors='replace'))
    pw = params.get('password', [''])[0]
    return pw == DASHBOARD_PASSWORD


def parse_params(query_string):
    return parse_qs(query_string.decode('utf-8', errors='replace'))


# ─── Data helpers ────────────────────────────────────────────────────────────

def get_players_for_session(session_code=None):
    """Get completed and in-progress players, optionally filtered by session."""
    from otree.database import dbq
    from livestock_counting_review import Player
    players = dbq(Player).all()
    completed = []
    in_progress = []
    for p in players:
        try:
            if session_code and p.session.code != session_code:
                continue
            agree = p.field_maybe_none('photo_1_agree')
            conf = p.field_maybe_none('confidence')
            cond = p.field_maybe_none('condition')
            if agree is not None and conf is not None:
                completed.append(p)
            elif cond:
                in_progress.append(p)
        except Exception:
            pass
    return completed, in_progress


def get_completed_players():
    """Backward-compatible: all sessions."""
    return get_players_for_session(session_code=None)


def safe_photo_vals(players, field_template):
    """Return list of 4 mean values for photo_1..4 of a given field."""
    result = []
    for i in range(1, 5):
        vals = [p.field_maybe_none(field_template.format(i)) for p in players]
        vals = [v for v in vals if v is not None]
        result.append(sum(vals) / len(vals) if vals else 0)
    return result


def safe_photo_pct(players, field_template, total):
    """Return list of 4 percentages for a boolean photo field."""
    result = []
    for i in range(1, 5):
        count = sum(1 for p in players if getattr(p, field_template.format(i), False))
        result.append((count / total * 100) if total > 0 else 0)
    return result


def compute_dashboard_data(session_code=None):
    completed, in_progress = get_players_for_session(session_code)

    ai_players = [p for p in completed if p.condition == 'ai']
    human_players = [p for p in completed if p.condition == 'human']
    ai_progress = [p for p in in_progress if p.condition == 'ai']
    human_progress = [p for p in in_progress if p.condition == 'human']

    n_ai = len(ai_players)
    n_human = len(human_players)
    n_all = n_ai + n_human

    def safe_mean(values):
        return sum(values) / len(values) if values else 0

    def pct(count, total):
        return (count / total * 100) if total > 0 else 0

    correct_pct_ai = []
    correct_pct_human = []
    correct_pct_all = []
    agree_pct_ai = []
    agree_pct_human = []
    agree_pct_all = []

    for i in range(1, 5):
        ai_correct = sum(1 for p in ai_players if p.photo_correct(i))
        human_correct = sum(1 for p in human_players if p.photo_correct(i))
        all_correct = ai_correct + human_correct

        correct_pct_ai.append(pct(ai_correct, n_ai))
        correct_pct_human.append(pct(human_correct, n_human))
        correct_pct_all.append(pct(all_correct, n_all))

        ai_agree = sum(1 for p in ai_players if getattr(p, f'photo_{i}_agree'))
        human_agree = sum(1 for p in human_players if getattr(p, f'photo_{i}_agree'))
        all_agree = ai_agree + human_agree
        agree_pct_ai.append(pct(ai_agree, n_ai))
        agree_pct_human.append(pct(human_agree, n_human))
        agree_pct_all.append(pct(all_agree, n_all))

    assessment_pct_ai = [0, 0, 0]
    assessment_pct_human = [0, 0, 0]
    assessment_pct_all = [0, 0, 0]
    for p in ai_players:
        if p.overall_assessment in [1, 2, 3]:
            assessment_pct_ai[p.overall_assessment - 1] += 1
            assessment_pct_all[p.overall_assessment - 1] += 1
    for p in human_players:
        if p.overall_assessment in [1, 2, 3]:
            assessment_pct_human[p.overall_assessment - 1] += 1
            assessment_pct_all[p.overall_assessment - 1] += 1
    assessment_pct_ai = [pct(v, n_ai) for v in assessment_pct_ai]
    assessment_pct_human = [pct(v, n_human) for v in assessment_pct_human]
    assessment_pct_all = [pct(v, n_all) for v in assessment_pct_all]

    # ── Time and engagement metrics ──────────────────────────────────
    mean_photo_time_all = safe_photo_vals(completed, 'photo_{}_time_spent')
    mean_photo_time_ai = safe_photo_vals(ai_players, 'photo_{}_time_spent')
    mean_photo_time_human = safe_photo_vals(human_players, 'photo_{}_time_spent')

    mean_active_time_all = safe_photo_vals(completed, 'photo_{}_active_time')
    mean_active_time_ai = safe_photo_vals(ai_players, 'photo_{}_active_time')
    mean_active_time_human = safe_photo_vals(human_players, 'photo_{}_active_time')

    mean_image_focus_time_all = safe_photo_vals(completed, 'photo_{}_image_focus_time')
    mean_image_focus_time_ai = safe_photo_vals(ai_players, 'photo_{}_image_focus_time')
    mean_image_focus_time_human = safe_photo_vals(human_players, 'photo_{}_image_focus_time')

    mean_zoom_count_all = safe_photo_vals(completed, 'photo_{}_zoom_count')
    mean_zoom_count_ai = safe_photo_vals(ai_players, 'photo_{}_zoom_count')
    mean_zoom_count_human = safe_photo_vals(human_players, 'photo_{}_zoom_count')

    zoom_open_pct_all = safe_photo_pct(completed, 'photo_{}_zoom_opened', n_all)
    zoom_open_pct_ai = safe_photo_pct(ai_players, 'photo_{}_zoom_opened', n_ai)
    zoom_open_pct_human = safe_photo_pct(human_players, 'photo_{}_zoom_opened', n_human)

    # Aggregate totals
    mean_total_time_all = safe_mean([p.total_time_spent for p in completed])
    mean_total_time_ai = safe_mean([p.total_time_spent for p in ai_players])
    mean_total_time_human = safe_mean([p.total_time_spent for p in human_players])

    mean_total_active_time_all = safe_mean([p.total_active_time for p in completed])
    mean_total_active_time_ai = safe_mean([p.total_active_time for p in ai_players])
    mean_total_active_time_human = safe_mean([p.total_active_time for p in human_players])

    mean_total_image_focus_time_all = safe_mean([p.total_image_focus_time for p in completed])
    mean_total_image_focus_time_ai = safe_mean([p.total_image_focus_time for p in ai_players])
    mean_total_image_focus_time_human = safe_mean([p.total_image_focus_time for p in human_players])

    # % who opened zoom at least once (any photo)
    zoom_any_pct_all = pct(sum(1 for p in completed if p.any_zoom_opened), n_all)
    zoom_any_pct_ai = pct(sum(1 for p in ai_players if p.any_zoom_opened), n_ai)
    zoom_any_pct_human = pct(sum(1 for p in human_players if p.any_zoom_opened), n_human)

    return dict(
        n_completed=n_all,
        n_in_progress=len(in_progress),
        n_ai=n_ai,
        n_human=n_human,
        n_ai_progress=len(ai_progress),
        n_human_progress=len(human_progress),

        correct_pct_ai=correct_pct_ai,
        correct_pct_human=correct_pct_human,
        correct_pct_all=correct_pct_all,

        agree_pct_ai=agree_pct_ai,
        agree_pct_human=agree_pct_human,
        agree_pct_all=agree_pct_all,

        mean_confidence_ai=safe_mean([p.confidence for p in ai_players if p.confidence is not None]),
        mean_confidence_human=safe_mean([p.confidence for p in human_players if p.confidence is not None]),
        mean_confidence_all=safe_mean([p.confidence for p in completed if p.confidence is not None]),

        mean_reliability_ai=safe_mean([p.perceived_reliability for p in ai_players if p.perceived_reliability is not None]),
        mean_reliability_human=safe_mean([p.perceived_reliability for p in human_players if p.perceived_reliability is not None]),
        mean_reliability_all=safe_mean([p.perceived_reliability for p in completed if p.perceived_reliability is not None]),

        assessment_pct_ai=assessment_pct_ai,
        assessment_pct_human=assessment_pct_human,
        assessment_pct_all=assessment_pct_all,

        mean_total_correct_ai=safe_mean([p.total_correct for p in ai_players]),
        mean_total_correct_human=safe_mean([p.total_correct for p in human_players]),
        mean_total_correct_all=safe_mean([p.total_correct for p in completed]),

        mean_overreliance_ai=safe_mean([p.overreliance_score for p in ai_players]),
        mean_overreliance_human=safe_mean([p.overreliance_score for p in human_players]),
        mean_overreliance_all=safe_mean([p.overreliance_score for p in completed]),

        mean_underreliance_ai=safe_mean([p.underreliance_score for p in ai_players]),
        mean_underreliance_human=safe_mean([p.underreliance_score for p in human_players]),
        mean_underreliance_all=safe_mean([p.underreliance_score for p in completed]),

        mean_abs_error_ai=safe_mean([p.mean_abs_error for p in ai_players]),
        mean_abs_error_human=safe_mean([p.mean_abs_error for p in human_players]),
        mean_abs_error_all=safe_mean([p.mean_abs_error for p in completed]),

        # Time and engagement metrics — per-photo lists of 4
        mean_photo_time_all=mean_photo_time_all,
        mean_photo_time_ai=mean_photo_time_ai,
        mean_photo_time_human=mean_photo_time_human,

        mean_active_time_all=mean_active_time_all,
        mean_active_time_ai=mean_active_time_ai,
        mean_active_time_human=mean_active_time_human,

        mean_image_focus_time_all=mean_image_focus_time_all,
        mean_image_focus_time_ai=mean_image_focus_time_ai,
        mean_image_focus_time_human=mean_image_focus_time_human,

        mean_zoom_count_all=mean_zoom_count_all,
        mean_zoom_count_ai=mean_zoom_count_ai,
        mean_zoom_count_human=mean_zoom_count_human,

        zoom_open_pct_all=zoom_open_pct_all,
        zoom_open_pct_ai=zoom_open_pct_ai,
        zoom_open_pct_human=zoom_open_pct_human,

        # Aggregate totals
        mean_total_time_all=mean_total_time_all,
        mean_total_time_ai=mean_total_time_ai,
        mean_total_time_human=mean_total_time_human,

        mean_total_active_time_all=mean_total_active_time_all,
        mean_total_active_time_ai=mean_total_active_time_ai,
        mean_total_active_time_human=mean_total_active_time_human,

        mean_total_image_focus_time_all=mean_total_image_focus_time_all,
        mean_total_image_focus_time_ai=mean_total_image_focus_time_ai,
        mean_total_image_focus_time_human=mean_total_image_focus_time_human,

        zoom_any_pct_all=zoom_any_pct_all,
        zoom_any_pct_ai=zoom_any_pct_ai,
        zoom_any_pct_human=zoom_any_pct_human,

        # Correct error detection
        mean_correct_error_detection_all=safe_mean([p.correct_error_detection for p in completed]),
        mean_correct_error_detection_ai=safe_mean([p.correct_error_detection for p in ai_players]),
        mean_correct_error_detection_human=safe_mean([p.correct_error_detection for p in human_players]),
    )


def generate_csv_content():
    completed, _ = get_completed_players()
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        'session_code', 'participant_id', 'participant_code', 'condition',
        'start_time', 'end_time',
    ]
    for i in range(1, 5):
        headers.extend([
            f'photo_{i}_displayed_count', f'photo_{i}_actual_count',
            f'photo_{i}_agree', f'photo_{i}_corrected_count',
            f'photo_{i}_effective_count', f'photo_{i}_correct',
            f'photo_{i}_abs_error', f'photo_{i}_signed_error',
            f'photo_{i}_accepted_incorrect', f'photo_{i}_rejected_correct',
            f'photo_{i}_time_spent', f'photo_{i}_active_time', f'photo_{i}_image_focus_time',
            f'photo_{i}_zoom_opened', f'photo_{i}_zoom_count', f'photo_{i}_recount_started',
        ])
    headers.extend([
        'total_correct', 'correct_error_detection', 'overreliance_score',
        'underreliance_score', 'mean_abs_error',
        'total_time_spent', 'total_active_time', 'total_image_focus_time',
        'total_zoom_count', 'any_zoom_opened',
        'confidence', 'overall_assessment', 'perceived_reliability',
    ])
    writer.writerow(headers)

    for p in completed:
        row = [
            p.session.code, p.participant.id_in_session, p.participant.code,
            p.condition, p.field_maybe_none('start_time'), p.field_maybe_none('end_time'),
        ]
        for i in range(1, 5):
            row.extend([
                getattr(p, f'photo_{i}_displayed_count'),
                getattr(p, f'photo_{i}_actual_count'),
                getattr(p, f'photo_{i}_agree'),
                p.field_maybe_none(f'photo_{i}_corrected_count'),
                p.effective_count(i),
                p.photo_correct(i),
                p.photo_abs_error(i),
                p.photo_signed_error(i),
                p.photo_accepted_incorrect(i),
                p.photo_rejected_correct(i),
                p.field_maybe_none(f'photo_{i}_time_spent'),
                p.field_maybe_none(f'photo_{i}_active_time'),
                p.field_maybe_none(f'photo_{i}_image_focus_time'),
                getattr(p, f'photo_{i}_zoom_opened', False),
                p.field_maybe_none(f'photo_{i}_zoom_count') or 0,
                getattr(p, f'photo_{i}_recount_started', False),
            ])
        row.extend([
            p.total_correct, p.correct_error_detection,
            p.overreliance_score, p.underreliance_score,
            round(p.mean_abs_error, 2),
            round(p.total_time_spent, 2),
            round(p.total_active_time, 2),
            round(p.total_image_focus_time, 2),
            p.total_zoom_count,
            p.any_zoom_opened,
            p.confidence, p.overall_assessment, p.perceived_reliability,
        ])
        writer.writerow(row)

    return output.getvalue()


def get_all_session_codes():
    """Return all session codes that have livestock_counting_review players."""
    from otree.database import dbq
    from livestock_counting_review import Player
    codes = set()
    for p in dbq(Player).all():
        try:
            codes.add(p.session.code)
        except Exception:
            pass
    return sorted(codes)


# ─── ASGI Middleware ─────────────────────────────────────────────────────────

class FacilitatorMiddleware:
    """ASGI middleware that intercepts custom URLs."""

    def __init__(self, app: ASGIApp):
        self.app = app

    def __getattr__(self, name):
        return getattr(self.app, name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '').rstrip('/')
        qs = scope.get('query_string', b'')
        params = parse_params(qs)

        # ── Facilitator dashboard ────────────────────────────────────
        if path == '/facilitator':
            if not check_password(qs):
                response = HTMLResponse(
                    '<h2>Access Denied</h2><p>Add <code>?password=far2026</code> to the URL.</p>',
                    status_code=403
                )
            else:
                html_path = Path(__file__).parent / 'livestock_counting_review' / 'FacilitatorDashboard.html'
                response = HTMLResponse(html_path.read_text())
            await response(scope, receive, send)
            return

        # ── Facilitator JSON API ─────────────────────────────────────
        if path == '/facilitator_api':
            if not check_password(qs):
                response = JSONResponse({'error': 'forbidden'}, status_code=403)
            else:
                try:
                    session_code = params.get('session', [None])[0]
                    data = compute_dashboard_data(session_code)
                    # Include session flags + list of sessions
                    sessions = get_all_session_codes()
                    flags_by_session = {}
                    for sc in sessions:
                        flags_by_session[sc] = get_session_flags(sc)
                    data['sessions'] = sessions
                    data['session_flags'] = flags_by_session
                    data['active_session'] = session_code
                    response = JSONResponse(data)
                except Exception as e:
                    import traceback
                    response = JSONResponse({'error': str(e), 'traceback': traceback.format_exc()}, status_code=500)
            await response(scope, receive, send)
            return

        # ── Facilitator action (release/hide answers) ────────────────
        if path == '/facilitator_action':
            if not check_password(qs):
                response = JSONResponse({'error': 'forbidden'}, status_code=403)
            else:
                action = params.get('action', [''])[0]
                session_code = params.get('session', [''])[0]
                if not session_code:
                    response = JSONResponse({'error': 'session parameter required'}, status_code=400)
                else:
                    flags = get_session_flags(session_code)
                    if action == 'release_answers':
                        flags['answers_released'] = True
                        response = JSONResponse({'ok': True, 'answers_released': True})
                    elif action == 'hide_answers':
                        flags['answers_released'] = False
                        response = JSONResponse({'ok': True, 'answers_released': False})
                    else:
                        response = JSONResponse({'error': f'unknown action: {action}'}, status_code=400)
            await response(scope, receive, send)
            return

        # ── Participant live results API (no password) ───────────────
        if path == '/participant_live_results_api':
            try:
                session_code = params.get('session', [None])[0]
                if not session_code:
                    response = JSONResponse({'error': 'session parameter required'}, status_code=400)
                    await response(scope, receive, send)
                    return

                data = compute_dashboard_data(session_code)
                flags = get_session_flags(session_code)

                def r1(v): return round(v, 1)
                def r2(v): return round(v, 2)
                def rl(lst): return [round(v, 1) for v in lst]

                safe_data = dict(
                    session_code=session_code,
                    n_completed=data['n_completed'],
                    n_in_progress=data['n_in_progress'],
                    n_completed_ai=data['n_ai'],
                    n_completed_human=data['n_human'],
                    n_in_progress_ai=data['n_ai_progress'],
                    n_in_progress_human=data['n_human_progress'],

                    agree_pct_all=rl(data['agree_pct_all']),
                    agree_pct_ai=rl(data['agree_pct_ai']),
                    agree_pct_human=rl(data['agree_pct_human']),

                    correct_pct_all=rl(data['correct_pct_all']),
                    correct_pct_ai=rl(data['correct_pct_ai']),
                    correct_pct_human=rl(data['correct_pct_human']),

                    mean_confidence_all=r1(data['mean_confidence_all']),
                    mean_confidence_ai=r1(data['mean_confidence_ai']),
                    mean_confidence_human=r1(data['mean_confidence_human']),

                    assessment_pct_all=rl(data['assessment_pct_all']),
                    assessment_pct_ai=rl(data['assessment_pct_ai']),
                    assessment_pct_human=rl(data['assessment_pct_human']),

                    mean_reliability_all=r1(data['mean_reliability_all']),
                    mean_reliability_ai=r1(data['mean_reliability_ai']),
                    mean_reliability_human=r1(data['mean_reliability_human']),

                    mean_total_correct_all=r2(data['mean_total_correct_all']),
                    mean_total_correct_ai=r2(data['mean_total_correct_ai']),
                    mean_total_correct_human=r2(data['mean_total_correct_human']),

                    mean_overreliance_all=r2(data['mean_overreliance_all']),
                    mean_overreliance_ai=r2(data['mean_overreliance_ai']),
                    mean_overreliance_human=r2(data['mean_overreliance_human']),

                    mean_underreliance_all=r2(data['mean_underreliance_all']),
                    mean_underreliance_ai=r2(data['mean_underreliance_ai']),
                    mean_underreliance_human=r2(data['mean_underreliance_human']),

                    # Time and engagement metrics (aggregates only)
                    mean_photo_time_all=rl(data['mean_photo_time_all']),
                    mean_photo_time_ai=rl(data['mean_photo_time_ai']),
                    mean_photo_time_human=rl(data['mean_photo_time_human']),

                    mean_active_time_all=rl(data['mean_active_time_all']),
                    mean_active_time_ai=rl(data['mean_active_time_ai']),
                    mean_active_time_human=rl(data['mean_active_time_human']),

                    mean_image_focus_time_all=rl(data['mean_image_focus_time_all']),
                    mean_image_focus_time_ai=rl(data['mean_image_focus_time_ai']),
                    mean_image_focus_time_human=rl(data['mean_image_focus_time_human']),

                    mean_zoom_count_all=rl(data['mean_zoom_count_all']),
                    mean_zoom_count_ai=rl(data['mean_zoom_count_ai']),
                    mean_zoom_count_human=rl(data['mean_zoom_count_human']),

                    zoom_open_pct_all=rl(data['zoom_open_pct_all']),
                    zoom_open_pct_ai=rl(data['zoom_open_pct_ai']),
                    zoom_open_pct_human=rl(data['zoom_open_pct_human']),

                    mean_total_time_all=r1(data['mean_total_time_all']),
                    mean_total_time_ai=r1(data['mean_total_time_ai']),
                    mean_total_time_human=r1(data['mean_total_time_human']),

                    mean_total_active_time_all=r1(data['mean_total_active_time_all']),
                    mean_total_active_time_ai=r1(data['mean_total_active_time_ai']),
                    mean_total_active_time_human=r1(data['mean_total_active_time_human']),

                    mean_total_image_focus_time_all=r1(data['mean_total_image_focus_time_all']),
                    mean_total_image_focus_time_ai=r1(data['mean_total_image_focus_time_ai']),
                    mean_total_image_focus_time_human=r1(data['mean_total_image_focus_time_human']),

                    zoom_any_pct_all=r1(data['zoom_any_pct_all']),
                    zoom_any_pct_ai=r1(data['zoom_any_pct_ai']),
                    zoom_any_pct_human=r1(data['zoom_any_pct_human']),

                    mean_correct_error_detection_all=r2(data['mean_correct_error_detection_all']),
                    mean_correct_error_detection_ai=r2(data['mean_correct_error_detection_ai']),
                    mean_correct_error_detection_human=r2(data['mean_correct_error_detection_human']),

                    mean_abs_error_all=r2(data['mean_abs_error_all']),
                    mean_abs_error_ai=r2(data['mean_abs_error_ai']),
                    mean_abs_error_human=r2(data['mean_abs_error_human']),

                    # Always show answers on participant page (no facilitator toggle needed)
                    answers_released=True,
                )
                response = JSONResponse(safe_data)
            except Exception as e:
                import traceback
                response = JSONResponse({'error': str(e), 'detail': traceback.format_exc()}, status_code=500)
            await response(scope, receive, send)
            return

        # ── CSV export ───────────────────────────────────────────────
        if path == '/facilitator_csv':
            if not check_password(qs):
                response = Response('Access denied', status_code=403)
            else:
                try:
                    csv_content = generate_csv_content()
                    response = Response(
                        csv_content,
                        media_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=livestock_counting_review_data.csv'},
                    )
                except Exception as e:
                    response = Response(f'Error: {e}', status_code=500)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ─── Patch oTree ASGI app ───────────────────────────────────────────────────
# Uses a background thread to wait for otree.asgi to load, then wraps it.
# This is more robust than the old sys.meta_path import hook which could
# silently fail on some Python versions.

import threading
import time as _time

_patch_done = False


def _deferred_patch():
    global _patch_done
    # If already loaded, patch immediately
    if 'otree.asgi' in sys.modules:
        _do_patch()
        return
    # Otherwise poll until it appears (up to 30 seconds)
    for _ in range(300):
        _time.sleep(0.1)
        if 'otree.asgi' in sys.modules:
            _do_patch()
            return
    print("[facilitator] WARNING: otree.asgi never loaded — middleware NOT installed")


def _do_patch():
    global _patch_done
    if _patch_done:
        return
    _patch_done = True
    import otree.asgi
    if not isinstance(otree.asgi.app, FacilitatorMiddleware):
        otree.asgi.app = FacilitatorMiddleware(otree.asgi.app)
        print("[facilitator] Dashboard middleware installed at /facilitator/")
    else:
        print("[facilitator] Middleware already installed")


threading.Thread(target=_deferred_patch, daemon=True).start()
