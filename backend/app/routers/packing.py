"""Packing-list route.

owner: ML/Engine

GET /packing-list?start_date&end_date[&lat&lon] — weather + duration aware,
built on the same "clean, tagged" garment eligibility rotation.py's daily
outfit uses, and the same lat/lon-optional-with-a-default-city convention
outfits.py's daily/generate endpoints use. See services/packing.py for the
actual algorithm.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.garment import Garment
from app.models.user import User

# Reuses garments.py's own key->presigned-URL serialization rather than
# duplicating it — a packing list's garments are the same objects the
# wardrobe grid shows, just a different selection of them.
from app.routers.garments import _garment_out
from app.schemas.packing import PackingCategoryOut, PackingListOut, TripWeatherOut
from app.services import weather as weather_service
from app.services.packing import PackableGarment, generate_packing_list

router = APIRouter(prefix="/packing-list", tags=["packing"])

# A trip longer than this is almost certainly a bad query (typo'd year, swapped
# dates) rather than a real ask — reject it outright instead of quietly
# generating a list for a multi-year "trip".
_MAX_TRIP_DAYS = 60


@router.get("", response_model=PackingListOut)
def get_packing_list(
    start_date: date = Query(...),
    end_date: date = Query(...),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PackingListOut:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must not be before start_date"
        )
    num_days = (end_date - start_date).days + 1
    if num_days > _MAX_TRIP_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trip is too long ({num_days} days) — max is {_MAX_TRIP_DAYS}.",
        )

    garments = (
        db.query(Garment)
        .filter(Garment.user_id == current_user.id, Garment.state == "clean")
        .all()
    )
    garments = [g for g in garments if g.category is not None]
    if not garments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough tagged, clean garments to build a packing list yet.",
        )

    forecast = weather_service.get_forecast(
        lat if lat is not None else settings.DEFAULT_LAT,
        lon if lon is not None else settings.DEFAULT_LON,
    )
    packable = [
        PackableGarment(id=g.id, category=g.category, wear_count=g.wear_count) for g in garments
    ]
    result = generate_packing_list(packable, num_days, forecast, start_date, end_date)

    garments_by_id = {g.id: g for g in garments}
    return PackingListOut(
        start_date=start_date,
        end_date=end_date,
        num_days=result.num_days,
        weather=TripWeatherOut(
            temp_min_c=result.weather.temp_min_c,
            temp_max_c=result.weather.temp_max_c,
            rain=result.weather.rain,
            days_with_forecast=result.weather.days_with_forecast,
        ),
        needs_outerwear=result.needs_outerwear,
        needs_rain_gear=result.needs_rain_gear,
        categories=[
            PackingCategoryOut(
                category=c.category,
                garments=[_garment_out(garments_by_id[gid]) for gid in c.garment_ids],
                short_by=c.short_by,
            )
            for c in result.categories
        ],
    )
