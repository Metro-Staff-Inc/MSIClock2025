import os
import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
import zeep
from zeep import Client, Transport, xsd
from zeep.exceptions import Fault, TransportError
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class SoapClient:
    def __init__(self, settings_path: str = 'settings.json'):
        self.settings = self._load_settings(settings_path)
        self.setup_client()
        
    def _load_settings(self, settings_path: str) -> Dict[str, Any]:
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise

    def setup_client(self):
        """Initialize SOAP clients for both services"""
        try:
            # Base transport settings
            transport = Transport(timeout=self.settings['soap']['timeout'])
            
            # Initialize clients for both services
            base_url = f"{self.settings['soap']['endpoint']}Services"
            self.checkin_client = Client(
                f'{base_url}/MSIWebTraxCheckIn.asmx?WSDL',
                transport=transport
            )
            self.summary_client = Client(
                f'{base_url}/MSIWebTraxCheckInSummary.asmx?WSDL',
                transport=transport
            )
            
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
            
        except Exception as e:
            logger.error(f"Failed to initialize SOAP clients: {e}")
            raise

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
            # Format the swipe input string
            swipe_input = f"{employee_id}|*|{punch_time.isoformat()}"
            if department_override:
                swipe_input += f"|*|{department_override}"
                
            # Log punch attempt
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
            logger.info(f"PUNCH SEND: {employee_id}, {punch_time.isoformat()}, {filename}")

            # Try online punch first
            try:
                # Create the request with proper header
                if department_override:
                    response = self.summary_client.service.RecordSwipeSummaryDepartmentOverride(
                        _soapheaders=[self.credentials],
                        swipeInput=swipe_input
                    )
                else:
                    response = self.summary_client.service.RecordSwipeSummary(
                        _soapheaders=[self.credentials],
                        swipeInput=swipe_input
                    )
                
                return self._format_response(response, True, employee_id)

            except (Fault, TransportError, RequestException) as e:
                logger.warning(f"Online punch failed, storing offline: {e}")
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
        try:
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
            client_id = str(self.settings['soap']['clientId'])
            
            
            try:
                response = self.checkin_client.service.SaveImage(
                    _soapheaders=[self.credentials],
                    fileName=filename,
                    data=image_data,
                    dir=client_id
                )
                
                # Check for system error codes
                if hasattr(response, 'SystemErrorCode'):
                    error_code = response.SystemErrorCode
                    if error_code:
                        logger.error(f"SaveImage error code: {error_code}")
                        return False
                
                return True if response else False
                
            except Exception as e:
                logger.error(f"SaveImage SOAP call failed: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return False

    def _store_offline_punch(self, employee_id: str, punch_time: datetime,
                           image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """Store punch data locally when offline"""
        try:
            db_path = self.settings['storage']['dbPath']
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Generate the filename that will be used when uploading the image
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg" if image_data else None
            
            # Log whether we have image data
            if image_data:
                logger.debug(f"Storing offline punch with image: {employee_id}, filename: {filename}")
            else:
                logger.debug(f"Storing offline punch without image: {employee_id}")
            
            cursor.execute('''
                INSERT INTO punches (employeeId, punchTime, punchType, imageData, imageFilename)
                VALUES (?, ?, ?, ?, ?)
            ''', (employee_id, punch_time.isoformat(), 'OFFLINE', image_data, filename))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'offline': True,
                'message': 'Punch stored offline',
                'punchType': 'OFFLINE',
                'employeeId': employee_id
            }
        except Exception as e:
            logger.error(f"Failed to store offline punch: {e}")
            raise

    def sync_offline_punches(self) -> Dict[str, Any]:
        """Attempt to sync stored offline punches"""
        try:
            db_path = self.settings['storage']['dbPath']
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all unsynced punches
            cursor.execute('''
                SELECT id, employeeId, punchTime, imageData, imageFilename
                FROM punches
                WHERE synced = 0
                ORDER BY punchTime ASC
            ''')
            
            unsynced_punches = cursor.fetchall()
            results = {
                'total': len(unsynced_punches),
                'synced': 0,
                'failed': 0
            }
            
            for punch in unsynced_punches:
                try:
                    punch_id, employee_id, punch_time, image_data, image_filename = punch
                    punch_datetime = datetime.fromisoformat(punch_time)
                    
                    # Attempt to sync the punch
                    response = self.record_punch(
                        employee_id=employee_id,
                        punch_time=punch_datetime
                    )
                    
                    if response.get('success') and not response.get('offline'):
                        # If punch was successful and we have image data, upload the image
                        if image_data and image_filename:
                            # Use the stored filename and upload the image directly
                            client_id = str(self.settings['soap']['clientId'])
                            
                            try:
                                upload_response = self.checkin_client.service.SaveImage(
                                    _soapheaders=[self.credentials],
                                    fileName=image_filename,
                                    data=image_data,
                                    dir=client_id
                                )
                                
                                if upload_response:
                                    logger.info(f"Successfully uploaded image for synced punch: {employee_id}, {image_filename}")
                                else:
                                    logger.warning(f"Failed to upload image for synced punch: {employee_id}, {image_filename}")
                            except Exception as e:
                                logger.error(f"Error uploading image for synced punch: {employee_id}, {image_filename}, error: {e}")
                        else:
                            # Log when no image data is available
                            if not image_data:
                                logger.debug(f"No image data available for synced punch: {employee_id}")
                            if not image_filename:
                                logger.debug(f"No image filename available for synced punch: {employee_id}")
                        
                        # Mark punch as synced
                        cursor.execute('''
                            UPDATE punches
                            SET synced = 1
                            WHERE id = ?
                        ''', (punch_id,))
                        results['synced'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync punch {punch_id}: {e}")
                    results['failed'] += 1
            
            conn.commit()
            conn.close()
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
            # Log at INFO level so it's visible in normal operation
            logger.info(f"PUNCH EXCEPTION: {employee_id}, exception={soap_response.RecordSwipeReturnInfo.PunchException}")
            
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
            db_path = self.settings['storage']['dbPath']
            retention_days = self.settings['storage']['retentionDays']
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM punches
                WHERE datetime(createdAt) < datetime('now', ?)
            ''', (f'-{retention_days} days',))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise