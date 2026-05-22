from otree.api import *
import time
import random
import json

doc = """
Livestock Counting Review — Inventory Observation Procedures
Between-subjects experiment: AI vs Human condition for calibrated reliance on technology in auditing.
"""

# ─── Centralized photo data (single source of truth) ────────────────────────

PHOTO_DATA = {
    1: dict(displayed=30, actual=30, image='Cows_1.jpg', error_label='Correct'),
    2: dict(displayed=42, actual=42, image='Cows_2.jpg', error_label='Correct'),
    3: dict(displayed=79, actual=74, image='Cows_3.jpg', error_label='+5 overcount'),
    4: dict(displayed=65, actual=57, image='Cows_4.jpg', error_label='+8 overcount'),
}

# ─── Constants ───────────────────────────────────────────────────────────────

class C(BaseConstants):
    NAME_IN_URL = 'livestock_counting_review'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


# ─── Subsession ──────────────────────────────────────────────────────────────

class Subsession(BaseSubsession):
    pass


def creating_session(subsession: Subsession):
    import itertools
    force = subsession.session.config.get('force_condition', None)
    if force:
        for p in subsession.get_players():
            p.participant.condition = force
            p.condition = force
    else:
        conditions = itertools.cycle(['ai', 'human'])
        players = subsession.get_players()
        random.shuffle(players)
        for p in players:
            c = next(conditions)
            p.participant.condition = c
            p.condition = c

    # Store photo data on each player
    for p in subsession.get_players():
        for i in range(1, 5):
            setattr(p, f'photo_{i}_displayed_count', PHOTO_DATA[i]['displayed'])
            setattr(p, f'photo_{i}_actual_count', PHOTO_DATA[i]['actual'])


# ─── Group ───────────────────────────────────────────────────────────────────

class Group(BaseGroup):
    pass


# ─── Player ──────────────────────────────────────────────────────────────────

