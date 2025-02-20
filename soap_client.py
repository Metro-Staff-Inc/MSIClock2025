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
            
            logger.info("SOAP clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SOAP clients: {e}")
            raise

    def record_punch(self, employee_id: str, punch_time: datetime,
                    department_override: Optional[int] = None) -> Dict[str, Any]:
        """
        Record a punch for an employee, handling both online and offline scenarios
        """
        try:
            # Format the swipe input string
            swipe_input = f"{employee_id}|*|{punch_time.isoformat()}"
            if department_override:
                swipe_input += f"|*|{department_override}"

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
                
                return self._format_response(response, True)

            except (Fault, TransportError, RequestException) as e:
                logger.warning(f"Online punch failed, storing offline: {e}")
                return self._store_offline_punch(employee_id, punch_time, image_data)

        except Exception as e:
            logger.error(f"Error recording punch: {e}")
            raise

    def _upload_image(self, employee_id: str, image_data: bytes, 
                     punch_time: datetime) -> bool:
        """Upload captured image to the server"""
        try:
            filename = f"{employee_id}__{punch_time.strftime('%Y%m%d_%H%M%S')}.jpg"
            client_id = str(self.settings['soap']['clientId'])
            
            logger.info(f"Attempting to save image: {filename}")
            logger.info(f"Client ID directory: {client_id}")
            
            try:
                response = self.checkin_client.service.SaveImage(
                    _soapheaders=[self.credentials],
                    fileName=filename,
                    data=image_data,
                    dir=client_id
                )
                
                # Log the raw response for debugging
                logger.info(f"SaveImage raw response: {response}")
                
                # Check for system error codes
                if hasattr(response, 'SystemErrorCode'):
                    error_code = response.SystemErrorCode
                    if error_code:
                        logger.error(f"SaveImage error code: {error_code}")
                        return False
                
                success = True if response else False
                logger.info(f"Image upload {'successful' if success else 'failed'}")
                return success
                
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
            
            cursor.execute('''
                INSERT INTO punches (employeeId, punchTime, punchType, imageData)
                VALUES (?, ?, ?, ?)
            ''', (employee_id, punch_time.isoformat(), 'OFFLINE', image_data))
            
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
                SELECT id, employeeId, punchTime, imageData
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
                    punch_id, employee_id, punch_time, image_data = punch
                    punch_datetime = datetime.fromisoformat(punch_time)
                    
                    # Attempt to sync the punch
                    response = self.record_punch(
                        employee_id=employee_id,
                        punch_time=punch_datetime,
                        image_data=image_data
                    )
                    
                    if response.get('success') and not response.get('offline'):
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

    def _format_response(self, soap_response: Any, online: bool = True) -> Dict[str, Any]:
        """Format the SOAP response into a standardized dictionary"""
        if not online:
            return {
                'success': True,
                'offline': True,
                'message': 'Punch stored offline'
            }

        # Check for system error codes
        if hasattr(soap_response.RecordSwipeReturnInfo, 'SystemErrorCode'):
            error_code = soap_response.RecordSwipeReturnInfo.SystemErrorCode
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

        return {
            'success': soap_response.RecordSwipeReturnInfo.PunchSuccess,
            'offline': False,
            'punchType': soap_response.RecordSwipeReturnInfo.PunchType,
            'firstName': soap_response.RecordSwipeReturnInfo.FirstName,
            'lastName': soap_response.RecordSwipeReturnInfo.LastName,
            'exception': soap_response.RecordSwipeReturnInfo.PunchException,
            'weeklyHours': soap_response.CurrentWeeklyHours if hasattr(soap_response, 'CurrentWeeklyHours') else None
        }

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
            
            logger.info(f"Cleaned up {deleted_count} old records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise