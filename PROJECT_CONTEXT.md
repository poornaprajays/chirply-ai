# Chirply AI — Complete Project Context

> **Purpose of this document**: A single source of truth for the entire Chirply AI project.
> Any AI assistant, IDE, or developer reading this file should be able to understand
> exactly what this project is, what it does, and how every part connects — with zero
> assumptions and zero hallucinations.

---

## 1. What is Chirply AI?

**Chirply AI** is a real-time, edge-deployed bird species identification system.

It uses a **Raspberry Pi** equipped with a **ReSpeaker Microphone Array** to continuously
capture ambient audio from the environment. Each 3-second audio chunk is passed through
**BirdNET** — an open-source neural network acoustic classifier — which identifies bird
species present in the recording. Detected species, their confidence scores, associated
WAV audio clips, and Mel spectrogram images are logged to a local **SQLite database**.
A **FastAPI** backend exposes this data over a REST API. A **React + Vite frontend**
consumes these APIs to display a real-time bird sighting dashboard to the user.

### Core Purpose

- Automate passive wildlife acoustic monitoring using AI at the edge.
- Classify bird species from raw ambient audio in real time without cloud dependency.
- Store, visualize, and explore every detection event through a web dashboard.
- Run entirely on low-power, low-cost hardware (Raspberry Pi) — no internet or GPU required.

### Who Uses This

Nature researchers, birdwatchers, ecologists, and wildlife conservation projects that
want automated, 24/7 acoustic monitoring of a location without cloud infrastructure.

---

## 2. Project Directory Structure

```
chirply-ai/                          ← Project root
├── PROJECT_CONTEXT.md               ← This file (single source of truth)
├── README.md                        ← Quick overview and ASCII architecture diagram
├── .gitignore
│
├── backend/                         ← Python FastAPI backend (runs on Raspberry Pi)
│   ├── requirements.txt             ← All Python dependencies
│   ├── models/                      ← BirdNET TFLite model files (not tracked in git)
│   │   ├── model.tflite             ← Compiled BirdNET TFLite inference model
│   │   └── labels.txt               ← Species taxonomy label index (~6000 species)
│   └── app/
│       ├── main.py                  ← FastAPI app entrypoint, startup/shutdown lifecycle
│       ├── core/
│       │   └── config.py            ← Pydantic Settings class (all global configuration)
│       ├── api/
│       │   └── routes/
│       │       ├── health.py        ← GET /api/v1/health — system diagnostics
│       │       ├── detections.py    ← GET /api/v1/detections — detection history + file serving
│       │       └── stats.py         ← GET /api/v1/stats — analytics and storage summary
│       ├── services/
│       │   ├── audio_recorder.py    ← ALSA arecord wrapper for ReSpeaker audio capture
│       │   ├── birdnet_service.py   ← TFLite BirdNET model inference engine
│       │   ├── spectrogram_service.py ← Mel spectrogram PNG generator (librosa + matplotlib)
│       │   └── detection_logger.py  ← SQLite write/read service for detection events
│       ├── pipelines/
│       │   └── realtime_pipeline.py ← Background thread orchestrator (the core loop)
│       ├── schemas/
│       │   └── detection_schema.py  ← Pydantic request/response models for all APIs
│       └── utils/
│           └── file_utils.py        ← Directory management and storage rotation helpers
│
├── frontend/                        ← React + Vite dashboard (runs in browser)
│   ├── package.json                 ← npm dependencies (React 18, Vite, Lucide)
│   ├── public/                      ← Static public assets
│   └── src/
│       ├── components/              ← React UI components (bird cards, spectrograms, charts)
│       ├── services/                ← API client layer (fetch calls to FastAPI)
│       ├── types/                   ← TypeScript/JSDoc type definitions
│       └── assets/                  ← Images, icons, fonts
│
├── data/                            ← Runtime data storage (written to at runtime)
│   ├── recordings/                  ← WAV audio clips for detections (rec_YYYYMMDD_HHMMSS.wav)
│   ├── spectrograms/                ← Mel spectrogram PNG images (spec_YYYYMMDD_HHMMSS.png)
│   └── detections/                  ← SQLite database file (chirply.db)
│
└── docs/
    ├── api_spec.md                  ← REST API contract documentation
    └── hardware_setup.md            ← ReSpeaker HAT wiring, ALSA config, driver install guide
```

---

## 3. Full Technology Stack

### 3.1 Hardware

| Component | Model | Role |
|---|---|---|
| Edge Computer | **Raspberry Pi** (any model with GPIO) | Hosts the entire backend: audio capture, ML inference, database, API server |
| Microphone | **ReSpeaker Mic Array HAT** (Seeed Studio — 2-Mic, 4-Mic, or 6-Mic Circular Array) | Captures ambient audio from the environment |
| Storage | **MicroSD card or external USB SSD** | Stores WAV recordings, spectrogram PNGs, and the SQLite database |

**Hardware interface**: The ReSpeaker HAT mounts directly onto the Raspberry Pi's 40-pin GPIO header. Audio is routed through the **ALSA (Advanced Linux Sound Architecture)** subsystem using the `seeed-voicecard` kernel driver. The device is accessible as `plughw:1,0` inside the application.

---

### 3.2 Backend — Python (runs on Raspberry Pi)

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core runtime language |
| **FastAPI** | ≥ 0.109.0 | REST API web framework |
| **Uvicorn** | ≥ 0.27.0 | ASGI server that hosts the FastAPI app |
| **Pydantic v2** (`pydantic-settings`) | ≥ 2.1.0 | Settings management and API request/response validation schemas |
| **SQLite** (stdlib `sqlite3`) | Built-in | Local embedded database — no external DB server needed |
| **TFLite Runtime** (`tflite-runtime`) | ≥ 2.14.0 | Runs the BirdNET `.tflite` model on-device. Preferred over full TensorFlow to save ~500MB RAM |
| **NumPy** | ≥ 1.24.0 | Audio array manipulation for pre/post-processing inference tensors |
| **Librosa** | ≥ 0.10.1 | Loads WAV files and computes Mel spectrograms (STFT → Mel scale → dB) |
| **Matplotlib** (OO API only) | ≥ 3.8.0 | Renders Mel spectrogram PNG images headlessly (no display server required) |
| **ALSA `arecord`** | System utility | Linux CLI tool called via `subprocess` to record audio from the ReSpeaker |
| **psutil** | Optional | Reads CPU%, RAM usage, and disk stats for the health endpoint |
| **threading** (stdlib) | Built-in | Runs the realtime pipeline in a background daemon thread alongside the API server |

**Key design principle**: No PyAudio, no sounddevice, no PortAudio. Audio capture uses `arecord` directly via `subprocess.run()` to bypass Python's GIL and avoid library dependency issues on ARM Linux.

---

### 3.3 ML Model — BirdNET TFLite

| Property | Value |
|---|---|
| Model name | **BirdNET** (developed by Cornell Lab of Ornithology + Chemnitz University) |
| Model format | **TensorFlow Lite (.tflite)** — compiled and quantized for edge inference |
| Model file | `backend/models/model.tflite` |
| Labels file | `backend/models/labels.txt` (~6000 bird species taxonomy labels) |
| Input | Float32 numpy array of shape `[1, input_sample_size]` — raw normalized PCM audio |
| Input audio spec | 16 kHz, mono, 3-second window, normalized to `[-1.0, 1.0]` |
| Expected input size | Typically 144,000 samples (3s × 48kHz native model rate; auto-padded/cropped) |
| Output | Float32 array of shape `[1, num_species]` — probability score per species label |
| Confidence threshold | Default **0.70** (70%) — configurable via `MIN_CONFIDENCE_THRESHOLD` in `config.py` |
| Inference library | `tflite_runtime.interpreter.Interpreter` (falls back to `tensorflow.lite` if not found) |

**How BirdNET works inside this project**:
1. A 3-second WAV file is read using Python's stdlib `wave` module.
2. PCM frames are decoded into a float32 numpy array and normalized to `[-1.0, 1.0]`.
3. Stereo audio is collapsed to mono by striding every `nchannels`-th sample.
4. The array is zero-padded or cropped to exactly `input_sample_size` samples.
5. The array is wrapped in a `[1, input_sample_size]` batch tensor and fed into the TFLite interpreter.
6. `interpreter.invoke()` runs the inference pass.
7. The output tensor (one float per species) is scanned; species with probability ≥ threshold are collected.
8. Results are sorted descending by confidence and returned as a list of dicts.

**Label parsing**: BirdNET labels follow the format `Scientific Name (Common Name)` or `0001_ScientificName_CommonName`. The `parse_detection()` method in `birdnet_service.py` handles both formats and strips numeric prefixes.

---

### 3.4 Frontend — React (runs in browser, polls the Pi's API)

| Technology | Version | Purpose |
|---|---|---|
| **React** | ^18.2.0 | UI component framework |
| **React DOM** | ^18.2.0 | DOM rendering |
| **Vite** | ^5.0.8 | Build tool and development server |
| **Lucide React** | ^0.300.0 | Icon library |
| **ESLint** | ^8.55.0 | Code linting |
| **Vanilla CSS** | — | Styling (no CSS framework) |

**Frontend data flow**: The frontend is a React SPA that polls the FastAPI backend over HTTP. There is no WebSocket connection yet (planned for a future release). The frontend fetches:
- `GET /api/v1/detections` — paginated bird detection logs
- `GET /api/v1/health` — hardware diagnostics (CPU temp, RAM, disk)
- `GET /api/v1/stats` — aggregate analytics (species counts, average confidence)
- `GET /api/v1/recordings/{filename}` — to play WAV audio clips inline
- `GET /api/v1/spectrograms/{filename}` — to display Mel spectrogram images

**Polling interval**: Every 2–5 seconds to `GET /api/v1/detections?limit=10` for real-time updates.

---

### 3.5 Database — SQLite (local, embedded)

**File location**: `data/detections/chirply.db`

**Engine**: Python's built-in `sqlite3` module. No ORM. Raw SQL only.

**WAL mode enabled**: `PRAGMA journal_mode=WAL` — allows FastAPI read queries to run concurrently while the pipeline worker thread is actively writing, without locking.

**Schema**:

```sql
CREATE TABLE IF NOT EXISTS detections (
    id                TEXT PRIMARY KEY,    -- e.g. "det_839f3c92" (det_ + 8-char UUID hex)
    timestamp         TEXT NOT NULL,       -- ISO 8601 UTC datetime, e.g. "2026-05-26T16:45:02Z"
    scientific_name   TEXT NOT NULL,       -- e.g. "Cyanocitta cristata"
    common_name       TEXT NOT NULL,       -- e.g. "Blue Jay"
    confidence        REAL NOT NULL,       -- e.g. 0.89 (0.0 to 1.0)
    audio_file        TEXT NOT NULL,       -- e.g. "rec_20260526_164500.wav"
    spectrogram_file  TEXT NOT NULL,       -- e.g. "spec_20260526_164500.png"
    start_time        REAL NOT NULL,       -- audio segment start, always 0.0
    end_time          REAL NOT NULL,       -- audio segment end, always 3.0
    latitude          REAL,                -- optional GPS latitude (nullable)
    longitude         REAL                 -- optional GPS longitude (nullable)
);

CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detections_common_name ON detections (common_name);
```

**SQLite PRAGMAs applied per connection**:
- `journal_mode=WAL` — concurrent reads/writes
- `busy_timeout=5000` — 5-second timeout before returning a lock error
- `synchronous=NORMAL` — safe write speed improvement with WAL

---

## 4. REST API Reference

All routes are prefixed with `/api/v1`.

### 4.1 Detections

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/detections` | Paginated list of all detection events |
| `GET` | `/api/v1/detections/{id}` | Single detection details by ID |
| `GET` | `/api/v1/detections/summary/species` | Aggregated species list with detection counts |

**Query params for `GET /api/v1/detections`**:
- `limit` (int, 1–100, default 50)
- `offset` (int, default 0)
- `min_confidence` (float 0.0–1.0, optional filter)
- `species` (string, optional — partial match on common_name or scientific_name)

**Example response for `GET /api/v1/detections`**:
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
      "audio_url": "/api/v1/recordings/rec_20260526_164500.wav",
      "spectrogram_url": "/api/v1/spectrograms/spec_20260526_164500.png"
    }
  ]
}
```

### 4.2 Media Asset Serving

| Method | Endpoint | Returns |
|---|---|---|
| `GET` | `/api/v1/recordings/{filename}` | Streams WAV audio file (`audio/wav`) |
| `GET` | `/api/v1/spectrograms/{filename}` | Returns PNG spectrogram image (`image/png`) |

**Security**: Both endpoints enforce strict regex validation on filenames (`^[a-zA-Z0-9_\-]+\.(wav|png)$`) and block path traversal attacks by verifying the resolved absolute path starts within the configured storage directory.

### 4.3 Health & System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Raspberry Pi diagnostics (CPU%, temperature, RAM, disk, pipeline status) |
| `GET` | `/api/v1/stats` | Total detections, unique species count, average confidence, storage utilization |

**Example response for `GET /api/v1/health`**:
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
  "microphone_level_db": 0.0,
  "telemetry": {
    "uptime_seconds": 3600,
    "total_processed_chunks": 1200,
    "total_detections": 47,
    "last_run_timestamp": "2026-05-26T16:45:02Z",
    "system_mode": "live",
    "database_path": "/path/to/data/detections/chirply.db",
    "recordings_dir": "/path/to/data/recordings",
    "spectrograms_dir": "/path/to/data/spectrograms"
  }
}
```

**Swagger UI**: Available at `http://<raspberry-pi-ip>:8000/docs` when the backend is running.

---

## 5. The Realtime Inference Pipeline

The **`RealtimeInferencePipeline`** class in `backend/app/pipelines/realtime_pipeline.py` is the heart of the system. It runs in a **background daemon thread**, started on FastAPI app startup, and orchestrates the continuous audio → AI → database loop.

### 5.1 Pipeline Lifecycle

```
FastAPI startup_event()
    │
    ├── FileUtils.ensure_directories_exist()   ← creates /data/recordings, /spectrograms, /detections
    ├── DetectionLoggerService.initialize_database()  ← provisions SQLite schema and indexes
    ├── BirdNetService()                        ← instantiated (model not loaded yet)
    ├── SpectrogramService()                    ← instantiated
    ├── AudioRecorderService()                  ← validates mic hardware; enters mock mode if absent
    ├── RealtimeInferencePipeline(...)          ← wired up with all services
    └── pipeline.start()                        ← spawns daemon worker thread → run_loop()
```

### 5.2 Main Loop — Step by Step

The `run_loop()` method executes the following steps **continuously** (no sleep between iterations — the `arecord` subprocess call itself blocks for exactly 3 seconds, acting as the loop clock):

```
┌─────────────────────────────────────────────────────────┐
│  LOOP ITERATION (every ~3 seconds)                      │
│                                                         │
│  1. AudioRecorderService.record_audio(duration=3)       │
│     └── Calls: arecord -D plughw:1,0 -d 3 -f S16_LE   │
│                -r 16000 -c 1 -t wav rec_TIMESTAMP.wav   │
│     └── Returns: absolute path to the new WAV file      │
│                                                         │
│  2. BirdNetService.run_inference(audio_path)            │
│     └── Opens WAV → numpy float32 array                 │
│     └── Pad/crop to model input_sample_size             │
│     └── TFLite interpreter.invoke()                     │
│     └── Filter outputs by confidence >= 0.70            │
│     └── Returns: list of {scientific_name, common_name, │
│                            confidence, start_time,      │
│                            end_time}                    │
│                                                         │
│  3. If detections found:                                │
│     ├── SpectrogramService.generate_spectrogram()       │
│     │   └── librosa.load() → Mel spectrogram STFT      │
│     │   └── power_to_db() → log scale                  │
│     │   └── matplotlib Figure → spec_TIMESTAMP.png     │
│     │                                                   │
│     └── DetectionLoggerService.log_detection()  (×N)   │
│         └── INSERT INTO detections (id, timestamp,     │
│              scientific_name, common_name, confidence,  │
│              audio_file, spectrogram_file, ...)         │
│                                                         │
│  4. If NO detections:                                   │
│     └── os.remove(audio_path)  ← discard the WAV       │
│                                                         │
│  5. Every 3600 seconds (hourly):                        │
│     ├── SpectrogramService.cleanup_old_spectrograms()   │
│     │   └── Deletes PNG files older than 24 hours       │
│     └── FileUtils.cleanup_old_files(recordings_dir)     │
│         └── Keeps only the newest 1000 WAV files        │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Error Resilience

- On any exception during an iteration: `consecutive_errors` counter increments.
- Back-off sleep: `min(5 × consecutive_errors, 30)` seconds — prevents CPU spin on hardware failure.
- After 5 consecutive failures: `pipeline_active = False` — the health endpoint reports `"degraded"`.
- `KeyboardInterrupt` exits the loop cleanly.

### 5.4 Developer Mock Mode

When running on a machine without an ALSA-compatible audio device (e.g., a Windows laptop during development):
- `AudioRecorderService.validate_microphone()` calls `arecord -l` and detects no hardware.
- `self.mock_mode = True` is set automatically.
- `record_audio()` generates a synthetic 440 Hz sine wave WAV file programmatically and waits 3 seconds to simulate real capture latency.
- BirdNET inference still runs on this mock audio (it will detect nothing, since a pure sine wave is not birdsong).
- The health endpoint reports `"system_mode": "mock"`.

---

## 6. Spectrogram Generation — Technical Detail

**Service**: `SpectrogramService` in `backend/app/services/spectrogram_service.py`

**Process**:
1. `librosa.load(audio_path, sr=None, mono=True)` — loads WAV at its native sample rate, converts to mono float32 `[-1.0, 1.0]`.
2. Amplitude normalization: divide by `np.max(np.abs(y))` so quiet recordings render clearly.
3. `librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=128)` — short-time Fourier transform → 128 Mel frequency bands.
4. `librosa.power_to_db(S, ref=np.max, top_db=80.0)` — converts power to log-scale dB, cutting the noise floor at −80 dB.
5. Matplotlib `Figure` (not `plt.figure`) renders the matrix as an image using the `"magma"` colormap.
6. `FigureCanvasAgg` (non-interactive Agg backend) writes the PNG directly to disk.
7. The Figure object is explicitly cleared (`fig.clf()`) to allow immediate garbage collection — critical in a long-running loop to prevent memory leaks.

**Output**: A `800 × 400 px`, `100 DPI`, axis-less PNG image.  
**Naming convention**: `rec_20260526_164500.wav` → `spec_20260526_164500.png`

---

## 7. Audio Recording — Technical Detail

**Service**: `AudioRecorderService` in `backend/app/services/audio_recorder.py`

**Hardware device string**: `plughw:1,0`
- `plughw` — ALSA plug layer for automatic format conversion
- `1` — soundcard index (the ReSpeaker registers as card 1; verified via `arecord -l`)
- `0` — subdevice index

**`arecord` command constructed**:
```bash
arecord -D plughw:1,0 -d 3 -f S16_LE -r 16000 -c 1 -t wav /path/to/data/recordings/rec_YYYYMMDD_HHMMSS.wav
```

| Flag | Meaning |
|---|---|
| `-D plughw:1,0` | Target ALSA device |
| `-d 3` | Duration in seconds |
| `-f S16_LE` | Format: 16-bit signed PCM, little-endian |
| `-r 16000` | Sample rate: 16,000 Hz (BirdNET standard) |
| `-c 1` | Channels: 1 (mono) |
| `-t wav` | Output container: WAV with headers |

**File naming**: `rec_YYYYMMDD_HHMMSS.wav` (UTC timestamp, guaranteed unique per second).

---

## 8. Configuration — All Tuneable Values

All configuration lives in `backend/app/core/config.py` as a Pydantic `BaseSettings` class.
Environment variables are prefixed with `CHIRPLY_` (e.g., `CHIRPLY_MIN_CONFIDENCE_THRESHOLD=0.85`).

| Setting | Default | Description |
|---|---|---|
| `APP_NAME` | `"Chirply AI"` | FastAPI app title |
| `APP_VERSION` | `"0.1.0"` | Application version |
| `API_PREFIX` | `"/api/v1"` | URL prefix for all API routes |
| `DB_PATH` | `data/detections/chirply.db` | SQLite database file path |
| `AUDIO_SAMPLE_RATE` | `16000` | Hz — BirdNET standard |
| `AUDIO_CHANNELS` | `1` | Mono recording |
| `AUDIO_CHUNK_DURATION_SECONDS` | `3.0` | Length of each recorded audio chunk |
| `AUDIO_INPUT_INDEX` | `1` | ALSA hardware card index for ReSpeaker |
| `BIRDNET_MODEL_PATH` | `backend/models/model.tflite` | Path to BirdNET TFLite model |
| `BIRDNET_LABELS_PATH` | `backend/models/labels.txt` | Path to species labels file |
| `MIN_CONFIDENCE_THRESHOLD` | `0.70` | Minimum confidence to log a detection |
| `DEFAULT_SPECIES_LIST` | `["American Robin", "Blue Jay", "Northern Cardinal"]` | Default filter list |
| `STORAGE_BASE_DIR` | `data/` | Root of all runtime data storage |
| `RECORDINGS_DIR` | `data/recordings/` | Where WAV clips are saved |
| `SPECTROGRAMS_DIR` | `data/spectrograms/` | Where spectrogram PNGs are saved |
| `SPECTROGRAM_DPI` | `100` | PNG resolution (dots per inch) |
| `SPECTROGRAM_WIDTH_PX` | `800` | Spectrogram image width in pixels |
| `SPECTROGRAM_HEIGHT_PX` | `400` | Spectrogram image height in pixels |
| `SPECTROGRAM_COLORMAP` | `"magma"` | Matplotlib colormap for rendering |

---

## 9. Pydantic Schemas (API Contracts)

All schemas live in `backend/app/schemas/detection_schema.py`.

| Schema Class | Used In | Purpose |
|---|---|---|
| `DetectionBaseSchema` | Internal base | `species_common`, `species_scientific`, `confidence` |
| `DetectionCreateSchema` | Internal | Extends base with `timestamp`, `audio_file`, `spectrogram_file` |
| `DetectionResponseSchema` | API response | Extends base with `id`, `timestamp`, `audio_url`, `spectrogram_url` |
| `DetectionHistorySchema` | `GET /detections` | Pagination wrapper: `total`, `limit`, `offset`, `results[]` |
| `HardwareStatusSchema` | `GET /health` | CPU%, temperature, RAM, disk |
| `TelemetryStatusSchema` | `GET /health` | Uptime, chunks processed, total detections, paths |
| `SystemStatusSchema` | `GET /health` | Top-level health response |
| `SpeciesCountSchema` | `GET /stats` | `common_name` + `count` |
| `StatsResponseSchema` | `GET /stats` | Total detections, unique species, average confidence, storage |

---

## 10. Working Architecture (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI EDGE DEVICE                        │
│                                                                     │
│  ┌───────────────┐   raw PCM audio (16kHz mono)                     │
│  │  ReSpeaker    │──────────────────────────────────────────────┐   │
│  │  4-Mic HAT    │  ALSA / seeed-voicecard driver               │   │
│  └───────────────┘                                              ▼   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              RealtimeInferencePipeline (daemon thread)       │   │
│  │                                                              │   │
│  │  AudioRecorderService                                        │   │
│  │  └── subprocess: arecord → rec_YYYYMMDD_HHMMSS.wav          │   │
│  │       ↓                                                      │   │
│  │  BirdNetService                                              │   │
│  │  └── wave.open() → numpy float32 → TFLite interpreter       │   │
│  │  └── model.tflite (BirdNET) → [0.0 ... 1.0] per species     │   │
│  │  └── filter by confidence ≥ 0.70                            │   │
│  │       ↓ (if species detected)                                │   │
│  │  SpectrogramService                                          │   │
│  │  └── librosa STFT → Mel spectrogram → dB scale              │   │
│  │  └── matplotlib Figure → spec_YYYYMMDD_HHMMSS.png           │   │
│  │       ↓                                                      │   │
│  │  DetectionLoggerService                                      │   │
│  │  └── sqlite3 INSERT INTO detections (...)                    │   │
│  │       ↓                                                      │   │
│  │  If no species detected:                                     │   │
│  │  └── os.remove(wav_path)  ← discard to save disk space      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              FastAPI (uvicorn, port 8000)                    │   │
│  │                                                              │   │[]
│  │  GET /api/v1/health         → system diagnostics             │   │
│  │  GET /api/v1/detections     → paginated detection history    │   │
│  │  GET /api/v1/detections/{id}→ single detection record        │   │
│  │  GET /api/v1/stats          → aggregate analytics            │   │
│  │  GET /api/v1/recordings/{f} → serve WAV file (audio/wav)    │   │
│  │  GET /api/v1/spectrograms/{f}→ serve PNG file (image/png)   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                │                                                     │
│                │ HTTP REST (LAN / localhost)                         │
└────────────────┼─────────────────────────────────────────────────────┘
                 │
                 ▼ (polling every 2–5 seconds)
┌─────────────────────────────────────────────────────────────────────┐
│                  REACT + VITE FRONTEND (browser)                    │
│                                                                     │
│  Dashboard views:                                                   │
│  - Real-time bird detection cards (species, confidence, timestamp)  │
│  - Inline WAV audio playback                                        │
│  - Mel spectrogram image display                                    │
│  - Species frequency charts and analytics                           │
│  - Hardware health panel (CPU temp, RAM, pipeline status)           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. Service Dependency Graph

```
main.py (FastAPI app)
│
├── FileUtils.ensure_directories_exist()
│
├── DetectionLoggerService
│   └── sqlite3 (stdlib)
│
├── BirdNetService
│   └── tflite_runtime.interpreter / tensorflow.lite
│   └── numpy
│   └── wave (stdlib)
│
├── SpectrogramService
│   └── librosa
│   └── numpy
│   └── matplotlib (Figure, FigureCanvasAgg — OO API only)
│
├── AudioRecorderService
│   └── subprocess → arecord (ALSA system utility)
│   └── wave, struct, math (stdlib, mock mode only)
│
└── RealtimeInferencePipeline
    ├── AudioRecorderService
    ├── BirdNetService
    ├── SpectrogramService
    └── DetectionLoggerService
