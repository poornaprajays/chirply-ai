import os
import sqlite3
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chirply.services.db")

class DetectionLoggerService:
    """
    Edge-optimized, lightweight logging service for chirply-ai bird detections.
    Directly utilizes Python's built-in sqlite3 library to avoid high memory usage 
    and database write blockages common with heavy ORMs on Raspberry Pi.
    """
    
    def __init__(self, db_path: str = "data/detections/chirply.db"):
        """
        Initializes the service and guarantees database target folders exist on disk.
        """
        # Resolve path as an absolute filesystem location to avoid process-context errors
        self.db_path = os.path.abspath(db_path)
        
        # Automatically establish parent storage directories to prevent write failures
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Database directory created at: {db_dir}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Retrieves a configured SQLite connection channel.
        
        Raspberry Pi Friendly Design:
        - Row Factory: Returns rows mapping keys like dictionary records (FastAPI JSON ready).
        - WAL (Write-Ahead Logging) Mode: Crucial for concurrent edge read/write states.
        - Busy Timeout: Prevents locks by delaying block errors up to 5000ms.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # WAL mode allows FastAPI requests (read) to run while the pipeline writes
            conn.execute("PRAGMA journal_mode=WAL;")
            # busy_timeout lets connections queue instead of crashing immediately under load
            conn.execute("PRAGMA busy_timeout=5000;")
            # synchronous=NORMAL is safe with WAL and dramatically speeds up transactions
            conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.Error as e:
            logger.warning(f"Could not apply edge-optimizing SQLite PRAGMAs: {e}")
            
        return conn

    def initialize_database(self) -> None:
        """
        Provisions table schemas and binary search indexes on initialization.
        Avoids slow DDL runtimes and prevents SD-card write exhaustion.
        """
        logger.info("Initializing SQLite database tables and indices...")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            scientific_name TEXT NOT NULL,
            common_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            audio_file TEXT NOT NULL,
            spectrogram_file TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            latitude REAL,
            longitude REAL
        );
        """
        
        # Index common filter properties to ensure querying takes <1ms on Raspberry Pi
        create_indices_sql = [
            "CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections (timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_detections_common_name ON detections (common_name);"
        ]
        
        conn = None
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(create_table_sql)
                for index_sql in create_indices_sql:
                    conn.execute(index_sql)
            logger.info("Database and indices created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing SQLite database: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def log_detection(self, scientific_name: str, common_name: str, confidence: float,
                      audio_file: str, spectrogram_file: str, start_time: float = 0.0,
                      end_time: float = 3.0, latitude: Optional[float] = None,
                      longitude: Optional[float] = None) -> str:
        """
        Commits a newly registered bird identification event into SQLite.
        
        Raspberry Pi Friendly Design:
        - Lightweight UUID string keys are faster than multi-table joins.
        - ISO8601 UTC dates keep text searches direct and indexing highly efficient.
        - Open-and-Close scoping prevents lingering locks on files.
        """
        # Generate unique lightweight key prefixes
        detection_id = f"det_{uuid.uuid4().hex[:8]}"
        timestamp_str = datetime.utcnow().isoformat() + "Z"
        
        insert_sql = """
        INSERT INTO detections (
            id, timestamp, scientific_name, common_name, confidence,
            audio_file, spectrogram_file, start_time, end_time, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        conn = None
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(insert_sql, (
                    detection_id,
                    timestamp_str,
                    scientific_name,
                    common_name,
                    confidence,
                    audio_file,
                    spectrogram_file,
                    start_time,
                    end_time,
                    latitude,
                    longitude
                ))
            logger.info(f"Logged species detection: {common_name} (Confidence: {confidence:.2f}) -> {detection_id}")
            return detection_id
        except sqlite3.Error as e:
            logger.error(f"Failed to record bird detection in database: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def fetch_recent_detections(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves paginated logs for rendering charts and telemetry tables.
        Returns serialized dictionary rows for direct REST translation.
        """
        query_sql = "SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?;"
        
        conn = None
        results = []
        try:
            conn = self._get_connection()
            cursor = conn.execute(query_sql, (limit,))
            rows = cursor.fetchall()
            
            for row in rows:
                results.append(dict(row))
                
            return results
        except sqlite3.Error as e:
            logger.error(f"Failed to query recent detections from SQLite database: {e}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()

