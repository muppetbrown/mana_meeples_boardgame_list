"""
API v1 router registration.
All v1 endpoints are defined here with the /api/v1 prefix.
"""
from fastapi import APIRouter

# Import all v1 routers (these are the existing routers with updated prefixes)
from api.routers import public, admin, bulk, health, buy_list, sleeves

# Create v1 main router
v1_router = APIRouter(prefix="/v1")

# Register all v1 sub-routers (without /api prefix as it's added by parent)
# Public endpoints
v1_public_router = APIRouter(prefix="/public", tags=["public-v1"])
v1_public_router.include_router(public.router, prefix="")

# Admin endpoints
v1_admin_router = APIRouter(prefix="/admin", tags=["admin-v1"])
v1_admin_router.include_router(admin.router, prefix="")
v1_admin_router.include_router(bulk.router, prefix="")
v1_admin_router.include_router(buy_list.router, prefix="/buy-list")
v1_admin_router.include_router(sleeves.router, prefix="/sleeves")

# Health/Debug endpoints (no versioning needed, but included for consistency)
v1_health_router = APIRouter(prefix="/health", tags=["health-v1"])
v1_debug_router = APIRouter(prefix="/debug", tags=["debug-v1"])
v1_health_router.include_router(health.health_router, prefix="")
v1_debug_router.include_router(health.debug_router, prefix="")

# Register all sub-routers to v1 main router
v1_router.include_router(v1_public_router)
v1_router.include_router(v1_admin_router)
v1_router.include_router(v1_health_router)
v1_router.include_router(v1_debug_router)
