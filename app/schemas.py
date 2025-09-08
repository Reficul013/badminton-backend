# app/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    owns_car: Optional[bool] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

class UserRead(ORMModel):
    id: int
    name: str
    email: str
    role: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    owns_car: bool
    bio: Optional[str] = None
    phone: Optional[str] = None

class VehicleCreate(BaseModel):
    name: str
    model: str
    license_plate: Optional[str] = None
    photo_url: Optional[str] = None

class VehicleRead(ORMModel):
    id: int
    owner_id: int
    name: str
    model: str
    license_plate: Optional[str] = None
    photo_url: Optional[str] = None

class RideCreate(BaseModel):
    origin: str
    departure_time: datetime
    seats_total: int
    notes: Optional[str] = None

class RideRead(ORMModel):
    id: int
    host_id: int
    vehicle_id: int
    origin: str
    departure_time: datetime
    seats_total: int
    seats_taken: int
    notes: Optional[str] = None
    destination: str = "Rally"

class RideReadFull(RideRead):
    host_nickname: Optional[str] = None
    host_avatar_url: Optional[str] = None
    vehicle_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_photo_url: Optional[str] = None

class ReservationCreate(BaseModel):
    ride_id: int

class ReservationRead(ORMModel):
    id: int
    ride_id: int
    rider_id: int
    created_at: datetime
    status: str
