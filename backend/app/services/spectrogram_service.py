import os
import time
import logging
from pathlib import Path
import librosa
import numpy as np

# Edge Optimization: Bypassing matplotlib.pyplot and importing Figure/FigureCanvasAgg
# directly. This completely isolates the figure lifecycle, avoiding pylab/pyplot's
# global figure registry (Gcf) which leaks memory under continuous edge ingestion loops.
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from backend.app.core.config import settings

logger = logging.getLogger("chirply.services.spectrogram")

class SpectrogramService:
    """
    Service responsible for transforming audio WAV chunks 
    into visual Mel spectrogram images (.png) for user validation.
    Optimized for headless edge deployment (Raspberry Pi) with strict memory controls.
    """
    
    def __init__(self, output_dir: str = None, dpi: int = None, 
                 width_px: int = None, height_px: int = None, colormap: str = None):
        """
        Initializes the spectrogram service with parameters.
        Falls back to global Settings configuration if parameters are not provided.
        """
        self.output_dir = Path(output_dir or settings.SPECTROGRAMS_DIR)
        self.dpi = dpi or settings.SPECTROGRAM_DPI
        self.width_px = width_px or settings.SPECTROGRAM_WIDTH_PX
        self.height_px = height_px or settings.SPECTROGRAM_HEIGHT_PX
        self.colormap = colormap or settings.SPECTROGRAM_COLORMAP
        
        # Output directory auto-creation to prevent write crash faults
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"SpectrogramService initialized (Output: {self.output_dir}, "
            f"DPI: {self.dpi}, Resolution: {self.width_px}x{self.height_px}, Colormap: {self.colormap})"
        )

    def generate_spectrogram(self, audio_path: str) -> str:
        """
        Loads a WAV file, converts to mono, normalizes amplitude, computes a Mel spectrogram,
        converts power to log-scale decibels, and saves a clean axis-less PNG image.
        
        Mel Spectrogram / STFT Reasoning:
        - Short-Time Fourier Transform (STFT): Divides the continuous time audio signal into short,
          overlapping time frames and applies Fast Fourier Transform (FFT) on each frame. This represents
          spectral components changing over time.
        - Mel Scale Mapping: Frequencies are mapped onto the non-linear Mel scale using overlapping
          triangular bandpass filters. This mimics both human and avian auditory perception models, which
          are far more sensitive to pitch changes at lower frequencies.
        - Logarithmic Decibel (dB) Scaling: Since sound pressure level perception is logarithmic, raw power
          values are compressed via 10 * log10(S) using librosa.power_to_db. This elevates quiet vocalizations
          and suppresses the dynamic range of background ambient noise, enhancing visual classification.
          
        Edge Optimization & Memory-Safety:
        - OO-API Canvas Isolation: By instantiating a raw Figure and canvas without pyplot, we bypass
          the global Gcf figure list. Figures are GC-reclaimed immediately when variables go out of scope.
        - Dynamic Downscaling: Calculations use native sampling rates and map to compact pixel layouts,
          creating compressed file outputs (<50KB) that save SD-card storage and network bandwidth.
        """
        # Validate path presence
        if not os.path.exists(audio_path):
            err_msg = f"Audio file not found for spectrogram generation: {audio_path}"
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)
            
        logger.info(f"Generating Mel spectrogram for: {audio_path}")
        
        # Standardize naming: rec_20260526_164500.wav -> spec_20260526_164500.png
        audio_name = Path(audio_path).stem
        clean_name = audio_name.replace("rec_", "")
        output_filename = f"spec_{clean_name}.png"
        output_path = str(self.output_dir / output_filename)
        
        fig = None
        try:
            # 1. Load WAV audio safely
            # librosa.load with sr=None preserves native sampling rate and automatically
            # normalizes 16-bit PCM amplitude values to a float32 array in the range [-1.0, 1.0].
            # mono=True automatically downmixes multi-channel recordings to mono.
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            
            if len(y) == 0:
                raise ValueError("Audio file decoded to an empty signal.")
                
            # 2. Normalize audio amplitude to peak 1.0 (prevents quiet recordings from appearing faint)
            peak = np.max(np.abs(y))
            if peak > 0:
                y = y / peak
                
            # 3. Compute Mel-scaled Spectrogram
            # n_fft=2048 and hop_length=512 are standard parameters optimized for avian calls (16kHz audio).
            # n_mels=128 compresses frequency space into 128 Mel bands.
            S = librosa.feature.melspectrogram(
                y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=128
            )
            
            # 4. Convert power spectrogram to logarithmic decibel (dB) scale
            # top_db=80.0 sets the noise floor cut-off. Any signal 80dB below the peak is filtered out.
            S_db = librosa.power_to_db(S, ref=np.max, top_db=80.0)
            
            # 5. Render borderless PNG image using Object-Oriented Matplotlib
            # Calculate target size in inches (inches = pixels / DPI)
            figsize_inches = (self.width_px / self.dpi, self.height_px / self.dpi)
            
            # Instantiate Figure directly (does not register in global pyplot list)
            fig = Figure(figsize=figsize_inches, dpi=self.dpi)
            canvas = FigureCanvas(fig)
            
            # Add axes spanning the entire figure canvas (0,0 to 1,1) for an axis-less visual render
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            
            # Display array values as an image. 'magma' colormap mimics typical bioacoustic spectrogram colors.
            ax.imshow(
                S_db, 
                aspect='auto', 
                origin='lower', 
                cmap=self.colormap, 
                interpolation='nearest'
            )
            
            # Save the rendering directly to disk
            fig.savefig(output_path, dpi=self.dpi, bbox_inches='tight', pad_inches=0)
            logger.info(f"Spectrogram generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Spectrogram generation failed for {audio_path}: {e}", exc_info=True)
            # Prune corrupted PNG files if the save process was interrupted
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise RuntimeError(f"Spectrogram generation failed: {e}") from e
            
        finally:
            # Memory Recovery: Clear figure elements and break object reference chains.
            # Bypassing pyplot means garbage collector will immediately recycle when scope exits.
            if fig is not None:
                fig.clf()

    def cleanup_old_spectrograms(self, max_age_hours: int) -> None:
        """
        Scans the spectrogram directory and prunes files older than max_age_hours.
        Prevents SD card write exhaustion and storage capacity limits on edge devices.
        """
        logger.info(f"Initiating cleanup of spectrograms older than {max_age_hours} hours...")
        if max_age_hours <= 0:
            logger.warning("Invalid max_age_hours value. Cleanup operation aborted.")
            return
            
        now = time.time()
        cutoff_seconds = max_age_hours * 3600
        deleted_count = 0
        
        try:
            # Iterate and filter PNG files inside the target spectrogram volume
            for file_path in self.output_dir.glob("*.png"):
                if file_path.is_file():
                    file_mtime = file_path.stat().st_mtime
                    if (now - file_mtime) > cutoff_seconds:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Purged old spectrogram file: {file_path.name}")
                        except OSError as e:
                            logger.error(f"Failed to delete spectrogram file {file_path.name}: {e}")
                            
            logger.info(f"Spectrogram folder cleanup finished. Deleted {deleted_count} files.")
        except Exception as e:
            logger.error(f"Error executing spectrogram database prune: {e}", exc_info=True)
