from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# ------------------------------------------------------------------
# Base class that works for both Pydantic v1 and v2
# ------------------------------------------------------------------
class ORMModel(BaseModel):
    # Pydantic v2
    model_config = {"from_attributes": True}
    # Pydantic v1
    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------
class UserUpdate(ORMModel):
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
    # If you want to expose these, uncomment:
    # created_at: datetime
    # updated_at: datetime


# ------------------------------------------------------------------
# Vehicles
# ------------------------------------------------------------------
class VehicleCreate(ORMModel):
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
    # created_at: datetime  # expose if you need it


# ------------------------------------------------------------------
# Rides (destination is presented by the API as "Rally"; not stored)
# ------------------------------------------------------------------
class RideCreate(ORMModel):
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
    seats_taken: int               # compute in the query/route
    notes: Optional[str] = None
    destination: str = "Rally"     # computed/presented field
    # created_at: datetime         # expose if you need it


class RideReadFull(RideRead):
    host_nickname: Optional[str] = None
    host_avatar_url: Optional[str] = None
    vehicle_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_photo_url: Optional[str] = None


# ------------------------------------------------------------------
# Reservations
# ------------------------------------------------------------------
class ReservationCreate(ORMModel):
    ride_id: int


class ReservationRead(ORMModel):
    id: int
    ride_id: int
    rider_id: int
    created_at: datetime
    status: str