```

---

## 12. File Naming Conventions

| File Type | Naming Pattern | Example |
|---|---|---|
| Audio recording | `rec_YYYYMMDD_HHMMSS.wav` | `rec_20260526_164500.wav` |
| Spectrogram image | `spec_YYYYMMDD_HHMMSS.png` | `spec_20260526_164500.png` |
| Detection record ID | `det_` + 8-char UUID hex | `det_839f3c92` |
| Database file | `chirply.db` | `data/detections/chirply.db` |

Audio and spectrogram filenames share the same timestamp so they can be paired by stripping the prefix (`rec_` / `spec_`).

---

## 13. Storage Management

The system runs 24/7 and proactively manages its own storage to prevent SD card exhaustion:

- **Hourly cleanup** (triggered inside `run_loop()`):
  - Spectrograms older than **24 hours** are deleted.
  - Oldest recordings are pruned when the total count exceeds **1,000 WAV files**.
- **Per-chunk cleanup**: WAV files with no bird detections are deleted immediately after inference.
- Only WAV files for confirmed detection events are kept on disk.

---

## 14. CORS Configuration

The FastAPI app allows all origins (`allow_origins=["*"]`) during development. This permits the React dev server (running on `localhost:5173`) to call the Pi's API over the local network. This should be restricted to the Pi's LAN IP in production.

---

## 15. Known Limitations & Planned Features

| Item | Status | Notes |
|---|---|---|
| WebSocket live push | **Planned** | Currently uses REST polling. `WS /api/v1/stream` is on the roadmap. |
| GPS coordinates | **Schema ready, not populated** | `latitude` and `longitude` columns exist in the DB but are always `NULL` currently. |
| Multi-device support | **Planned** | Multiple pipeline instances targeting different ReSpeaker units |
| Authentication | **Not implemented** | API is open; recommended to restrict via firewall rules on the Pi's LAN |
| Frontend is scaffold | **In progress** | React app structure exists; full UI components are under active development |
| `psutil` dependency | **Optional** | If not installed, CPU/RAM stats in `/health` return `0` — no crash |

---

## 16. How to Run

### Backend (on Raspberry Pi)

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Place the BirdNET model files
#    Download model.tflite and labels.txt from the BirdNET-Analyzer releases
#    and place them at:
#      backend/models/model.tflite
#      backend/models/labels.txt

# 4. Start the FastAPI backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (on any machine on the same LAN)

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
# Configure the API base URL to point at http://<raspberry-pi-ip>:8000
```

---

*This document was auto-generated on 2026-06-01 by reading every source file in the project.*
*It reflects the actual implemented state of the codebase — not aspirational or planned features, unless explicitly noted in Section 15.*
