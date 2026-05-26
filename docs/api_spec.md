# chirply-ai REST & WebSocket API Specification

This document details the API contracts between the **FastAPI backend** and **React + Vite frontend** services.

---

## 1. Detections API

### Get Detection Logs
Returns a paginated list of acoustic detections logged by the BirdNET pipeline.

* **Endpoint**: `GET /api/v1/detections`
* **Query Parameters**:
  * `limit` (int, default: 50): Number of records to return.
  * `offset` (int, default: 0): Pagination offset.
  * `min_confidence` (float, optional): Filter by minimum prediction confidence (0.0 to 1.0).
  * `species` (string, optional): Filter by species common name or scientific name.
* **Response (200 OK)**:
```json
{
  "total": 124,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "id": "det_839f3c92",
      "timestamp": "2026-05-26T16:45:02.124Z",
      "species_scientific": "Cyanocitta cristata",
      "species_common": "Blue Jay",
      "confidence": 0.89,
      "audio_file": "rec_20260526_164500.wav",
      "spectrogram_file": "spec_20260526_164500.png",
      "location": {
        "lat": 37.7749,
        "lng": -122.4194
      }
    }
  ]
}
```

### Get Single Detection Details
* **Endpoint**: `GET /api/v1/detections/{id}`
* **Response (200 OK)**:
```json
{
  "id": "det_839f3c92",
  "timestamp": "2026-05-26T16:45:02.124Z",
  "species_scientific": "Cyanocitta cristata",
  "species_common": "Blue Jay",
  "confidence": 0.89,
  "audio_duration_seconds": 3.0,
  "audio_url": "/api/v1/recordings/rec_20260526_164500.wav",
  "spectrogram_url": "/api/v1/spectrograms/spec_20260526_164500.png",
  "meta": {
    "db_level_db": -24.5,
    "pi_temperature_celsius": 48.2
  }
}
```

---

## 2. System and Diagnostics API

### Get System Health
Retrieves local Raspberry Pi performance diagnostics to verify edge-node health.

* **Endpoint**: `GET /api/v1/system/status`
* **Response (200 OK)**:
```json
{
  "status": "healthy",
  "pipeline_active": true,
  "hardware": {
    "cpu_usage_percent": 14.5,
    "cpu_temperature_celsius": 47.8,
    "ram_used_mb": 412,
    "ram_total_mb": 2048,
    "disk_free_percent": 68.2
  },
  "microphone": {
    "device_name": "ReSpeaker 4-Mic Array (seeed-voicecard)",
    "input_level_db": -18.2
  }
}
```

---

## 3. Streaming (WebSocket) API

To support real-time audio dashboard rendering, the client opens a permanent WebSocket stream.

* **Endpoint**: `WS /api/v1/stream`
* **Message Payload (Server-to-Client)**:
  Every time BirdNET finishes an inference chunk or detects a trigger species:
```json
{
  "event": "detection",
  "data": {
    "id": "det_839f3f98",
    "timestamp": "2026-05-26T16:46:12.000Z",
    "species_common": "American Robin",
    "confidence": 0.94,
    "spectrogram_url": "/api/v1/spectrograms/spec_20260526_164600.png"
  }
}
```
Or periodic decibel checks to animate UI microphones:
```json
{
  "event": "mic_level",
  "data": {
    "db": -12.4
  }
}
```
