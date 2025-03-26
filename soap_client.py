import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import zeep
from zeep import Client, Transport, xsd
from zeep.exceptions import Fault, TransportError
from requests.exceptions import RequestException
from offline_storage import OfflineStorage

logger = logging.getLogger(__name__)

class SoapClient:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings = self._load_settings(settings_path)
        self.storage = OfflineStorage(settings_path)
        self.checkin_client = None
        self.summary_client = None
        self.credentials = None
        self._is_online = False
        self._connection_error = None
        # Try initial setup but don't block on failure
        try:
            self.setup_client()
        except Exception as e:
            logger.warning(f"Initial connection failed, starting in offline mode: {e}")
            self._connection_error = str(e)
        
    def _load_settings(self, settings_path: str) -> Dict[str, Any]:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def setup_client(self) -> bool:
        """Initialize SOAP clients for both services
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Base transport settings with optimized configuration
            from requests import Session
            session = Session()
            
            # Configure session for better performance
            session.headers = {
                'Connection': 'keep-alive',  # Use persistent connections
                'Accept-Encoding': 'gzip, deflate',  # Enable compression
                'Cache-Control': 'no-cache'  # Avoid caching issues
            }
            
            # Set timeouts more aggressively
            timeout = min(self.settings['soap']['timeout'], 10)  # Max 10 seconds
            transport = Transport(timeout=timeout, session=session)
            
            # Log transport settings
            logger.debug(f"SOAP transport configured with timeout={timeout}s and keep-alive connections")
            
            # Initialize clients with optimized settings
            base_url = f"{self.settings['soap']['endpoint']}Services"
            
            # Add performance logging
            import time
            start_time = time.time()
            
            # Initialize clients with simpler configuration
            self.checkin_client = Client(
                f'{base_url}/MSIWebTraxCheckIn.asmx?WSDL',
                transport=transport
            )
            
            checkin_time = time.time()
            logger.debug(f"CheckIn client initialized in {checkin_time - start_time:.2f}s")
            
            self.summary_client = Client(
                f'{base_url}/MSIWebTraxCheckInSummary.asmx?WSDL',
                transport=transport
            )
            
            summary_time = time.time()
            logger.debug(f"Summary client initialized in {summary_time - checkin_time:.2f}s")
            
            # Prepare credentials as a SOAP header
            header = zeep.xsd.Element(
                '{http://msiwebtrax.com/}UserCredentials',
                zeep.xsd.ComplexType([
                    zeep.xsd.Element(
                        '{http://msiwebtrax.com/}UserName',
                        zeep.xsd.String()
                    ),
                    zeep.xsd.Element(
                        '{http://msiwebtrax.com/}PWD',
                        zeep.xsd.String()
                    )
                ])
            )
            self.credentials = header(
                UserName=self.settings['soap']['username'],
                PWD=self.settings['soap']['password']
            )
            
            # Test connection by checking if we can access both services
            try:
                # Check if required operations exist in both services
                summary_ops = self.summary_client.service._operations
                checkin_ops = self.checkin_client.service._operations
                
                if 'RecordSwipeSummary' in summary_ops and 'RecordSwipe' in checkin_ops:
                    self._is_online = True
                    self._connection_error = None
                    logger.info("Successfully connected to SOAP services")
                    return True
                else:
                    missing = []
                    if 'RecordSwipeSummary' not in summary_ops:
                        missing.append('RecordSwipeSummary')
                    if 'RecordSwipe' not in checkin_ops:
                        missing.append('RecordSwipe')
                    error = f"Required SOAP operations not found: {', '.join(missing)}"
                    logger.warning(error)
                    self._connection_error = error
                    return False
            except Exception as e:
                logger.warning(f"Connection test failed: {e}")
                self._connection_error = str(e)
                return False
            
        except Exception as e:
            logger.error(f"Failed to initialize SOAP clients: {e}")
            self._connection_error = str(e)
            return False

    def is_online(self) -> bool:
        """Check if service is currently online"""
        return self._is_online

    def get_connection_error(self) -> Optional[str]:
        """Get the last connection error message"""
        return self._connection_error

    def try_reconnect(self) -> bool:
        """Attempt to reconnect to the service
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        logger.info("Attempting to reconnect to SOAP service")
        return self.setup_client()

    # Track repeated punch attempts
    _recent_punches = {}
    
    def record_punch(self, employee_id: str, punch_time: datetime,
                    department_override: Optional[int] = None, image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Record a punch for an employee, handling both online and offline scenarios
        
        Args:
            employee_id: Employee's ID number
            punch_time: Timestamp for the punch
            department_override: Optional department code
            
        Sends: "{employee_id}|*|{punch_time}|*|{department_override}"
        
        Returns response containing:
            - PunchSuccess: Whether punch was recorded
            - PunchType: "checkin" or "checkout"
            - FirstName: Employee's first name
            - LastName: Employee's last name
            - PunchException: Any punch exceptions
            - WeeklyHours: Current week's hours (if available)
        """
        try:
            # Check for repeated punches in a short time window
            import time
            current_time = time.time()
            
            # If this employee ID has been punched recently and failed with exception 2,
            # don't retry immediately to prevent potential system overload
            if employee_id in SoapClient._recent_punches:
                last_attempt, exception_code = SoapClient._recent_punches[employee_id]
                time_diff = current_time - last_attempt
                
                # If less than 5 seconds have passed since the last attempt with exception 2,
                # return the cached response to prevent rapid retries
                if time_diff < 5.0 and exception_code == 2:
                    logger.warning(f"Throttling repeated punch for {employee_id} - last attempt was {time_diff:.2f} seconds ago with exception {exception_code}")
                    return {
                        'success': False,
                        'offline': False,
                        'message': 'Not Authorized. No punch recorded. (Throttled)',
                        'exception': 2,
                        'firstName': None,
                        'lastName': None
                    }
            
            # Format the swipe input string
            swipe_input = f"{employee_id}|*|{punch_time.isoformat()}"
            if department_override:
                swipe_input += f"|*|{department_override}"
                
            # Log punch attempt
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
            logger.info(f"PUNCH SEND: {employee_id}, {punch_time.isoformat()}, {filename}")

            # If we're offline, try to reconnect first
            if not self._is_online:
                logger.info("Attempting to reconnect before processing punch")
                if self.try_reconnect():
                    logger.info("Successfully reconnected")
                else:
                    logger.info("Reconnection failed, storing punch locally")
                    return self._store_offline_punch(employee_id, punch_time, image_data)

            # If we're still missing clients after reconnect attempt, store offline
            if not self.summary_client or not self.credentials:
                logger.info("Missing SOAP clients, storing punch locally")
                return self._store_offline_punch(employee_id, punch_time, image_data)

            # Try online punch with timeout protection and performance tracking
            try:
                # Create the request with proper header
                import threading
                import time
                
                response_container = [None]
                exception_container = [None]
                timing_data = {'start': 0, 'end': 0, 'soap_start': 0, 'soap_end': 0}
                
                # Record start time
                timing_data['start'] = time.time()
                
                def soap_call():
                    try:
                        # Record SOAP call start time
                        timing_data['soap_start'] = time.time()
                        
                        # Pre-warm DNS and connection
                        try:
                            import socket
                            endpoint = self.settings['soap']['endpoint'].replace('https://', '').replace('http://', '').split('/')[0]
                            socket.gethostbyname(endpoint)
                            logger.debug(f"DNS lookup for {endpoint} completed")
                        except Exception as e:
                            logger.debug(f"DNS pre-warm failed: {e}")
                        
                        # Make the actual SOAP call
                        if department_override:
                            response_container[0] = self.summary_client.service.RecordSwipeSummaryDepartmentOverride(
                                _soapheaders=[self.credentials],
                                swipeInput=swipe_input
                            )
                        else:
                            response_container[0] = self.summary_client.service.RecordSwipeSummary(
                                _soapheaders=[self.credentials],
                                swipeInput=swipe_input
                            )
                        
                        # Record SOAP call end time
                        timing_data['soap_end'] = time.time()
                    except Exception as e:
                        timing_data['soap_end'] = time.time()
                        exception_container[0] = e
                
                # Run SOAP call in a thread with a timeout
                soap_thread = threading.Thread(target=soap_call)
                soap_thread.daemon = True
                soap_thread.start()
                
                # Use a shorter timeout for better responsiveness
                timeout = min(self.settings['soap'].get('timeout', 10.0), 8.0)  # Max 8 seconds
                soap_thread.join(timeout=timeout)
                
                # Record end time
                timing_data['end'] = time.time()
                
                # Calculate timing information
                total_time = timing_data['end'] - timing_data['start']
                
                if soap_thread.is_alive():
                    # Thread is still running after timeout
                    logger.error(f"SOAP call timed out for {employee_id} after {total_time:.2f}s")
                    self._is_online = False
                    self._connection_error = f"SOAP call timed out after {total_time:.2f}s"
                    return self._store_offline_punch(employee_id, punch_time, image_data)
                
                if exception_container[0]:
                    # Thread encountered an exception
                    logger.error(f"SOAP call failed for {employee_id} after {total_time:.2f}s: {exception_container[0]}")
                    raise exception_container[0]
                
                if response_container[0] is None:
                    # No response but no exception either
                    logger.error(f"SOAP call returned no response for {employee_id} after {total_time:.2f}s")
                    self._is_online = False
                    self._connection_error = "SOAP call returned no response"
                    return self._store_offline_punch(employee_id, punch_time, image_data)
                
                # Calculate SOAP call time if available
                if timing_data['soap_start'] > 0 and timing_data['soap_end'] > 0:
                    soap_time = timing_data['soap_end'] - timing_data['soap_start']
                    logger.info(f"SOAP call for {employee_id} completed in {soap_time:.2f}s (total time: {total_time:.2f}s)")
                else:
                    logger.info(f"SOAP call for {employee_id} completed in {total_time:.2f}s")
                
                # Successful punch, we're definitely online
                self._is_online = True
                self._connection_error = None
                response = self._format_response(response_container[0], True, employee_id)
                
                # Store this punch attempt with its exception code (if any)
                exception_code = response.get('exception', None)
                SoapClient._recent_punches[employee_id] = (current_time, exception_code)
                
                return response

            except (Fault, TransportError, RequestException) as e:
                logger.warning(f"Online punch failed, storing offline: {e}")
                self._is_online = False
                self._connection_error = str(e)
                return self._store_offline_punch(employee_id, punch_time, image_data)

        except Exception as e:
            logger.error(f"Error recording punch: {e}")
            raise

    def _upload_image(self, employee_id: str, image_data: bytes,
                     punch_time: datetime) -> bool:
        """Upload captured image to the server
        
        Args:
            employee_id: Employee's ID number
            image_data: JPEG image as bytes
            punch_time: Timestamp for the photo
            
        Sends:
            - fileName: "{employee_id}__{timestamp}.jpg"
            - data: JPEG image bytes
            - dir: Client ID for storage directory
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        # If we're offline or missing clients, don't attempt upload
        if not self._is_online or not self.checkin_client or not self.credentials:
            logger.info("System is offline, skipping image upload")
            return False

        try:
            import time
            start_time = time.time()
            
            # Check if image needs to be optimized
            try:
                import io
                from PIL import Image
                
                # Only optimize if image is larger than 100KB
                if len(image_data) > 100 * 1024:
                    logger.debug(f"Optimizing image for {employee_id} (original size: {len(image_data)/1024:.1f}KB)")
                    
                    # Load image
                    img = Image.open(io.BytesIO(image_data))
                    
                    # Determine if resizing is needed
                    max_dimension = 800  # Maximum width or height
                    width, height = img.size
                    
                    if width > max_dimension or height > max_dimension:
                        # Calculate new dimensions while maintaining aspect ratio
                        if width > height:
                            new_width = max_dimension
                            new_height = int(height * (max_dimension / width))
                        else:
                            new_height = max_dimension
                            new_width = int(width * (max_dimension / height))
                            
                        # Resize image
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
                    
                    # Save optimized image to bytes
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    optimized_data = output.getvalue()
                    
                    # Only use optimized image if it's actually smaller
                    if len(optimized_data) < len(image_data):
                        logger.debug(f"Optimized image size: {len(optimized_data)/1024:.1f}KB (saved {(1 - len(optimized_data)/len(image_data))*100:.1f}%)")
                        image_data = optimized_data
                    else:
                        logger.debug("Optimization did not reduce image size, using original")
            except Exception as e:
                logger.warning(f"Image optimization failed: {e}")
            
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
            client_id = str(self.settings['soap']['clientId'])
            
            # Use threading with timeout for image upload
            import threading
            response_container = [None]
            exception_container = [None]
            timing_data = {'soap_start': 0, 'soap_end': 0}
            
            def upload_call():
                try:
                    timing_data['soap_start'] = time.time()
                    response_container[0] = self.checkin_client.service.SaveImage(
                        _soapheaders=[self.credentials],
                        fileName=filename,
                        data=image_data,
                        dir=client_id
                    )
                    timing_data['soap_end'] = time.time()
                except Exception as e:
                    timing_data['soap_end'] = time.time()
                    exception_container[0] = e
            
            # Run upload in a thread with a timeout
            upload_thread = threading.Thread(target=upload_call)
            upload_thread.daemon = True
            upload_thread.start()
            
            # Use a shorter timeout for image upload
            timeout = min(self.settings['soap'].get('timeout', 10.0), 5.0)  # Max 5 seconds for image upload
            upload_thread.join(timeout=timeout)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            if upload_thread.is_alive():
                # Thread is still running after timeout
                logger.error(f"Image upload timed out for {employee_id} after {total_time:.2f}s")
                self._is_online = False
                self._connection_error = f"Image upload timed out after {total_time:.2f}s"
                return False
            
            if exception_container[0]:
                # Thread encountered an exception
                logger.error(f"Image upload failed for {employee_id} after {total_time:.2f}s: {exception_container[0]}")
                self._is_online = False
                self._connection_error = str(exception_container[0])
                return False
            
            if response_container[0] is None:
                # No response but no exception either
                logger.error(f"Image upload returned no response for {employee_id} after {total_time:.2f}s")
                self._is_online = False
                self._connection_error = "Image upload returned no response"
                return False
            
            # Calculate SOAP call time if available
            if timing_data['soap_start'] > 0 and timing_data['soap_end'] > 0:
                soap_time = timing_data['soap_end'] - timing_data['soap_start']
                logger.info(f"Image upload for {employee_id} completed in {soap_time:.2f}s (total time: {total_time:.2f}s)")
            else:
                logger.info(f"Image upload for {employee_id} completed in {total_time:.2f}s")
            
            # Successful upload means we're definitely online
            self._is_online = True
            self._connection_error = None
            
            # Check for system error codes
            response = response_container[0]
            if hasattr(response, 'SystemErrorCode'):
                error_code = response.SystemErrorCode
                if error_code:
                    logger.error(f"SaveImage error code: {error_code}")
                    return False
            
            return True if response else False
                
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return False

    def _store_offline_punch(self, employee_id: str, punch_time: datetime,
                           image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """Store punch data locally when offline"""
        try:
            # Generate the filename that will be used when uploading the image
            filename = None
            if image_data:
                filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                # Save image to photos directory
                os.makedirs('photos', exist_ok=True)
                with open(os.path.join('photos', filename), 'wb') as f:
                    f.write(image_data)
                logger.debug(f"Storing offline punch with image: {employee_id}, filename: {filename}")
            else:
                logger.debug(f"Storing offline punch without image: {employee_id}")
            
            return self.storage.store_punch(
                employee_id=employee_id,
                punch_time=punch_time,
                punch_type='OFFLINE',
                image_filename=filename
            )
            
        except Exception as e:
            logger.error(f"Failed to store offline punch: {e}")
            raise

    def sync_offline_punches(self) -> Dict[str, Any]:
        """Attempt to sync stored offline punches"""
        try:
            # If we're offline, try to reconnect first
            if not self._is_online:
                logger.info("Attempting to reconnect before syncing offline punches")
                if not self.try_reconnect():
                    logger.warning("Failed to reconnect, skipping sync")
                    return {
                        'total': 0,
                        'synced': 0,
                        'failed': 0,
                        'error': self._connection_error
                    }

            unsynced_punches = self.storage.get_unsynced_punches()
            results = {
                'total': len(unsynced_punches),
                'synced': 0,
                'failed': 0,
                'error': None
            }

            if not unsynced_punches:
                logger.debug("No offline punches to sync")
                return results
            
            for punch in unsynced_punches:
                try:
                    punch_id = punch['id']
                    employee_id = punch['employeeId']
                    punch_datetime = datetime.fromisoformat(punch['punchTime'])
                    image_filename = punch.get('imageFilename')
                    
                    # Attempt to sync the punch
                    response = self.record_punch(
                        employee_id=employee_id,
                        punch_time=punch_datetime
                    )
                    
                    if response.get('success') and not response.get('offline'):
                        # If punch was successful and we have an image file, upload it
                        if image_filename:
                            image_path = os.path.join('photos', image_filename)
                            if os.path.exists(image_path):
                                try:
                                    with open(image_path, 'rb') as f:
                                        image_data = f.read()
                                    
                                    upload_response = self.checkin_client.service.SaveImage(
                                        _soapheaders=[self.credentials],
                                        fileName=image_filename,
                                        data=image_data,
                                        dir=str(self.settings['soap']['clientId'])
                                    )
                                    
                                    if upload_response:
                                        logger.info(f"Successfully uploaded image for synced punch: {employee_id}, {image_filename}")
                                    else:
                                        logger.warning(f"Failed to upload image for synced punch: {employee_id}, {image_filename}")
                                except Exception as e:
                                    logger.error(f"Error uploading image for synced punch: {employee_id}, {image_filename}, error: {e}")
                            else:
                                logger.warning(f"Image file not found for synced punch: {image_filename}")
                        
                        # Mark punch as synced
                        self.storage.mark_as_synced(punch_id)
                        results['synced'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync punch {punch_id}: {e}")
                    results['failed'] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync offline punches: {e}")
            raise

    def _format_response(self, soap_response: Any, online: bool = True, employee_id: Optional[str] = None) -> Dict[str, Any]:
        """Format the SOAP response into a standardized dictionary"""
        # Log the raw SOAP response at DEBUG level
        if online and soap_response:
            logger.debug(f"RAW SOAP RESPONSE: employee_id={employee_id}, response_type={type(soap_response).__name__}")
            # Log all attributes of RecordSwipeReturnInfo if it exists
            if hasattr(soap_response, 'RecordSwipeReturnInfo'):
                attrs = vars(soap_response.RecordSwipeReturnInfo)
                logger.debug(f"SOAP RESPONSE ATTRIBUTES: {', '.join(f'{k}={v}' for k, v in attrs.items())}")
        
        if not online:
            return {
                'success': True,
                'offline': True,
                'message': 'Punch stored offline'
            }

        # Check for system error codes
        if hasattr(soap_response.RecordSwipeReturnInfo, 'SystemErrorCode'):
            error_code = soap_response.RecordSwipeReturnInfo.SystemErrorCode
            # Log raw error code at DEBUG level for debugging
            logger.debug(f"SOAP RAW ERROR CODE: {error_code}, type: {type(error_code).__name__}, employee_id: {employee_id}")
            error_messages = {
                '-1': 'Connection not secure',
                '-2': 'Input parameters not found',
                '-3': 'Client not authorized',
                '-4': 'Invalid input parameter format',
                '-5': 'Too few input parameters',
                '-6': 'Invalid date'
            }
            if error_code in error_messages:
                logger.error(f"SOAP error: {error_messages[error_code]} (code: {error_code})")
                return {
                    'success': False,
                    'offline': False,
                    'message': error_messages[error_code],
                    'error_code': error_code
                }

        # Log punch exceptions at INFO level
        if hasattr(soap_response.RecordSwipeReturnInfo, 'PunchException') and soap_response.RecordSwipeReturnInfo.PunchException:
            exception_code = soap_response.RecordSwipeReturnInfo.PunchException
            
            # Get the exception message if available
            from punch_exceptions import PunchExceptions
            exception_msg = PunchExceptions.get_message(exception_code)
            
            # Log at INFO level so it's visible in normal operation
            logger.info(f"PUNCH EXCEPTION: {employee_id}, exception={exception_code}")
            
            if exception_msg:
                eng_msg, esp_msg, status_color = exception_msg
                logger.info(f"PUNCH EXCEPTION DETAILS: {eng_msg} ({status_color})")
                
                # For exception code 2 (Not Authorized), add more detailed logging
                if exception_code == 2:
                    logger.warning(f"Not Authorized exception for {employee_id} - This may indicate an invalid employee ID or permissions issue")
            
        response = {
            'success': soap_response.RecordSwipeReturnInfo.PunchSuccess,
            'offline': False,
            'punchType': soap_response.RecordSwipeReturnInfo.PunchType,
            'firstName': soap_response.RecordSwipeReturnInfo.FirstName,
            'lastName': soap_response.RecordSwipeReturnInfo.LastName,
            'exception': soap_response.RecordSwipeReturnInfo.PunchException,
            'weeklyHours': soap_response.CurrentWeeklyHours if hasattr(soap_response, 'CurrentWeeklyHours') else None
        }
        
        # Log punch response
        logger.info(
            f"PUNCH RESPONSE: {employee_id}, "
            f"{response['lastName']}, {response['firstName']}, "
            f"{response['success']}, {response['punchType']}, "
            f"{response['weeklyHours'] if response['weeklyHours'] is not None else 'N/A'}"
        )
        
        return response

    def cleanup_old_records(self) -> int:
        """Remove old offline records based on retention policy"""
        try:
            retention_days = self.settings['storage']['retentionDays']
            return self.storage.cleanup_old_records(retention_days)
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise