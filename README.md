# alarm-app

# Build Command
### On the Pi (or cross-compile on x86 with buildx):
```
docker compose up --build -d
```

### Set an alarm (wake time in HH:MM, 24-hour local time)
```
curl -X POST http://localhost:8000/alarm/set \
  -H "Content-Type: application/json" \
  -d '{"wake_time": "07:30", "curve": "linear"}'
```

### Check status
```
curl http://localhost:8000/alarm/status
```

### Stop the alarm
```
curl -X DELETE http://localhost:8000/alarm/stop
```