class Player(BasePlayer):
    # Condition
    condition = models.StringField()

    # Timestamps
    start_time = models.StringField()
    end_time = models.StringField()

    # ── Photo 1 ──────────────────────────────────────────────────────
    photo_1_displayed_count = models.IntegerField()
    photo_1_actual_count = models.IntegerField()
    photo_1_agree = models.BooleanField(
        label="Do you agree with this count?",
        choices=[[True, 'Yes'], [False, 'No']],
        widget=widgets.RadioSelect,
    )
    photo_1_corrected_count = models.IntegerField(
        label="Your corrected count:",
        blank=True,
        min=0,
    )
    photo_1_time_spent = models.FloatField(blank=True)
    photo_1_active_time = models.FloatField(blank=True)
    photo_1_image_focus_time = models.FloatField(blank=True)
    photo_1_zoom_opened = models.BooleanField(initial=False)
    photo_1_zoom_count = models.IntegerField(initial=0)
    photo_1_recount_started = models.BooleanField(initial=False)

    # ── Photo 2 ──────────────────────────────────────────────────────
    photo_2_displayed_count = models.IntegerField()
    photo_2_actual_count = models.IntegerField()
    photo_2_agree = models.BooleanField(
        label="Do you agree with this count?",
        choices=[[True, 'Yes'], [False, 'No']],
        widget=widgets.RadioSelect,
    )
    photo_2_corrected_count = models.IntegerField(
        label="Your corrected count:",
        blank=True,
        min=0,
    )
    photo_2_time_spent = models.FloatField(blank=True)
    photo_2_active_time = models.FloatField(blank=True)
    photo_2_image_focus_time = models.FloatField(blank=True)
    photo_2_zoom_opened = models.BooleanField(initial=False)
    photo_2_zoom_count = models.IntegerField(initial=0)
    photo_2_recount_started = models.BooleanField(initial=False)

    # ── Photo 3 ──────────────────────────────────────────────────────
    photo_3_displayed_count = models.IntegerField()
    photo_3_actual_count = models.IntegerField()
    photo_3_agree = models.BooleanField(
        label="Do you agree with this count?",
        choices=[[True, 'Yes'], [False, 'No']],
        widget=widgets.RadioSelect,
    )
    photo_3_corrected_count = models.IntegerField(
        label="Your corrected count:",
        blank=True,
        min=0,
    )
    photo_3_time_spent = models.FloatField(blank=True)
    photo_3_active_time = models.FloatField(blank=True)
    photo_3_image_focus_time = models.FloatField(blank=True)
    photo_3_zoom_opened = models.BooleanField(initial=False)
    photo_3_zoom_count = models.IntegerField(initial=0)
    photo_3_recount_started = models.BooleanField(initial=False)

    # ── Photo 4 ──────────────────────────────────────────────────────
    photo_4_displayed_count = models.IntegerField()
    photo_4_actual_count = models.IntegerField()
    photo_4_agree = models.BooleanField(
        label="Do you agree with this count?",
        choices=[[True, 'Yes'], [False, 'No']],
        widget=widgets.RadioSelect,
    )
    photo_4_corrected_count = models.IntegerField(
        label="Your corrected count:",
        blank=True,
        min=0,
    )
    photo_4_time_spent = models.FloatField(blank=True)
    photo_4_active_time = models.FloatField(blank=True)
    photo_4_image_focus_time = models.FloatField(blank=True)
    photo_4_zoom_opened = models.BooleanField(initial=False)
    photo_4_zoom_count = models.IntegerField(initial=0)
    photo_4_recount_started = models.BooleanField(initial=False)

    # ── Post-task ────────────────────────────────────────────────────
    confidence = models.IntegerField(
        min=0, max=100,
        label="How confident are you that your review of the four photographs was thorough?",
    )
    overall_assessment = models.IntegerField(
        label="Based on your review, which statement best describes your overall assessment?",
        choices=[
            [1, 'The counts are reliable. No additional procedures are needed.'],
            [2, 'The counts are mostly reliable. Minor follow-up may be warranted.'],
            [3, 'The counts contain discrepancies. Additional procedures are required.'],
        ],
        widget=widgets.RadioSelect,
    )
    perceived_reliability = models.IntegerField(
        min=0, max=100,
        label="How reliable do you consider the preparer of these counts to be?",
    )

    # ── Computed properties ──────────────────────────────────────────

    def effective_count(self, i):
        agree = getattr(self, f'photo_{i}_agree')
        if agree:
            return getattr(self, f'photo_{i}_displayed_count')
        else:
            corrected = self.field_maybe_none(f'photo_{i}_corrected_count')
            return corrected if corrected is not None else getattr(self, f'photo_{i}_displayed_count')

    def photo_correct(self, i):
        return 1 if self.effective_count(i) == getattr(self, f'photo_{i}_actual_count') else 0

    def photo_abs_error(self, i):
        return abs(self.effective_count(i) - getattr(self, f'photo_{i}_actual_count'))

    def photo_signed_error(self, i):
        return self.effective_count(i) - getattr(self, f'photo_{i}_actual_count')

    def photo_accepted_incorrect(self, i):
        """1 if participant agreed but displayed != actual (relevant for photos 3,4)"""
        agree = getattr(self, f'photo_{i}_agree')
        displayed = getattr(self, f'photo_{i}_displayed_count')
        actual = getattr(self, f'photo_{i}_actual_count')
        return 1 if agree and displayed != actual else 0

    def photo_rejected_correct(self, i):
        """1 if participant disagreed but displayed == actual (relevant for photos 1,2)"""
        agree = getattr(self, f'photo_{i}_agree')
        displayed = getattr(self, f'photo_{i}_displayed_count')
        actual = getattr(self, f'photo_{i}_actual_count')
        return 1 if (not agree) and displayed == actual else 0

    @property
    def total_correct(self):
        return sum(self.photo_correct(i) for i in range(1, 5))

    @property
    def correct_error_detection(self):
        """Number of incorrect photos (3,4) correctly challenged AND corrected to actual"""
        count = 0
        for i in [3, 4]:
            if not getattr(self, f'photo_{i}_agree'):
                if self.effective_count(i) == getattr(self, f'photo_{i}_actual_count'):
                    count += 1
        return count

    @property
    def overreliance_score(self):
        """Number of incorrect counts accepted (photos 3,4 where agreed)"""
        return sum(self.photo_accepted_incorrect(i) for i in [3, 4])

    @property
    def underreliance_score(self):
        """Number of correct counts rejected (photos 1,2 where disagreed)"""
        return sum(self.photo_rejected_correct(i) for i in [1, 2])

    @property
    def mean_abs_error(self):
        return sum(self.photo_abs_error(i) for i in range(1, 5)) / 4

    # ── Aggregate time/engagement properties ─────────────────────────

    @property
    def total_time_spent(self):
        return sum(self.field_maybe_none(f'photo_{i}_time_spent') or 0 for i in range(1, 5))

    @property
    def total_active_time(self):
        return sum(self.field_maybe_none(f'photo_{i}_active_time') or 0 for i in range(1, 5))

    @property
    def total_image_focus_time(self):
        return sum(self.field_maybe_none(f'photo_{i}_image_focus_time') or 0 for i in range(1, 5))

    @property
    def total_zoom_count(self):
        return sum(self.field_maybe_none(f'photo_{i}_zoom_count') or 0 for i in range(1, 5))

    @property
    def any_zoom_opened(self):
        return any(getattr(self, f'photo_{i}_zoom_opened', False) for i in range(1, 5))


# ─── Helper: get label depending on condition ────────────────────────────────

def get_source_label(player, count):
    if player.condition == 'ai':
        return f"DroneCount AI count: {count}"
    else:
        return f"J. de Vries count: {count}"


# ─── Pages ───────────────────────────────────────────────────────────────────

class Welcome(Page):
    @staticmethod
    def vars_for_template(player: Player):
        player.participant.start_time = str(time.time())
        player.start_time = str(time.time())
        return dict(step=1, total_steps=8)


class SourceFraming(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            is_ai=player.condition == 'ai',
            step=2,
            total_steps=8,
        )


class PhotoReview1(Page):
    form_model = 'player'
    form_fields = [
        'photo_1_agree', 'photo_1_corrected_count',
        'photo_1_time_spent', 'photo_1_active_time', 'photo_1_image_focus_time',
        'photo_1_zoom_opened', 'photo_1_zoom_count', 'photo_1_recount_started',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            photo_num=1,
            photo_file='livestock_counting_review/' + PHOTO_DATA[1]['image'],
            displayed_count=PHOTO_DATA[1]['displayed'],
            source_label=get_source_label(player, PHOTO_DATA[1]['displayed']),
            step=3,
            total_steps=8,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.photo_1_agree:
            player.photo_1_corrected_count = None
        # Ensure defaults for process fields
        if player.field_maybe_none('photo_1_zoom_opened') is None:
            player.photo_1_zoom_opened = False
        if player.field_maybe_none('photo_1_zoom_count') is None:
            player.photo_1_zoom_count = 0
        if player.field_maybe_none('photo_1_recount_started') is None:
            player.photo_1_recount_started = False

    @staticmethod
    def error_message(player: Player, values):
        if values['photo_1_agree'] is False and not values.get('photo_1_corrected_count'):
            return 'Please enter your corrected count.'


class PhotoReview2(Page):
    form_model = 'player'
    form_fields = [
        'photo_2_agree', 'photo_2_corrected_count',
        'photo_2_time_spent', 'photo_2_active_time', 'photo_2_image_focus_time',
        'photo_2_zoom_opened', 'photo_2_zoom_count', 'photo_2_recount_started',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            photo_num=2,
            photo_file='livestock_counting_review/' + PHOTO_DATA[2]['image'],
            displayed_count=PHOTO_DATA[2]['displayed'],
            source_label=get_source_label(player, PHOTO_DATA[2]['displayed']),
            step=4,
            total_steps=8,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.photo_2_agree:
            player.photo_2_corrected_count = None
        if player.field_maybe_none('photo_2_zoom_opened') is None:
            player.photo_2_zoom_opened = False
        if player.field_maybe_none('photo_2_zoom_count') is None:
            player.photo_2_zoom_count = 0
        if player.field_maybe_none('photo_2_recount_started') is None:
            player.photo_2_recount_started = False

    @staticmethod
    def error_message(player: Player, values):
        if values['photo_2_agree'] is False and not values.get('photo_2_corrected_count'):
            return 'Please enter your corrected count.'


class PhotoReview3(Page):
    form_model = 'player'
    form_fields = [
        'photo_3_agree', 'photo_3_corrected_count',
        'photo_3_time_spent', 'photo_3_active_time', 'photo_3_image_focus_time',
        'photo_3_zoom_opened', 'photo_3_zoom_count', 'photo_3_recount_started',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            photo_num=3,
            photo_file='livestock_counting_review/' + PHOTO_DATA[3]['image'],
            displayed_count=PHOTO_DATA[3]['displayed'],
            source_label=get_source_label(player, PHOTO_DATA[3]['displayed']),
            step=5,
            total_steps=8,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.photo_3_agree:
            player.photo_3_corrected_count = None
        if player.field_maybe_none('photo_3_zoom_opened') is None:
            player.photo_3_zoom_opened = False
        if player.field_maybe_none('photo_3_zoom_count') is None:
            player.photo_3_zoom_count = 0
        if player.field_maybe_none('photo_3_recount_started') is None:
            player.photo_3_recount_started = False

    @staticmethod
    def error_message(player: Player, values):
        if values['photo_3_agree'] is False and not values.get('photo_3_corrected_count'):
            return 'Please enter your corrected count.'


class PhotoReview4(Page):
    form_model = 'player'
    form_fields = [
        'photo_4_agree', 'photo_4_corrected_count',
        'photo_4_time_spent', 'photo_4_active_time', 'photo_4_image_focus_time',
        'photo_4_zoom_opened', 'photo_4_zoom_count', 'photo_4_recount_started',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            photo_num=4,
            photo_file='livestock_counting_review/' + PHOTO_DATA[4]['image'],
            displayed_count=PHOTO_DATA[4]['displayed'],
            source_label=get_source_label(player, PHOTO_DATA[4]['displayed']),
            step=6,
            total_steps=8,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.photo_4_agree:
            player.photo_4_corrected_count = None
        if player.field_maybe_none('photo_4_zoom_opened') is None:
            player.photo_4_zoom_opened = False
        if player.field_maybe_none('photo_4_zoom_count') is None:
            player.photo_4_zoom_count = 0
        if player.field_maybe_none('photo_4_recount_started') is None:
            player.photo_4_recount_started = False

    @staticmethod
    def error_message(player: Player, values):
        if values['photo_4_agree'] is False and not values.get('photo_4_corrected_count'):
            return 'Please enter your corrected count.'


class PostReview(Page):
    form_model = 'player'
    form_fields = ['confidence', 'overall_assessment', 'perceived_reliability']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            is_ai=player.condition == 'ai',
            step=7,
            total_steps=8,
        )


# ─── Live results helper (used by Completion page) ──────────────────────────

def compute_live_results_payload(player):
    """Compute aggregate live results for the current session.
    Returns a JSON-safe dict with no participant-level identifiers.
    Used by Completion.live_method and Completion.js_vars."""
    players = player.subsession.get_players()

    completed = [
        p for p in players
        if p.field_maybe_none('confidence') is not None
        and p.field_maybe_none('overall_assessment') is not None
        and p.field_maybe_none('perceived_reliability') is not None
    ]

    in_progress = [
        p for p in players
        if p.field_maybe_none('condition') is not None
        and p not in completed
    ]

    ai_players = [p for p in completed if p.condition == 'ai']
    human_players = [p for p in completed if p.condition == 'human']
    ai_progress = [p for p in in_progress if p.condition == 'ai']
    human_progress = [p for p in in_progress if p.condition == 'human']

    def safe_mean(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else 0

    def pct(count, total):
        return count / total * 100 if total else 0

    def round_list(values, digits=1):
        return [round(v, digits) for v in values]

    def condition_payload(condition_players):
        n = len(condition_players)

        agree_pct = []
        correct_pct = []
        mean_photo_time = []
        mean_active_time = []
        mean_image_focus_time = []
        zoom_open_pct = []
        mean_zoom_count = []

        for i in range(1, 5):
            agree_pct.append(
                pct(sum(1 for p in condition_players if getattr(p, f'photo_{i}_agree')), n)
            )
            correct_pct.append(
                pct(sum(1 for p in condition_players if p.photo_correct(i)), n)
            )
            mean_photo_time.append(
                safe_mean([p.field_maybe_none(f'photo_{i}_time_spent') for p in condition_players])
            )
            mean_active_time.append(
                safe_mean([p.field_maybe_none(f'photo_{i}_active_time') for p in condition_players])
            )
            mean_image_focus_time.append(
                safe_mean([p.field_maybe_none(f'photo_{i}_image_focus_time') for p in condition_players])
            )
            zoom_open_pct.append(
                pct(sum(1 for p in condition_players if getattr(p, f'photo_{i}_zoom_opened', False)), n)
            )
            mean_zoom_count.append(
                safe_mean([p.field_maybe_none(f'photo_{i}_zoom_count') or 0 for p in condition_players])
            )

        assessment_pct = []
        for value in [1, 2, 3]:
            assessment_pct.append(
                pct(sum(1 for p in condition_players if p.overall_assessment == value), n)
            )

        return dict(
            n=n,
            agree_pct=round_list(agree_pct),
            correct_pct=round_list(correct_pct),
            mean_photo_time=round_list(mean_photo_time),
            mean_active_time=round_list(mean_active_time),
            mean_image_focus_time=round_list(mean_image_focus_time),
            zoom_open_pct=round_list(zoom_open_pct),
            mean_zoom_count=round_list(mean_zoom_count),
            assessment_pct=round_list(assessment_pct),
            mean_confidence=round(safe_mean([p.confidence for p in condition_players]), 1),
            mean_reliability=round(safe_mean([p.perceived_reliability for p in condition_players]), 1),
            mean_total_correct=round(safe_mean([p.total_correct for p in condition_players]), 2),
            mean_overreliance=round(safe_mean([p.overreliance_score for p in condition_players]), 2),
            mean_underreliance=round(safe_mean([p.underreliance_score for p in condition_players]), 2),
            mean_abs_error=round(safe_mean([p.mean_abs_error for p in condition_players]), 2),
            mean_total_time=round(safe_mean([p.total_time_spent for p in condition_players]), 1),
            mean_total_active_time=round(safe_mean([p.total_active_time for p in condition_players]), 1),
            mean_total_image_focus_time=round(safe_mean([p.total_image_focus_time for p in condition_players]), 1),
            zoom_any_pct=round(
                pct(sum(1 for p in condition_players if p.any_zoom_opened), n),
                1
            ),
            mean_correct_error_detection=round(
                safe_mean([p.correct_error_detection for p in condition_players]), 2
            ),
        )

    all_payload = condition_payload(completed)
    ai_payload = condition_payload(ai_players)
    human_payload = condition_payload(human_players)

    return dict(
        session_code=player.session.code,
        n_completed=len(completed),
        n_in_progress=len(in_progress),
        n_completed_ai=len(ai_players),
        n_completed_human=len(human_players),
        n_in_progress_ai=len(ai_progress),
        n_in_progress_human=len(human_progress),

        agree_pct_all=all_payload['agree_pct'],
        agree_pct_ai=ai_payload['agree_pct'],
        agree_pct_human=human_payload['agree_pct'],

        correct_pct_all=all_payload['correct_pct'],
        correct_pct_ai=ai_payload['correct_pct'],
        correct_pct_human=human_payload['correct_pct'],

        assessment_pct_all=all_payload['assessment_pct'],
        assessment_pct_ai=ai_payload['assessment_pct'],
        assessment_pct_human=human_payload['assessment_pct'],

        mean_confidence_all=all_payload['mean_confidence'],
        mean_confidence_ai=ai_payload['mean_confidence'],
        mean_confidence_human=human_payload['mean_confidence'],

        mean_reliability_all=all_payload['mean_reliability'],
        mean_reliability_ai=ai_payload['mean_reliability'],
        mean_reliability_human=human_payload['mean_reliability'],

        mean_total_correct_all=all_payload['mean_total_correct'],
        mean_total_correct_ai=ai_payload['mean_total_correct'],
        mean_total_correct_human=human_payload['mean_total_correct'],

        mean_overreliance_all=all_payload['mean_overreliance'],
        mean_overreliance_ai=ai_payload['mean_overreliance'],
        mean_overreliance_human=human_payload['mean_overreliance'],

        mean_underreliance_all=all_payload['mean_underreliance'],
        mean_underreliance_ai=ai_payload['mean_underreliance'],
        mean_underreliance_human=human_payload['mean_underreliance'],

        mean_abs_error_all=all_payload['mean_abs_error'],
        mean_abs_error_ai=ai_payload['mean_abs_error'],
        mean_abs_error_human=human_payload['mean_abs_error'],

        mean_photo_time_all=all_payload['mean_photo_time'],
        mean_photo_time_ai=ai_payload['mean_photo_time'],
        mean_photo_time_human=human_payload['mean_photo_time'],

        mean_active_time_all=all_payload['mean_active_time'],
        mean_active_time_ai=ai_payload['mean_active_time'],
        mean_active_time_human=human_payload['mean_active_time'],

        mean_image_focus_time_all=all_payload['mean_image_focus_time'],
        mean_image_focus_time_ai=ai_payload['mean_image_focus_time'],
        mean_image_focus_time_human=human_payload['mean_image_focus_time'],

        zoom_open_pct_all=all_payload['zoom_open_pct'],
        zoom_open_pct_ai=ai_payload['zoom_open_pct'],
        zoom_open_pct_human=human_payload['zoom_open_pct'],

        mean_zoom_count_all=all_payload['mean_zoom_count'],
        mean_zoom_count_ai=ai_payload['mean_zoom_count'],
        mean_zoom_count_human=human_payload['mean_zoom_count'],

        mean_total_time_all=all_payload['mean_total_time'],
        mean_total_time_ai=ai_payload['mean_total_time'],
        mean_total_time_human=human_payload['mean_total_time'],

        mean_total_active_time_all=all_payload['mean_total_active_time'],
        mean_total_active_time_ai=ai_payload['mean_total_active_time'],
        mean_total_active_time_human=human_payload['mean_total_active_time'],

        mean_total_image_focus_time_all=all_payload['mean_total_image_focus_time'],
        mean_total_image_focus_time_ai=ai_payload['mean_total_image_focus_time'],
        mean_total_image_focus_time_human=human_payload['mean_total_image_focus_time'],

        zoom_any_pct_all=all_payload['zoom_any_pct'],
        zoom_any_pct_ai=ai_payload['zoom_any_pct'],
        zoom_any_pct_human=human_payload['zoom_any_pct'],

        mean_correct_error_detection_all=all_payload['mean_correct_error_detection'],
        mean_correct_error_detection_ai=ai_payload['mean_correct_error_detection'],
        mean_correct_error_detection_human=human_payload['mean_correct_error_detection'],

        # No facilitator involvement. Always true on participant page.
        answers_released=True,
    )


class Completion(Page):
    """Automatic live results page — no facilitator involvement."""

    @staticmethod
    def vars_for_template(player: Player):
        player.end_time = str(time.time())
        return dict(
            step=8,
            total_steps=8,
            is_ai=player.condition == 'ai',
            session_code=player.session.code,
        )

    @staticmethod
    def js_vars(player: Player):
        return dict(
            initial_results=compute_live_results_payload(player)
        )

    @staticmethod
    def live_method(player: Player, data):
        payload = compute_live_results_payload(player)
        return {player.id_in_group: payload}


page_sequence = [
    Welcome,
    SourceFraming,
    PhotoReview1,
    PhotoReview2,
    PhotoReview3,
    PhotoReview4,
    PostReview,
    Completion,
]


# ─── Custom Export ───────────────────────────────────────────────────────────

def custom_export(players):
    """Export all data including computed fields."""
    header = [
        'session_code', 'participant_id', 'participant_code', 'condition',
        'start_time', 'end_time',
    ]
    for i in range(1, 5):
        header.extend([
            f'photo_{i}_displayed_count', f'photo_{i}_actual_count', f'photo_{i}_agree',
            f'photo_{i}_corrected_count', f'photo_{i}_effective_count',
            f'photo_{i}_correct', f'photo_{i}_abs_error', f'photo_{i}_signed_error',
            f'photo_{i}_accepted_incorrect', f'photo_{i}_rejected_correct',
            f'photo_{i}_time_spent', f'photo_{i}_active_time', f'photo_{i}_image_focus_time',
            f'photo_{i}_zoom_opened', f'photo_{i}_zoom_count', f'photo_{i}_recount_started',
        ])
    header.extend([
        'total_correct', 'correct_error_detection', 'overreliance_score',
        'underreliance_score', 'mean_abs_error',
        'total_time_spent', 'total_active_time', 'total_image_focus_time',
        'total_zoom_count', 'any_zoom_opened',
        'confidence', 'overall_assessment', 'perceived_reliability',
    ])
    yield header

    for p in players:
        # Skip incomplete
        if p.field_maybe_none('photo_1_agree') is None:
            continue
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
        yield row
