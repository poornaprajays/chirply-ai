Chirply-ai 
know the vast variety of difrrent species of birds with thier chirp...


<p align="center">
  <img src="images1/demo.png" width="800"/>
</p>

System Architecture:



┌─────────────────────────────┐
│ Raspberry Pi Edge Device    │
│                             │
│ ReSpeaker Mic Array         │
│ BirdNET Inference Engine    │
│ Audio Chunk Processor       │
│ Detection Logger Service    │
└─────────────┬───────────────┘
              │
              │ REST API (Polling)
              ▼
┌─────────────────────────────┐
│ FastAPI Backend             │
│                             │
│ Detection REST APIs         │
│ Species Metadata            │
│ Audio Clip Storage          │
│ Local SQLite DB Logger      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ SQLite Database (Local)     │
└─────────────┬───────────────┘
              │
         
             ▼
┌─────────────────────────────┐
│ React Frontend              │
│ Real-time (via polling)     │
│ Spectrograms                │
│ Bird cards                  │
│ Maps & analytics            │
└─────────────────────────────┘
