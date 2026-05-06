from ninja import Router
from .security import SessionOrServiceAuth

from .api_plans import router as plans_router
from .api_system import router as system_router
from .api_auth import router as auth_router
from .api_tenants import router as tenants_router

router = Router(auth=SessionOrServiceAuth())

# Add sub-routers
router.add_router("/", plans_router)
router.add_router("/", system_router)
router.add_router("/", auth_router)
router.add_router("/", tenants_router)
