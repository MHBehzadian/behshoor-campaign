from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import (
    auth,
    checkups,
    commissions,
    day_schedules,
    followups,
    fulfillments,
    pack_deliveries,
    regions,
    settings,
    shops,
    uploads,
    users,
)

app = FastAPI(title="Zanjan Campaign API")
app.mount("/uploads", StaticFiles(directory=str(uploads.UPLOAD_DIR)), name="uploads")

# TODO(phase 3): once the webapp has a real domain, replace "*" with it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    regions.router,
    day_schedules.router,
    shops.router,
    pack_deliveries.router,
    followups.router,
    fulfillments.router,
    checkups.router,
    settings.router,
    commissions.router,
    users.router,
    uploads.router,
):
    app.include_router(router)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
