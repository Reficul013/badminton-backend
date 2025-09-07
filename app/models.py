from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, UniqueConstraint

class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    role: str = "RIDER"
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    owns_car: bool = False
    bio: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Vehicle(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("owner_id", "license_plate"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    name: str
    model: str
    license_plate: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Ride(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_id: int = Field(foreign_key="user.id", index=True)
    vehicle_id: int = Field(foreign_key="vehicle.id", index=True)
    origin: str
    departure_time: datetime = Field(index=True)
    seats_total: int
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Reservation(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("ride_id", "rider_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    ride_id: int = Field(foreign_key="ride.id", index=True)
    rider_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "CONFIRMED"
    cancelled_at: Optional[datetime] = None
