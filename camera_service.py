import cv2
import logging
import numpy as np
from typing import Optional, Tuple, Dict
from datetime import datetime
import json
import os
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings = self._load_settings(settings_path)
        self.camera = None
        self.is_initialized = False
        # Initialize YOLO model for person detection
        try:
            self.model = YOLO('yolov8n.pt')  # Using the smallest model for faster inference
            logger.info("YOLO model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO model: {e}")
            self.model = None

    def detect_and_crop_person(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect a person in the frame and crop to their bounds
        Returns: Cropped frame containing the person or None if no person detected
        """
        if self.model is None:
            logger.error("YOLO model not initialized")
            return None

        try:
            # Run inference
            results = self.model(frame, conf=0.5)  # Confidence threshold of 0.5
            
            # Get person detections (class 0 is person in COCO dataset)
            person_boxes = []
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == 0:  # Person class
                        person_boxes.append(box.xyxy[0].cpu().numpy())  # Get box coordinates

            if not person_boxes:
                logger.warning("No person detected in frame")
                return frame  # Return original frame if no person detected

            # Use the largest person detection (assuming it's the closest/main subject)
            largest_box = max(person_boxes, key=lambda box: (box[2]-box[0]) * (box[3]-box[1]))
            
            # Add padding around the detection (10% on each side)
            height, width = frame.shape[:2]
            x1, y1, x2, y2 = largest_box
            padding_x = (x2 - x1) * 0.1
            padding_y = (y2 - y1) * 0.1
            
            x1 = max(0, int(x1 - padding_x))
            y1 = max(0, int(y1 - padding_y))
            x2 = min(width, int(x2 + padding_x))
            y2 = min(height, int(y2 + padding_y))

            # Crop the frame to the padded person bounds
            cropped_frame = frame[y1:y2, x1:x2]
            
            return cropped_frame

        except Exception as e:
            logger.error(f"Error in person detection: {e}")
            return None

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

    def _resize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Resize image if it exceeds max dimensions while maintaining aspect ratio
        """
        max_width = self.settings['camera'].get('maxWidth', float('inf'))
        max_height = self.settings['camera'].get('maxHeight', float('inf'))
        
        height, width = image.shape[:2]
        
        # Calculate scaling factor if image exceeds max dimensions
        scale_width = max_width / width if width > max_width else 1
        scale_height = max_height / height if height > max_height else 1
        scale = min(scale_width, scale_height)
        
        # Only resize if image needs to be scaled down
        if scale < 1:
            new_width = int(width * scale)
            new_height = int(height * scale)
            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return image

    def capture_photo(self, employee_id: str, timestamp: Optional[datetime] = None) -> Optional[bytes]:
        """
        Capture a photo for an employee punch, detect person and crop
        Args:
            employee_id: Employee ID for the photo
            timestamp: Optional timestamp to use for the filename (defaults to current time)
        Returns: JPEG encoded bytes or None if failed
        """
        try:
            result = self.capture_frame()
            if result is None:
                return None

            frame, _ = result

            # Detect and crop person from frame
            cropped_frame = self.detect_and_crop_person(frame)
            if cropped_frame is None:
                logger.warning("Failed to detect person, using original frame")
                cropped_frame = frame

            # Resize image if it exceeds max dimensions
            resized_frame = self._resize_image(cropped_frame)

            # Convert resized frame to JPEG
            quality = self.settings['camera']['captureQuality']
            _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            jpeg_data = buffer.tobytes()

            # Save a local copy for backup using provided timestamp or current time
            if timestamp is None:
                timestamp = datetime.now()
            filename = f"photos/{employee_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            
            os.makedirs("photos", exist_ok=True)
            cv2.imwrite(filename, resized_frame)

            return jpeg_data

        except Exception as e:
            logger.error(f"Error capturing photo: {e}")
            return None

    def start_preview(self, window_name: str = "Camera Preview") -> bool:
        """Start a preview window for camera testing with person detection"""
        if not self.is_initialized or self.camera is None:
            logger.error("Camera not initialized")
            return False

        try:
            while True:
                result = self.capture_frame()
                if result is None:
                    break

                frame, _ = result
                
                try:
                    # Show original frame
                    cv2.imshow(f"{window_name} - Original", frame)
                    
                    # Detect and crop person
                    cropped_frame = self.detect_and_crop_person(frame)
                    if cropped_frame is not None:
                        # Resize cropped frame if needed
                        resized_frame = self._resize_image(cropped_frame)
                        
                        # Show dimensions in window title
                        height, width = resized_frame.shape[:2]
                        cv2.imshow(f"{window_name} - Processed ({width}x{height})", resized_frame)

                    # Break loop on 'q' key or window close
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or cv2.getWindowProperty(f"{window_name} - Original", cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error as e:
                    logger.error(f"OpenCV error in preview: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error in preview loop: {e}")
                    break

            # Ensure windows are properly closed
            try:
                cv2.destroyAllWindows()
                cv2.waitKey(1)  # This is needed to properly close windows on some systems
            except Exception as e:
                logger.error(f"Error closing windows: {e}")

            return True

        except Exception as e:
            logger.error(f"Error in preview: {e}")
            return False

    def cleanup(self):
        """Release camera resources"""
        try:
            # Close any remaining windows
            try:
                cv2.destroyAllWindows()
                cv2.waitKey(1)  # Needed to properly close windows on some systems
            except Exception as e:
                logger.error(f"Error closing windows: {e}")

            # Release camera
            if self.camera is not None:
                try:
                    self.camera.release()
                except Exception as e:
                    logger.error(f"Error releasing camera: {e}")
                finally:
                    self.camera = None

            # Reset initialization state
            self.is_initialized = False
            logger.info("Camera resources released")

        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
            raise  # Re-raise the exception for proper error handling

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