import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

from app.state import state, CurveType
from app.curves import get_volume, RAMP_SECONDS

scheduler = BackgroundScheduler()
scheduler.start()

_audio_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _audio_loop():
    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.music.load("app/assets/birds.wav")
        pygame.mixer.music.play(loops=-1)
    except Exception as e:
        print(f"[audio] Failed to init pygame: {e}")
        return

    start_time = time.monotonic()

    while not _stop_event.is_set():
        elapsed = time.monotonic() - start_time
        volume = get_volume(elapsed, state.curve.value)
        state.current_volume = volume

        try:
            import pygame
            pygame.mixer.music.set_volume(volume)
        except Exception as e:
            print(f"[audio] Volume set error: {e}")

        print(f"[audio] elapsed={int(elapsed)}s  volume={volume}  curve={state.curve.value}")
        time.sleep(10)

    try:
        import pygame
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except Exception:
        pass

    state.is_running = False
    state.current_volume = 0.0
    print("[audio] Stopped.")


def start_alarm():
    global _audio_thread

    if state.is_running:
        print("[scheduler] Alarm already running, skipping.")
        return

    print("[scheduler] Starting alarm ramp.")
    state.is_running = True
    _stop_event.clear()

    _audio_thread = threading.Thread(target=_audio_loop, daemon=True)
    _audio_thread.start()


def stop_alarm():
    global _audio_thread

    _stop_event.set()

    if _audio_thread and _audio_thread.is_alive():
        _audio_thread.join(timeout=5)

    state.is_running = False
    state.current_volume = 0.0
    state.wake_time = None
    print("[scheduler] Alarm stopped by user.")


def schedule_alarm(wake_time: datetime, curve: CurveType):
    if state.job_id:
        try:
            scheduler.remove_job(state.job_id)
        except Exception:
            pass

    trigger_time = wake_time - timedelta(seconds=RAMP_SECONDS)
    job = scheduler.add_job(start_alarm, "date", run_date=trigger_time)

    state.wake_time = wake_time
    state.curve = curve
    state.job_id = job.id

    print(f"[scheduler] Alarm set for {wake_time}, ramp starts at {trigger_time}")