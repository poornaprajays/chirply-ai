import logging
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger("chirply.services.birdnet")

class BirdNetService:
    """
    Service layer handling loading of the BirdNET TF Lite model
    and running acoustic inference over raw 3-second audio arrays.
    """
    
    def __init__(self, model_path: str):
        """
        Sets model paths and initializes interpreter variables to None.
        """
        self.model_path = model_path
        self.interpreter = None
        self.labels = []

    def load_model(self) -> None:
        """
        Loads the TFLite interpreter, allocates tensors, and imports 
        species taxonomy lookup indexes from labels file on startup.
        """
        pass

    def run_inference(self, audio_data: np.ndarray, min_confidence: float = 0.70) -> List[Dict[str, Any]]:
        """
        Converts input audio arrays into floating points, feeds them to the 
        TFLite model inputs, triggers calculation, and parses outputs.
        Returns a list of dictionaries with matching species and confidence metrics.
        """
        pass
