import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from app.curves import RAMP_SECONDS

from app.state import state, CurveType
from app.scheduler import schedule_alarm, stop_alarm

app = FastAPI(title="Nature Alarm", version="0.1.0")


class AlarmRequest(BaseModel):
    wake_time: str
    curve: CurveType = CurveType.linear


class AlarmResponse(BaseModel):
    message: str
    wake_time: str
    curve: str
    ramp_starts_at: str


class StatusResponse(BaseModel):
    is_running: bool
    wake_time: Optional[str]
    curve: str
    current_volume: float


@app.post("/alarm/set", response_model=AlarmResponse)
def set_alarm(req: AlarmRequest):
    try:
        now = datetime.now().astimezone()
        if not re.fullmatch(r"\d{2}:\d{2}", req.wake_time):
            raise HTTPException(status_code=400, detail="wake_time must be HH:MM format")
        wake = datetime.strptime(req.wake_time, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day,
            tzinfo=now.tzinfo
        )
        if wake <= now:
            wake += timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="wake_time must be HH:MM format")

    schedule_alarm(wake, req.curve)

    ramp_start = wake - timedelta(seconds=RAMP_SECONDS)

    return AlarmResponse(
        message="Alarm scheduled",
        wake_time=wake.strftime("%Y-%m-%d %H:%M"),
        curve=req.curve.value,
        ramp_starts_at=ramp_start.strftime("%Y-%m-%d %H:%M"),
    )


@app.delete("/alarm/stop")
def stop():
    if not state.is_running and not state.wake_time:
        raise HTTPException(status_code=404, detail="No active alarm")
    stop_alarm()
    return {"message": "Alarm stopped"}


@app.get("/alarm/status", response_model=StatusResponse)
def get_status():
    return StatusResponse(
        is_running=state.is_running,
        wake_time=state.wake_time.strftime("%Y-%m-%d %H:%M") if state.wake_time else None,
        curve=state.curve.value,
        current_volume=state.current_volume,
    )