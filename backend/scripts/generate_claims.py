import os
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd

fake = Faker()
Faker.seed(42)
random.seed(42)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")


def generate_synthetic_dataset(num_claims=5000, output_dir=None):
    # 1. Generate Entities
    providers = [
        {
            "provider_npi": f"1{i:09d}",
            "provider_name": f"Dr. {fake.name()}",
            "specialty": random.choice(
                ["Cardiology", "Orthopedics", "General Practice", "Radiology"]
            ),
            "primary_city": "Chennai",
        }
        for i in range(200)
    ]

    members = [
        {
            "member_id": f"MEM{i:06d}",
            "member_name": fake.name(),
            "age": random.randint(18, 85),
            "gender": random.choice(["M", "F"]),
        }
        for i in range(1000)
    ]

    facilities = [
        {
            "facility_id": f"FAC{i:03d}",
            "facility_name": f"{fake.company()} Hospital",
            "city": random.choice(["Chennai", "Delhi", "Mumbai", "Bangalore"]),
        }
        for i in range(50)
    ]

    # Explicit Injected Fraud Entities
    phantom_doctor = {
        "provider_npi": "1999999999",
        "provider_name": "Dr. Synthetic-A (Phantom)",
        "specialty": "General Practice",
        "primary_city": "Chennai",
    }
    teleport_doctor = {
        "provider_npi": "1888888888",
        "provider_name": "Dr. Synthetic-B (Teleport)",
        "specialty": "Orthopedics",
        "primary_city": "Chennai",
    }
    upcode_doctor = {
        "provider_npi": "1777777777",
        "provider_name": "Dr. Synthetic-C (Upcoder)",
        "specialty": "Cardiology",
        "primary_city": "Mumbai",
    }

    providers.extend([phantom_doctor, teleport_doctor, upcode_doctor])

    claims = []
    base_time = datetime(2026, 1, 1, 9, 0, 0)

    # 2. Standard Legitimate Claims (~4,800)
    for _ in range(num_claims - 200):
        prov = random.choice(providers)
        mem = random.choice(members)
        fac = random.choice(facilities)
        claim_date = base_time + timedelta(
            days=random.randint(0, 180), hours=random.randint(0, 8)
        )

        cpt_code = random.choice(["99213", "99214", "99215", "71045", "93000"])
        base_amount = {
            "99213": 100,
            "99214": 150,
            "99215": 220,
            "71045": 80,
            "93000": 60,
        }[cpt_code]

        claims.append(
            {
                "claim_id": f"CLM-{random.getrandbits(32):08X}",
                "provider_npi": prov["provider_npi"],
                "provider_name": prov["provider_name"],
                "member_id": mem["member_id"],
                "facility_id": fac["facility_id"],
                "claim_timestamp": claim_date.isoformat(),
                "cpt_code": cpt_code,
                "claim_amount": round(base_amount * random.uniform(0.9, 1.1), 2),
                "location_city": prov["primary_city"],
                "fraud_flag": "CLEAN",
            }
        )

    # 3. Inject Fraud Pattern 1: Phantom Billing (Dr. Synthetic-A)
    for _ in range(60):
        claims.append(
            {
                "claim_id": f"CLM-PHANTOM-{random.getrandbits(24):06X}",
                "provider_npi": phantom_doctor["provider_npi"],
                "provider_name": phantom_doctor["provider_name"],
                "member_id": f"GHOST-MEM-{random.randint(9000, 9999)}",  # Non-existent/fake member ID ring
                "facility_id": random.choice(facilities)["facility_id"],
                "claim_timestamp": (
                    base_time + timedelta(days=random.randint(10, 50))
                ).isoformat(),
                "cpt_code": "99215",
                "claim_amount": 450.00,
                "location_city": "Chennai",
                "fraud_flag": "PHANTOM_BILLING",
            }
        )

    # 4. Inject Fraud Pattern 2: Upcoding / Unbundling (Dr. Synthetic-C)
    for _ in range(70):
        claims.append(
            {
                "claim_id": f"CLM-UPCODE-{random.getrandbits(24):06X}",
                "provider_npi": upcode_doctor["provider_npi"],
                "provider_name": upcode_doctor["provider_name"],
                "member_id": random.choice(members)["member_id"],
                "facility_id": random.choice(facilities)["facility_id"],
                "claim_timestamp": (
                    base_time + timedelta(days=random.randint(50, 100))
                ).isoformat(),
                "cpt_code": "99215",
                "claim_amount": 1800.00,  # 4x peer baseline average
                "location_city": "Mumbai",
                "fraud_flag": "UPCODING",
            }
        )

    # 5. Inject Fraud Pattern 3: Impossible Geography (Dr. Synthetic-B)
    target_member = members[0]["member_id"]
    overlap_time = datetime(2026, 3, 15, 10, 0, 0)

    for i in range(10):
        # 10 claims in Chennai
        claims.append(
            {
                "claim_id": f"CLM-GEO-CHN-{i}",
                "provider_npi": teleport_doctor["provider_npi"],
                "provider_name": teleport_doctor["provider_name"],
                "member_id": target_member,
                "facility_id": "FAC001",
                "claim_timestamp": (
                    overlap_time + timedelta(minutes=i * 2)
                ).isoformat(),
                "cpt_code": "99214",
                "claim_amount": 300.00,
                "location_city": "Chennai",
                "fraud_flag": "IMPOSSIBLE_GEOGRAPHY",
            }
        )
        # 10 claims in Delhi within 1 hour window
        claims.append(
            {
                "claim_id": f"CLM-GEO-DEL-{i}",
                "provider_npi": teleport_doctor["provider_npi"],
                "provider_name": teleport_doctor["provider_name"],
                "member_id": target_member,
                "facility_id": "FAC002",
                "claim_timestamp": (
                    overlap_time + timedelta(minutes=30 + i * 2)
                ).isoformat(),
                "cpt_code": "99214",
                "claim_amount": 300.00,
                "location_city": "Delhi",
                "fraud_flag": "IMPOSSIBLE_GEOGRAPHY",
            }
        )

    df_claims = pd.DataFrame(claims)

    target_dir = output_dir if output_dir else DATA_DIR
    os.makedirs(target_dir, exist_ok=True)

    csv_path = os.path.join(target_dir, "synthetic_claims.csv")
    json_path = os.path.join(target_dir, "synthetic_claims.json")
    df_claims.to_csv(csv_path, index=False)
    df_claims.to_json(json_path, orient="records", indent=2)

    print(
        f" Successfully generated {len(df_claims)} synthetic claims to {csv_path} & {json_path}"
    )
    return df_claims


if __name__ == "__main__":
    generate_synthetic_dataset()
