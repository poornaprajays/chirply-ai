import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger("chirply.services.audio")

class AudioRecorderService:
    """
    Edge-optimized audio recording service utilizing the Linux native `arecord` command.
    Bypasses high-overhead Python sound libraries to maximize recording stability 
    on Raspberry Pi systems equipped with the ReSpeaker 4 Mic Array.
    """
    
    def __init__(self, device_name: str = "plughw:1,0", sample_rate: int = 16000, 
                 channels: int = 1, output_dir: str = "data/recordings/"):
        """
        Initializes recording paths and configures the default ALSA audio device.
        """
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_dir = os.path.abspath(output_dir)
        
        # Create output directories if missing to prevent file creation errors
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Recordings storage folder created at: {self.output_dir}")

    def generate_output_path(self) -> str:
        """
        Generates a clean timestamped filename to prevent naming collisions.
        Format: rec_YYYYMMDD_HHMMSS.wav
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"rec_{timestamp}.wav"
        return os.path.join(self.output_dir, filename)

    def validate_microphone(self) -> bool:
        """
        Validates hardware presence by invoking 'arecord -l'.
        Ensures the soundcard interface is active before initiating pipeline threads.
        """
        logger.info("Querying system soundcards for input hardware devices...")
        try:
            result = subprocess.run(
                ["arecord", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Scan output lines for capture card indicators
            if "card" in result.stdout.lower():
                logger.info("Arecord soundcard validation succeeded.")
                logger.debug(f"Arecord devices:\n{result.stdout}")
                return True
            else:
                logger.warning("arecord found no available capture hardware devices.")
                return False
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Soundcard validation failed: {e}", exc_info=True)
            return False

    def record_audio(self, duration: int = 3) -> str:
        """
        Invokes ALSA 'arecord' directly via subprocess to record a WAV segment.
        Returns the absolute filepath of the generated WAV file.
        
        Raspberry Pi Friendly Design:
        - Natively executes in C via ALSA, completely bypassing Python's GIL.
        - Clean exit hooks prevent zombie audio device locks on process restarts.
        """
        output_path = self.generate_output_path()
        logger.info(f"Initiating arecord capture: {output_path} (Duration: {duration}s)")
        
        # command flags:
        # -D: target sound device
        # -d: duration in seconds
        # -f: format (S16_LE is standard 16-bit Signed PCM)
        # -r: sample rate (16000Hz is BirdNET standard)
        # -c: channels (1 for Mono)
        # -t: output container type (WAV format metadata headers)
        command = [
            "arecord",
            "-D", self.device_name,
            "-d", str(duration),
            "-f", "S16_LE",
            "-r", str(self.sample_rate),
            "-c", str(self.channels),
            "-t", "wav",
            output_path
        ]
        
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logger.info(f"Recording completed: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"arecord failed with exit code {e.returncode}. Stderr: {e.stderr}")
            # Prune corrupted or empty output files to maintain storage cleanliness
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise RuntimeError(f"ALSA recording failed: {e.stderr}") from e
            
        except FileNotFoundError:
            err_msg = "ALSA 'arecord' utility not found. Please install alsa-utils on your Linux host."
            logger.critical(err_msg)
            raise RuntimeError(err_msg)

