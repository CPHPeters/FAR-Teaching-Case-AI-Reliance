from os import environ

# Register custom facilitator dashboard routes (optional — facilitator dashboard only)
try:
    import register_routes
except Exception as e:
    print(f'[facilitator] Dashboard middleware not loaded: {e}')

SESSION_CONFIGS = [
    dict(
        name='livestock_training_demo',
        display_name='Livestock Counting Review — Training Demo',
        app_sequence=['livestock_counting_review'],
        num_demo_participants=20,
    ),
    dict(
        name='livestock_training_ai_only',
        display_name='Livestock Counting Review — AI Only',
        app_sequence=['livestock_counting_review'],
        num_demo_participants=10,
        force_condition='ai',
    ),
    dict(
        name='livestock_training_human_only',
        display_name='Livestock Counting Review — Human Only',
        app_sequence=['livestock_counting_review'],
        num_demo_participants=10,
        force_condition='human',
    ),
    dict(
        name='livestock_training_test',
        display_name='Livestock Counting Review — Test',
        app_sequence=['livestock_counting_review'],
        num_demo_participants=4,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)

PARTICIPANT_FIELDS = ['condition', 'start_time']
SESSION_FIELDS = ['facilitator_password']

LANGUAGE_CODE = 'en'
ADMIN_USERNAME = environ.get('OTREE_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD', 'far2026admin')
SECRET_KEY = environ.get('OTREE_SECRET_KEY', 'far-livestock-training-2026')

ROOMS = [
    dict(
        name='training_room',
        display_name='FAR Training Room',
    ),
]
