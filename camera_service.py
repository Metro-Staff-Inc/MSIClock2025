import cv2
import logging
import numpy as np
from typing import Optional, Tuple, Dict
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings = self._load_settings(settings_path)
        self.camera = None
        self.is_initialized = False

    def _load_settings(self, settings_path: str) -> Dict:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def initialize(self) -> bool:
        """Initialize the camera with configured settings"""
        try:
            if self.camera is not None:
                self.camera.release()

            device_id = self.settings['camera']['deviceId']
            
            # Try different backends in order of preference
            backends = [
                cv2.CAP_DSHOW,  # DirectShow (Windows)
                cv2.CAP_MSMF,   # Microsoft Media Foundation
                cv2.CAP_ANY     # Auto-detect
            ]
            
            for backend in backends:
                self.camera = cv2.VideoCapture(device_id + backend)
                if self.camera.isOpened():
                    logger.info(f"Camera initialized using backend: {backend}")
                    break

            if not self.camera.isOpened():
                logger.error(f"Failed to open camera device {device_id} with any backend")
                return False

            # Test capture to ensure camera is working
            ret, _ = self.camera.read()
            if not ret:
                logger.error("Camera opened but failed to capture test frame")
                self.camera.release()
                self.camera = None
                return False

            # Set resolution
            width = self.settings['camera']['resolution']['width']
            height = self.settings['camera']['resolution']['height']
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            # Verify settings were applied
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            if abs(width - actual_width) > 1 or abs(height - actual_height) > 1:
                logger.warning(
                    f"Camera resolution mismatch. Requested: {width}x{height}, "
                    f"Got: {actual_width}x{actual_height}"
                )

            self.is_initialized = True
            logger.info("Camera initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self.is_initialized = False
            return False

    def capture_frame(self) -> Optional[Tuple[np.ndarray, bytes]]:
        """
        Capture a frame from the camera
        Returns: Tuple of (frame as numpy array, JPEG encoded bytes) or None if failed
        """
        if not self.is_initialized or self.camera is None:
            logger.error("Camera not initialized")
            return None

        try:
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Failed to capture frame")
                return None

            # Convert frame to JPEG
            quality = self.settings['camera']['captureQuality']
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            return frame, buffer.tobytes()

        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None

    def capture_photo(self, employee_id: str) -> Optional[bytes]:
        """
        Capture a photo for an employee punch
        Returns: JPEG encoded bytes or None if failed
        """
        try:
            result = self.capture_frame()
            if result is None:
                return None

            frame, jpeg_data = result

            # Save a local copy for backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photos/{employee_id}_{timestamp}.jpg"
            
            os.makedirs("photos", exist_ok=True)
            cv2.imwrite(filename, frame)

            return jpeg_data

        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            return None

    def start_preview(self, window_name: str = "Camera Preview") -> bool:
        """Start a preview window for camera testing"""
        if not self.is_initialized or self.camera is None:
            logger.error("Camera not initialized")
            return False

        try:
            while True:
                result = self.capture_frame()
                if result is None:
                    break

                frame, _ = result
                cv2.imshow(window_name, frame)

                # Break loop on 'q' key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cv2.destroyWindow(window_name)
            return True

        except Exception as e:
            logger.error(f"Error in preview: {e}")
            return False

    def cleanup(self):
        """Release camera resources"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            self.is_initialized = False
            logger.info("Camera resources released")
        except Exception as e:
            logger.error(f"Error cleaning up camera: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()

    def test_camera(self) -> Dict[str, any]:
        """
        Test camera functionality and return status
        Returns: Dictionary with test results
        """
        results = {
            'initialized': False,
            'capture_test': False,
            'resolution_match': False,
            'actual_resolution': None
        }

        try:
            # Test initialization
            if self.initialize():
                results['initialized'] = True

                # Test capture
                capture_result = self.capture_frame()
                if capture_result is not None:
                    results['capture_test'] = True

                # Check resolution
                actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                results['actual_resolution'] = f"{actual_width}x{actual_height}"

                expected_width = self.settings['camera']['resolution']['width']
                expected_height = self.settings['camera']['resolution']['height']
                results['resolution_match'] = (
                    abs(expected_width - actual_width) <= 1 and 
                    abs(expected_height - actual_height) <= 1
                )

        except Exception as e:
            logger.error(f"Camera test failed: {e}")
            results['error'] = str(e)

        finally:
            self.cleanup()

        return results