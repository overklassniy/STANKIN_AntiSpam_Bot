"""
Маршруты веб-панели.
"""

from panel.routes.auth import router as auth_router
from panel.routes.spam import router as spam_router
from panel.routes.muted import router as muted_router
from panel.routes.settings import router as settings_router
from panel.routes.api import router as api_router

__all__ = [
    'auth_router',
    'spam_router',
    'muted_router',
    'settings_router',
    'api_router',
]
