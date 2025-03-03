import cv2
import logging
import numpy as np
import sys
from typing import Optional, Tuple, Dict
from datetime import datetime
import json
import os
from ultralytics import YOLO
# Suppress YOLO logging
logging.getLogger("ultralytics").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings = self._load_settings(settings_path)
        self.camera = None
        self.is_initialized = False
        # Initialize YOLO model for person detection
        try:
            self.model = YOLO('yolov8n.pt')  # Using the smallest model for faster inference
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
            # Run inference with suppressed output
            import sys, os
            with open(os.devnull, 'w') as devnull:
                old_stdout = sys.stdout
                sys.stdout = devnull
                try:
                    results = self.model(frame, conf=0.5)  # Confidence threshold of 0.5
                finally:
                    sys.stdout = old_stdout
            
            # Get person detections (class 0 is person in COCO dataset)
            person_boxes = []
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == 0:  # Person class
                        person_boxes.append(box.xyxy[0].cpu().numpy())  # Get box coordinates

            if not person_boxes:
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

    def _list_available_cameras(self):
        """List all available camera devices on the system"""
        available_cameras = []
        
        # Check for cameras on Linux
        if sys.platform != 'win32':
            import glob
            # List all video devices
            video_devices = glob.glob('/dev/video*')
            logger.debug(f"Found video devices: {video_devices}")
            
            # Test each device
            for device in video_devices:
                try:
                    cap = cv2.VideoCapture(device)
                    if cap.isOpened():
                        available_cameras.append(device)
                        cap.release()
                except Exception as e:
                    logger.debug(f"Error testing device {device}: {e}")
            
        # Check for cameras by index (works on all platforms)
        for i in range(10):  # Check first 10 indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()
            except Exception:
                pass
                
        logger.debug(f"Available cameras: {available_cameras}")
        return available_cameras
    
    def initialize(self) -> bool:
        """Initialize the camera with configured settings"""
        try:
            if self.camera is not None:
                self.camera.release()
                
            # List available cameras
            available_cameras = self._list_available_cameras()
            if not available_cameras:
                logger.warning("No cameras detected on the system")
                # Create a fallback camera that returns a placeholder image
                self._setup_fallback_camera()
                return True

            device_id = self.settings['camera']['deviceId']
            
            # If configured device is not available, use the first available one
            if device_id not in available_cameras and len(available_cameras) > 0:
                logger.warning(f"Configured camera device {device_id} not available. Using {available_cameras[0]} instead.")
                device_id = available_cameras[0]
            
            # Select backends based on platform
            if sys.platform == 'win32':
                # Windows-specific backends
                backends = [
                    cv2.CAP_DSHOW,  # DirectShow (Windows)
                    cv2.CAP_MSMF,   # Microsoft Media Foundation
                    cv2.CAP_ANY     # Auto-detect
                ]
                
                # Try each backend
                for backend in backends:
                    self.camera = cv2.VideoCapture(device_id + backend)
                    if self.camera.isOpened():
                        logger.debug(f"Camera initialized with Windows backend: {backend}")
                        break
            else:
                # Linux/macOS backends
                try:
                    # If device_id is a string (path), use it directly
                    if isinstance(device_id, str):
                        self.camera = cv2.VideoCapture(device_id)
                        if not self.camera.isOpened():
                            self.camera = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
                    else:
                        # Try with numeric index
                        self.camera = cv2.VideoCapture(device_id)
                        if not self.camera.isOpened():
                            # Try with explicit path
                            self.camera = cv2.VideoCapture(f"/dev/video{device_id}")
                            
                    if not self.camera.isOpened():
                        # If still not open, try any available camera
                        for cam in available_cameras:
                            self.camera = cv2.VideoCapture(cam)
                            if self.camera.isOpened():
                                logger.debug(f"Camera initialized with device: {cam}")
                                break
                                
                    if not self.camera or not self.camera.isOpened():
                        logger.error("Failed to initialize camera with any available device")
                        self._setup_fallback_camera()
                        return True
                        
                except Exception as e:
                    logger.error(f"Error with Linux camera initialization: {e}")
                    self._setup_fallback_camera()
                    return True

            if not self.camera.isOpened():
                logger.error(f"Failed to open camera device {device_id} with any backend")
                self._setup_fallback_camera()
                return True

            # Test capture to ensure camera is working
            ret, _ = self.camera.read()
            if not ret:
                logger.error("Camera opened but failed to capture test frame")
                self.camera.release()
                self._setup_fallback_camera()
                return True

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
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self._setup_fallback_camera()
            return True
            
    def _setup_fallback_camera(self):
        """Set up a fallback camera that returns a placeholder image"""
        logger.info("Setting up fallback camera mode")
        self.is_initialized = True
        self._fallback_mode = True
        
        # Create a placeholder image
        width = self.settings['camera']['resolution']['width']
        height = self.settings['camera']['resolution']['height']
        
        # Create a dark gray image with text
        self._placeholder_image = np.zeros((height, width, 3), dtype=np.uint8)
        self._placeholder_image.fill(50)  # Dark gray
        
        # Add text to the image
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            self._placeholder_image,
            "No Camera Available",
            (width//2 - 150, height//2 - 20),
            font, 1, (255, 255, 255), 2, cv2.LINE_AA
        )
        cv2.putText(
            self._placeholder_image,
            "System will function without photos",
            (width//2 - 200, height//2 + 20),
            font, 0.7, (200, 200, 200), 1, cv2.LINE_AA
        )

    def capture_frame(self) -> Optional[Tuple[np.ndarray, bytes]]:
        """
        Capture a frame from the camera
        Returns: Tuple of (frame as numpy array, JPEG encoded bytes) or None if failed
        """
        if not self.is_initialized:
            logger.error("Camera not initialized")
            return None

        try:
            # Check if we're in fallback mode
            if hasattr(self, '_fallback_mode') and self._fallback_mode:
                frame = self._placeholder_image.copy()
                
                # Add timestamp to make the image dynamic
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(
                    frame,
                    timestamp,
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA
                )
                
                # Convert frame to JPEG
                quality = self.settings['camera']['captureQuality']
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                
                return frame, buffer.tobytes()
            
            # Normal camera mode
            if self.camera is None:
                logger.error("Camera object is None")
                return None
                
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
            # If in fallback mode, create a special placeholder for employee photos
            if hasattr(self, '_fallback_mode') and self._fallback_mode:
                # Create a timestamp if not provided
                if timestamp is None:
                    timestamp = datetime.now()
                
                # Create a placeholder image with employee ID and timestamp
                width = self.settings['camera']['resolution']['width']
                height = self.settings['camera']['resolution']['height']
                
                # Create a dark gray image with text
                placeholder = np.zeros((height, width, 3), dtype=np.uint8)
                placeholder.fill(50)  # Dark gray
                
                # Add text to the image
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(
                    placeholder,
                    f"Employee ID: {employee_id}",
                    (width//2 - 150, height//2 - 40),
                    font, 0.8, (255, 255, 255), 1, cv2.LINE_AA
                )
                cv2.putText(
                    placeholder,
                    f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    (width//2 - 150, height//2),
                    font, 0.8, (255, 255, 255), 1, cv2.LINE_AA
                )
                cv2.putText(
                    placeholder,
                    "No Camera Available",
                    (width//2 - 150, height//2 + 40),
                    font, 0.8, (200, 200, 200), 1, cv2.LINE_AA
                )
                
                # Convert to JPEG
                quality = self.settings['camera']['captureQuality']
                _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, quality])
                jpeg_data = buffer.tobytes()
                
                # Save a local copy
                filename = f"photos/{employee_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                os.makedirs("photos", exist_ok=True)
                cv2.imwrite(filename, placeholder)
                
                return jpeg_data
            
            # Normal camera mode
            result = self.capture_frame()
            if result is None:
                return None

            frame, _ = result

            # Detect and crop person from frame
            cropped_frame = self.detect_and_crop_person(frame)
            if cropped_frame is None:
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
            'actual_resolution': None,
            'fallback_mode': False,
            'available_cameras': []
        }

        try:
            # List available cameras
            available_cameras = self._list_available_cameras()
            results['available_cameras'] = available_cameras
            
            # Test initialization
            if self.initialize():
                results['initialized'] = True
                
                # Check if we're in fallback mode
                if hasattr(self, '_fallback_mode') and self._fallback_mode:
                    results['fallback_mode'] = True
                    results['capture_test'] = True  # Fallback mode always provides frames
                    
                    # Set resolution info
                    width = self.settings['camera']['resolution']['width']
                    height = self.settings['camera']['resolution']['height']
                    results['actual_resolution'] = f"{width}x{height}"
                    results['resolution_match'] = True
                    
                    # Add message about fallback mode
                    results['message'] = "Running in fallback mode - no camera detected"
                else:
                    # Test capture in normal mode
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