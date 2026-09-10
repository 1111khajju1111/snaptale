from pydantic import BaseModel, Field, constr
from typing import Optional

class PinSetupRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class PinVerifyRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class PinChangeRequest(BaseModel):
    current_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    new_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class AgeGateRequest(BaseModel):
    confirmed_age_eligible: bool = True
