# ReSpeaker Microphone Array & Raspberry Pi Setup Guide

This guide explains how to connect and configure the **ReSpeaker Mic Array** with your Raspberry Pi for real-time acoustic recording on the **chirply-ai** platform.

---

## 1. Hardware Integration

1. Turn off your Raspberry Pi.
2. Mount the **ReSpeaker HAT** (e.g., 2-Mics, 4-Mics, or 6-Mic Circular Array) carefully onto the Raspberry Pi's GPIO pins. Ensure it is fully seated.
3. Power on the Raspberry Pi.

---

## 2. Driver Installation (Raspberry Pi OS)

To enable the audio channels of the ReSpeaker, you must install the Seeed Voicecard drivers.

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Clone the driver repository
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard

# Install the drivers (Requires reboot)
sudo ./install.sh
sudo reboot
```

---

## 3. Audio Configuration (ALSA)

After rebooting, check if the sound card is recognized:

```bash
# List all capture hardware devices
arecord -l
```

You should see an output containing a card named `seeed-voicecard` or `ReSpeaker`.

### Configuring the Default Capture Card
Create or modify your ALSA configuration file at `/etc/asound.conf` or `~/.asoundrc` to route system-wide recording to the mic array:

```text
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:1,0"  # Adjust '1' depending on the card index from 'arecord -l'
    }
}
```

---

## 4. Troubleshooting and Validation

### Capture Test
Verify that the microphone is capturing audio correctly by recording a short test WAV clip:

```bash
# Record a 5-second 16kHz mono WAV clip
arecord -D plughw:1,0 -d 5 -f S16_LE -r 16000 -c 1 test_input.wav
```

You can copy this file to your computer or play it back to confirm the recording is clear:

```bash
aplay test_input.wav
```

### Python SoundDevice Check
To confirm your Python virtual environment can communicate with the hardware, run this in your activated venv:

```python
import sounddevice as sd
print(sd.query_devices())
```

Look for the device index pointing to `seeed-voicecard` or the default `capture` hardware. Use this index in your `backend/app/core/config.py` settings.
