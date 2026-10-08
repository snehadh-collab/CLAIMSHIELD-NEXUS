from datetime import timedelta
from typing import List
from app.models.schemas import Claim, RuleFlags

CPT_BASELINE_BENCHMARK = {
    "99213": 120.00,
    "99214": 180.00,
    "99215": 250.00
}

def evaluate_claim_rules(current_claim: Claim, recent_claims: List[Claim]) -> RuleFlags:
    flags = RuleFlags()
    reasons = []

    for previous in recent_claims:
        if previous.claim_id == current_claim.claim_id:
            continue

        # Rule 1: Duplicate Billing (< 5 minutes)
        if (
            previous.member_id == current_claim.member_id
            and previous.provider_npi == current_claim.provider_npi
            and previous.cpt_code == current_claim.cpt_code
            and abs((current_claim.timestamp - previous.timestamp).total_seconds()) < 300
        ):
            flags.is_duplicate = True
            reasons.append(f"Duplicate billing detected against Claim {previous.claim_id}")

        # Rule 2: Impossible Geography (< 2 hours across locations)
        if (
            previous.member_id == current_claim.member_id
            and previous.location != current_claim.location
            and abs((current_claim.timestamp - previous.timestamp).total_seconds()) < 7200
        ):
            flags.impossible_geography = True
            mins = int(abs((current_claim.timestamp - previous.timestamp).total_seconds()) / 60)
            reasons.append(f"Impossible travel between {previous.location} and {current_claim.location} within {mins} mins")

    # Rule 3: Upcoding Anomaly (4x over benchmark)
    baseline_price = CPT_BASELINE_BENCHMARK.get(current_claim.cpt_code, 150.00)
    if current_claim.claim_amount >= (baseline_price * 4.0):
        flags.upcoding_anomaly = True
        reasons.append(f"Claim amount ${current_claim.claim_amount:.2f} is >= 4x benchmark (${baseline_price:.2f})")

    flags.flag_reasons = list(set(reasons))
    flags.flag_count = sum([flags.is_duplicate, flags.impossible_geography, flags.upcoding_anomaly])
    return flags