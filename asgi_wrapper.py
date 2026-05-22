"""
ASGI wrapper that adds facilitator dashboard routes to the oTree app.
Used via: uvicorn asgi_wrapper:app
"""
from otree.asgi import app as otree_app
from register_routes import FacilitatorMiddleware

app = FacilitatorMiddleware(otree_app)
