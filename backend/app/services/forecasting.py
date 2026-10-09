from collections import defaultdict
from typing import List
from app.models.schemas import Claim, ExposureForecast, ForecastPoint

MIN_WINDOW_DAYS = 30.0


def calculate_provider_exposure(provider_npi: str, provider_claims: List[Claim]) -> ExposureForecast:
    """
    Projects 30/60/90 day billing exposure as a linear run-rate.

    daily rate = total billed / max(observed window, 30 days). The 30-day floor stops a burst of
    claims on one day from being extrapolated to a huge 90-day figure (audit D-17). This is a
    run-rate extrapolation, not a statistical forecast, and it carries no confidence interval.
    """
    if not provider_claims:
        return ExposureForecast(
            provider_npi=provider_npi,
            historical_daily_avg_claim=0.0,
            day_30_exposure=0.0,
            day_60_exposure=0.0,
            day_90_exposure=0.0,
        )

    total_billed = sum(c.claim_amount for c in provider_claims)
    timestamps = [c.timestamp for c in provider_claims]

    observed_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400.0
    window_days = max(observed_days, MIN_WINDOW_DAYS)
    daily_velocity = total_billed / window_days

    by_day = defaultdict(float)
    for c in provider_claims:
        by_day[c.timestamp.date().isoformat()] += c.claim_amount
    running = 0.0
    history = []
    for day in sorted(by_day):
        running += by_day[day]
        history.append(ForecastPoint(date=day, cumulative_billed=round(running, 2)))

    return ExposureForecast(
        provider_npi=provider_npi,
        historical_daily_avg_claim=round(daily_velocity, 2),
        day_30_exposure=round(daily_velocity * 30, 2),
        day_60_exposure=round(daily_velocity * 60, 2),
        day_90_exposure=round(daily_velocity * 90, 2),
        claim_count=len(provider_claims),
        total_billed=round(total_billed, 2),
        observed_days=round(observed_days, 2),
        window_days_used=round(window_days, 2),
        history=history,
    )
