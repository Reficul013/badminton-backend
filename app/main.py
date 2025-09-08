# app/main.py
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import func, select as sa_select
from sqlalchemy.exc import IntegrityError

from sqlmodel import Session, select as sql_select

from .database import init_db, get_session
from .auth import get_current_user_id
from . import models as m
from . import schemas as s

APP_VERSION = "0.5.1"

def create_app() -> FastAPI:
    app = FastAPI(title="Rides to Rally API", version=APP_VERSION)

    # CORS
    origins = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    allow_origins = [o.strip() for o in origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # static (optional)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    def _startup():
        init_db()

    # ---------------- Health ----------------
    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": APP_VERSION}

    # ---------------- Users -----------------
    @app.get("/api/users/me", response_model=s.UserRead)
    def me(
        user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
    ):
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        # validate to Pydantic explicitly
        return s.UserRead.model_validate(user)

    @app.patch("/api/users/{user_id}", response_model=s.UserRead)
    def update_user(
        user_id: int,
        payload: s.UserUpdate,
        current_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
    ):
        if current_id != user_id:
            raise HTTPException(403, "You can only update your own profile")
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(user, k, v)
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)
        return s.UserRead.model_validate(user)

    # --------------- Vehicles ---------------
    @app.get("/api/vehicles", response_model=List[s.VehicleRead])
    def list_vehicles(
        session: Session = Depends(get_session),
        user_id: int = Depends(get_current_user_id),  # auth + scope
    ):
        # Use SQLModel.select for clean ORM objects
        rows = session.exec(
            sql_select(m.Vehicle).where(m.Vehicle.owner_id == user_id)
        ).all()
        # Return strictly-validated Pydantic models
        return [s.VehicleRead.model_validate(v) for v in rows]

    @app.post("/api/vehicles", response_model=s.VehicleRead, status_code=201)
    def create_vehicle(
        payload: s.VehicleCreate,
        user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
    ):
        v = m.Vehicle(owner_id=user_id, **payload.model_dump())
        session.add(v)
        session.commit()
        session.refresh(v)
        return s.VehicleRead.model_validate(v)

    # ---------------- Rides -----------------
    @app.get("/api/rides", response_model=List[s.RideReadFull])
    def list_rides(session: Session = Depends(get_session)):
        rides = session.exec(sa_select(m.Ride)).all()
        out: List[s.RideReadFull] = []
        for r in rides:
            taken = session.exec(
                sa_select(func.count(m.Reservation.id)).where(
                    (m.Reservation.ride_id == r.id) &
                    (m.Reservation.status == "CONFIRMED")
                )
            ).scalar_one() or 0

            host = session.get(m.User, r.host_id)
            veh  = session.get(m.Vehicle, r.vehicle_id)

            out.append(s.RideReadFull(
                id=r.id,
                host_id=r.host_id,
                vehicle_id=r.vehicle_id,
                origin=r.origin,
                departure_time=r.departure_time,
                seats_total=r.seats_total,
                seats_taken=int(taken),
                notes=r.notes,
                destination="Rally",
                host_nickname=host.nickname if host else None,
                host_avatar_url=host.avatar_url if host else None,
                vehicle_name=veh.name if veh else None,
                vehicle_model=veh.model if veh else None,
                vehicle_photo_url=veh.photo_url if veh else None,
            ))
        out.sort(key=lambda x: x.departure_time)
        return out

    @app.post("/api/rides", response_model=s.RideRead)
    def create_ride(
        payload: s.RideCreate,
        user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
    ):
        host = session.get(m.User, user_id)
        if not host:
            raise HTTPException(404, "Host not found")
        if not host.owns_car:
            raise HTTPException(400, "Set 'I own a car' in your profile to host")

        my_vehicles = session.exec(
            sql_select(m.Vehicle).where(m.Vehicle.owner_id == user_id)
        ).all()
        if not my_vehicles:
            raise HTTPException(400, "Add your car in Profile before hosting")

        veh = my_vehicles[0]
        if payload.departure_time < datetime.utcnow():
            raise HTTPException(400, "Departure time must be in the future")

        ride = m.Ride(
            host_id=user_id,
            vehicle_id=veh.id,
            origin=payload.origin,
            departure_time=payload.departure_time,
            seats_total=payload.seats_total,
            notes=payload.notes,
        )
        session.add(ride)
        session.commit()
        session.refresh(ride)

        return s.RideRead(
            id=ride.id,
            host_id=ride.host_id,
            vehicle_id=ride.vehicle_id,
            origin=ride.origin,
            departure_time=ride.departure_time,
            seats_total=ride.seats_total,
            seats_taken=0,
            notes=ride.notes,
            destination="Rally",
        )

    # ------------- Reservations -------------
    @app.post("/api/reservations", response_model=s.ReservationRead)
    def reserve(
        payload: s.ReservationCreate,
        user_id: int = Depends(get_current_user_id),
        session: Session = Depends(get_session),
    ):
        ride = session.exec(
            sql_select(m.Ride).where(m.Ride.id == payload.ride_id).with_for_update()
        ).one_or_none()
        if not ride:
            raise HTTPException(404, "Ride not found")

        if ride.host_id == user_id:
            raise HTTPException(400, "Host cannot reserve own ride")

        taken = session.exec(
            sa_select(func.count(m.Reservation.id)).where(
                (m.Reservation.ride_id == ride.id) &
                (m.Reservation.status == "CONFIRMED")
            )
        ).scalar_one() or 0
        if int(taken) >= ride.seats_total:
            raise HTTPException(400, "Ride is full")

        res = m.Reservation(ride_id=ride.id, rider_id=user_id, status="CONFIRMED")
        session.add(res)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(400, "You already reserved a seat on this ride")

        session.refresh(res)
        return s.ReservationRead.model_validate(res)

    return app

app = create_app()
