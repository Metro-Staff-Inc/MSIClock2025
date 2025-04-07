import os
import json
import logging
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class OfflineStorage:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings_path = settings_path
        self.storage_file = self._get_storage_path()
        self._ensure_data_dir()

    def _get_storage_path(self) -> str:
        """Get the path to the offline storage file from settings"""
        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)
                # Convert the SQLite path to JSON path
                db_path = settings['storage']['dbPath']
                return db_path.replace('.db', '.json')
        except Exception as e:
            logger.error(f"Failed to get storage path: {e}")
            return 'data/local.json'  # Default path

    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

    def _load_punches(self) -> List[Dict[str, Any]]:
        """Load punches from the JSON file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load punches: {e}")
            return []

    def _save_punches(self, punches: List[Dict[str, Any]]):
        """Save punches to the JSON file using atomic write"""
        try:
            # Create a temporary file in the same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.storage_file),
                prefix='punches_',
                suffix='.tmp'
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(punches, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                
                # Atomic rename
                shutil.move(temp_path, self.storage_file)
                
            except Exception:
                # Clean up the temp file if something went wrong
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
                
        except Exception as e:
            logger.error(f"Failed to save punches: {e}")
            raise

    def store_punch(self, employee_id: str, punch_time: datetime,
                   punch_type: str = 'OFFLINE', image_filename: Optional[str] = None) -> Dict[str, Any]:
        """Store a punch in the offline storage"""
        try:
            punches = self._load_punches()
            
            # Create new punch record
            punch = {
                'id': len(punches) + 1,  # Simple auto-increment
                'employeeId': employee_id,
                'punchTime': punch_time.isoformat(),
                'punchType': punch_type,
                'imageFilename': image_filename,
                'synced': False,
                'createdAt': datetime.now().isoformat()
            }
            
            punches.append(punch)
            self._save_punches(punches)
            
            return {
                'success': True,
                'offline': True,
                'message': 'Punch stored offline',
                'punchType': punch_type,
                'employeeId': employee_id
            }
            
        except Exception as e:
            logger.error(f"Failed to store offline punch: {e}")
            raise

    def get_unsynced_punches(self) -> List[Dict[str, Any]]:
        """Get all unsynced punches"""
        try:
            punches = self._load_punches()
            return [p for p in punches if not p.get('synced', False)]
        except Exception as e:
            logger.error(f"Failed to get unsynced punches: {e}")
            return []

    def mark_as_synced(self, punch_id: int):
        """Mark a punch as synced"""
        try:
            punches = self._load_punches()
            for punch in punches:
                if punch['id'] == punch_id:
                    punch['synced'] = True
                    punch['syncedAt'] = datetime.now().isoformat()
                    break
            self._save_punches(punches)
        except Exception as e:
            logger.error(f"Failed to mark punch as synced: {e}")
            raise

    def cleanup_old_records(self, retention_days: int) -> int:
        """Remove old records based on retention policy"""
        try:
            from datetime import timedelta
            punches = self._load_punches()
            cutoff_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # Calculate cutoff date using timedelta
            cutoff_date = cutoff_date - timedelta(days=retention_days)
            
            # Filter out old records
            new_punches = [
                p for p in punches
                if datetime.fromisoformat(p['createdAt']).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) > cutoff_date
            ]
            
            deleted_count = len(punches) - len(new_punches)
            
            if deleted_count > 0:
                self._save_punches(new_punches)
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise