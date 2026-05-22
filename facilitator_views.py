"""
Custom Starlette views for the Facilitator Dashboard.
Imported and registered by __init__.py monkey-patch in settings.
"""
import csv
import io
import json
from pathlib import Path

from starlette.endpoints import HTTPEndpoint
from starlette.responses import HTMLResponse, JSONResponse, Response

from otree.database import dbq
from otree.models import Session, Participant


DASHBOARD_PASSWORD = 'far2026'


def check_password(request):
    pw = request.query_params.get('password', '')
    return pw == DASHBOARD_PASSWORD


def get_completed_players():
    """Get all completed players across all sessions of this app."""
    from livestock_counting_review import Player
    players = dbq(Player).all()
    completed = []
    in_progress = []
    for p in players:
        if p.field_maybe_none('photo_1_agree') is not None and p.field_maybe_none('confidence') is not None:
            completed.append(p)
        elif p.field_maybe_none('condition'):
            in_progress.append(p)
    return completed, in_progress


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


def compute_dashboard_data():
    completed, in_progress = get_completed_players()

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

    # Correct counts per photo
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

    # Assessment distribution
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

        # Time and engagement metrics
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


class FacilitatorDashboard(HTTPEndpoint):
    async def get(self, request):
        if not check_password(request):
            return Response('Access denied. Add ?password=far2026 to the URL.', status_code=403)
        html_path = Path(__file__).parent / 'livestock_counting_review' / 'FacilitatorDashboard.html'
        html = html_path.read_text()
        return HTMLResponse(html)


class FacilitatorAPI(HTTPEndpoint):
    async def get(self, request):
        if not check_password(request):
            return JSONResponse({'error': 'forbidden'}, status_code=403)
        data = compute_dashboard_data()
        return JSONResponse(data)


class FacilitatorCSV(HTTPEndpoint):
    async def get(self, request):
        if not check_password(request):
            return Response('Access denied', status_code=403)

        csv_content = generate_csv_content()
        return Response(
            csv_content,
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=livestock_counting_review_data.csv'},
        )
