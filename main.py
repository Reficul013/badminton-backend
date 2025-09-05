import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# -------------------------
# In-memory “DB” (MVP only)
# -------------------------
_users = {}         # id -> user
_vehicles = {}      # id -> vehicle
_rides = {}         # id -> ride
_reservations = {}  # id -> reservation

_next_ids = {"user": 1, "vehicle": 1, "ride": 1, "reservation": 1}

def _next(kind: str) -> int:
    _next_ids[kind] += 1
    return _next_ids[kind] - 1

# -------------------------
# Schemas (Pydantic)
# -------------------------
class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "RIDER"
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    owns_car: bool = False

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    owns_car: Optional[bool] = None

class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    owns_car: bool = False

class VehicleCreate(BaseModel):
    make: str
    model: str
    color: Optional[str] = None
    plate_number: Optional[str] = None
    photo_url: Optional[str] = None

class VehicleRead(BaseModel):
    id: int
    owner_id: int
    make: str
    model: str
    color: Optional[str] = None
    plate_number: Optional[str] = None
    photo_url: Optional[str] = None

class RideCreate(BaseModel):
    origin: str
    destination: str
    departure_time: datetime
    seats_total: int
    notes: Optional[str] = None

class RideRead(BaseModel):
    id: int
    host_id: int
    vehicle_id: int
    origin: str
    destination: str
    departure_time: datetime
    seats_total: int
    seats_taken: int
    notes: Optional[str] = None

class RideReadFull(RideRead):
    host_nickname: Optional[str] = None
    host_avatar_url: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_color: Optional[str] = None
    vehicle_photo_url: Optional[str] = None

class ReservationCreate(BaseModel):
    ride_id: int

class ReservationRead(BaseModel):
    id: int
    ride_id: int
    rider_id: int
    created_at: datetime
    status: str = "CONFIRMED"

# -------------------------
# Helpers
# -------------------------
def get_current_user_id(request: Request) -> int:
    # TEMP auth stub (will swap for Keycloak later)
    uid = request.headers.get("X-User-Id")
    if not uid:
        raise HTTPException(401, "Missing X-User-Id header (temp auth)")
    try:
        return int(uid)
    except ValueError:
        raise HTTPException(400, "Invalid X-User-Id")

def ensure_static(app: FastAPI):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# -------------------------
# App factory
# -------------------------
def get_app() -> FastAPI:
    app = FastAPI(title="Rides to Rally API", version="0.2.0")

    origins = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ensure_static(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # -------------------------
    # Users
    # -------------------------
    @app.post("/api/users", response_model=UserRead)
    def create_user(payload: UserCreate):
        uid = _next("user")
        user = {"id": uid, **payload.model_dump()}
        _users[uid] = user
        return user

    @app.get("/api/users", response_model=List[UserRead])
    def list_users():
        return list(_users.values())

    @app.get("/api/users/me", response_model=UserRead)
    def me(request: Request):
        uid = get_current_user_id(request)
        user = _users.get(uid)
        if not user:
            # auto-create a basic user for dev convenience
            user = {"id": uid, "name": f"User {uid}", "email": f"user{uid}@example.com", "role": "RIDER",
                    "avatar_url": None, "nickname": None, "owns_car": False}
            _users[uid] = user
        return user

    @app.patch("/api/users/{user_id}", response_model=UserRead)
    def update_user(user_id: int, payload: UserUpdate, request: Request):
        uid = get_current_user_id(request)
        if uid != user_id:
            raise HTTPException(403, "You can only update your own profile")
        user = _users.get(user_id)
        if not user:
            raise HTTPException(404, "User not found")
        data = payload.model_dump(exclude_unset=True)
        user.update(data)
        return user

    # -------------------------
    # Vehicles
    # -------------------------
    @app.get("/api/vehicles", response_model=List[VehicleRead])
    def list_vehicles():
        return list(_vehicles.values())

    @app.post("/api/vehicles", response_model=VehicleRead)
    def create_vehicle(payload: VehicleCreate, request: Request):
        owner_id = get_current_user_id(request)
        vid = _next("vehicle")
        vehicle = {"id": vid, "owner_id": owner_id, **payload.model_dump()}
        _vehicles[vid] = vehicle
        return vehicle

    # -------------------------
    # Rides
    # -------------------------
    @app.get("/api/rides", response_model=List[RideReadFull])
    def list_rides():
        out: List[RideReadFull] = []
        for r in _rides.values():
            host = _users.get(r["host_id"])
            veh = _vehicles.get(r["vehicle_id"])
            out.append(RideReadFull(
                **r,
                host_nickname=host.get("nickname") if host else None,
                host_avatar_url=host.get("avatar_url") if host else None,
                vehicle_make=veh.get("make") if veh else None,
                vehicle_model=veh.get("model") if veh else None,
                vehicle_color=veh.get("color") if veh else None,
                vehicle_photo_url=veh.get("photo_url") if veh else None,
            ))
        # sort by departure
        out.sort(key=lambda x: x.departure_time)
        return out

    @app.post("/api/rides", response_model=RideRead)
    def create_ride(payload: RideCreate, request: Request):
        host_id = get_current_user_id(request)
        host = _users.get(host_id)
        if not host:
            raise HTTPException(404, "Host not found")
        if not host.get("owns_car"):
            raise HTTPException(400, "Set 'I own a car' in your profile to host")

        # pick the first vehicle for this owner
        my_vehicles = [v for v in _vehicles.values() if v["owner_id"] == host_id]
        if not my_vehicles:
            raise HTTPException(400, "Add your car in Profile before hosting")

        veh = my_vehicles[0]
        if payload.departure_time < datetime.utcnow():
            raise HTTPException(400, "Departure time must be in the future")

        rid = _next("ride")
        ride = {
            "id": rid,
            "host_id": host_id,
            "vehicle_id": veh["id"],
            "origin": payload.origin,
            "destination": payload.destination,
            "departure_time": payload.departure_time,
            "seats_total": payload.seats_total,
            "seats_taken": 0,
            "notes": payload.notes,
        }
        _rides[rid] = ride
        return ride

    # -------------------------
    # Reservations
    # -------------------------
    @app.post("/api/reservations", response_model=ReservationRead)
    def reserve(payload: ReservationCreate, request: Request):
        rider_id = get_current_user_id(request)
        ride = _rides.get(payload.ride_id)
        if not ride:
            raise HTTPException(404, "Ride not found")
        if ride["seats_taken"] >= ride["seats_total"]:
            raise HTTPException(400, "Ride is full")
        # (no duplicate check in-memory; fine for demo)
        ride["seats_taken"] += 1
        res_id = _next("reservation")
        res = {
            "id": res_id,
            "ride_id": payload.ride_id,
            "rider_id": rider_id,
            "created_at": datetime.utcnow(),
            "status": "CONFIRMED",
        }
        _reservations[res_id] = res
        return res

    return app

app = get_app()
