import os
import pandas as pd
from typing import List, Optional
from app.models.claim import Claim
from app.config import settings
from scripts.generate_claims import generate_synthetic_dataset

class DataService:
    def __init__(self):
        self.claims: List[Claim] = []
        self._is_loaded: bool = False

    def load_or_generate_dataset(self, num_claims: int = 5000) -> List[Claim]:
        csv_path = settings.CLAIMS_CSV
        if not os.path.exists(csv_path):
            print("Synthetic claims CSV not found. Generating synthetic dataset...")
            generate_synthetic_dataset(num_claims=num_claims, output_dir=settings.DATA_DIR)
        
        df = pd.read_csv(csv_path)
        claims = []
        for idx, row in df.iterrows():
            claim_dict = row.to_dict()
            try:
                claim = Claim.model_validate(claim_dict)
                claims.append(claim)
            except Exception as e:
                if idx == 0:
                    print(f"Error parsing row 0: {e}")
                continue

        self.claims = claims
        self._is_loaded = True
        print(f" DataService loaded {len(self.claims)} claims into memory from {csv_path}.")
        return self.claims

    def get_claims(self, limit: int = 100, skip: int = 0) -> List[Claim]:
        return self.claims[skip:skip + limit]

    def get_claim_by_id(self, claim_id: str) -> Optional[Claim]:
        for c in self.claims:
            if c.claim_id == claim_id:
                return c
        return None

    def add_claim(self, claim: Claim):
        self.claims.append(claim)

data_service = DataService()
