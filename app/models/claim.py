from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
from datetime import datetime

class Claim(BaseModel):
    claim_id: str = Field(..., json_schema_extra={"example": "CLM-10029"})
    provider_npi: str = Field(..., json_schema_extra={"example": "1999999999"})
    provider_name: Optional[str] = Field(None, json_schema_extra={"example": "Dr. Synthetic-A"})
    member_id: str = Field(..., json_schema_extra={"example": "MEM-44012"})
    facility_id: Optional[str] = Field(None, json_schema_extra={"example": "FAC-0012"})
    cpt_code: str = Field(..., json_schema_extra={"example": "99214"})
    claim_amount: float = Field(..., json_schema_extra={"example": 450.00})
    timestamp: datetime = Field(default_factory=datetime.now)
    location: str = Field(..., json_schema_extra={"example": "Chennai"})
    diagnosis_code: Optional[str] = Field("R05", json_schema_extra={"example": "R05"})
    fraud_flag: Optional[str] = Field("CLEAN", json_schema_extra={"example": "PHANTOM_BILLING"})

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Coerce fields that pandas might parse as int/float to string
            for key in ["claim_id", "provider_npi", "member_id", "facility_id", "cpt_code", "diagnosis_code", "fraud_flag"]:
                if key in values and values[key] is not None and not isinstance(values[key], str):
                    values[key] = str(values[key])

            # Alias location_city -> location if location not provided
            if "location_city" in values and "location" not in values:
                values["location"] = str(values["location_city"])
            elif "location" in values and "location_city" not in values:
                values["location_city"] = str(values["location"])

            # Alias claim_timestamp -> timestamp
            if "claim_timestamp" in values and "timestamp" not in values:
                raw_ts = values["claim_timestamp"]
                if isinstance(raw_ts, str):
                    values["timestamp"] = datetime.fromisoformat(raw_ts)
                else:
                    values["timestamp"] = raw_ts
            elif "timestamp" in values and isinstance(values["timestamp"], str):
                values["timestamp"] = datetime.fromisoformat(values["timestamp"])
        return values
