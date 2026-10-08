from typing import List
from app.models.schemas import Claim, ExposureForecast

def calculate_provider_exposure(provider_npi: str, provider_claims: List[Claim]) -> ExposureForecast:
    """
    Calculates historical claim velocity and projects 30/60/90 day financial exposure.
    """
    if not provider_claims:
        return ExposureForecast(
            provider_npi=provider_npi,
            daily_velocity=0.0,
            historical_daily_avg_claim=0.0,
            day_30_exposure=0.0,
            day_60_exposure=0.0,
            day_90_exposure=0.0
        )

    total_billed = sum(c.claim_amount for c in provider_claims)
    timestamps = [c.timestamp for c in provider_claims]

    time_span_days = max((max(timestamps) - min(timestamps)).total_seconds() / 86400.0, 1.0)
    daily_velocity = total_billed / time_span_days

    return ExposureForecast(
        provider_npi=provider_npi,
        daily_velocity=round(daily_velocity, 2),
        historical_daily_avg_claim=round(daily_velocity, 2),
        day_30_exposure=round(daily_velocity * 30, 2),
        day_60_exposure=round(daily_velocity * 60, 2),
        day_90_exposure=round(daily_velocity * 90, 2)
    )