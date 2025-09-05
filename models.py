from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    role: str = "RIDER"
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    owns_car: bool = False

class Vehicle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    make: str
    model: str
    color: Optional[str] = None
    plate_number: Optional[str] = None
    photo_url: Optional[str] = None

class Ride(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="user.id")
    vehicle_id: int = Field(foreign_key="vehicle.id")
    origin: str
    destination: str
    departure_time: datetime
    seats_total: int
    seats_taken: int = 0
    notes: Optional[str] = None

class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ride_id: int = Field(foreign_key="ride.id")
    rider_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "CONFIRMED"
