import os
import logging
from typing import List

logger = logging.getLogger("chirply.utils")

class FileUtils:
    """
    Utility helpers to manage files, directories, and data rotation
    specifically tailored for edge nodes (Raspberry Pi) with storage constraints.
    """
    
    @staticmethod
    def ensure_directories_exist(paths: List[str]) -> None:
        """
        Guarantees that essential system write paths (/data/recordings, etc.) 
        exist on start. Avoids read/write crash faults during pipelines.
        """
        for path in paths:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                os.makedirs(abs_path, exist_ok=True)
                logger.info(f"Created system directory: {abs_path}")

    @staticmethod
    def generate_unique_filename(prefix: str, extension: str) -> str:
        """
        Creates a time-structured file label (e.g., rec_20260526_164500.wav) 
        to guarantee strict ordering and easy offline sync query matches.
        """
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = extension.lstrip('.')
        return f"{prefix}_{timestamp}.{ext}"

    @staticmethod
    def cleanup_old_files(directory: str, max_files: int = 1000) -> None:
        """
        Scans a media folder (like recordings) and purges the oldest files
        when count exceeds max_files. Prevents Raspberry Pi SD/SSD exhaustion.
        """
        from pathlib import Path
        dir_path = Path(directory)
        if not dir_path.exists():
            return
            
        try:
            # Sort files in ascending order of modification time (oldest first)
            files = sorted(
                [f for f in dir_path.iterdir() if f.is_file()],
                key=lambda x: x.stat().st_mtime
            )
            
            if len(files) > max_files:
                num_to_delete = len(files) - max_files
                logger.info(f"Purging {num_to_delete} oldest files in {directory} to free up space...")
                for i in range(num_to_delete):
                    try:
                        files[i].unlink()
                        logger.debug(f"Purged file: {files[i].name}")
                    except OSError as e:
                        logger.error(f"Failed to delete old file {files[i].name}: {e}")
        except Exception as e:
            logger.error(f"Failed to execute files cleanup for {directory}: {e}", exc_info=True)
