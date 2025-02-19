import sys
import logging
import json
from camera_service import CameraService
from soap_client import SoapClient
from datetime import datetime

def test_camera():
    print("\nTesting Camera Service...")
    try:
        camera = CameraService()
        results = camera.test_camera()
        print("Camera Test Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Camera test failed: {e}")
    finally:
        camera.cleanup()

def test_soap():
    print("\nTesting SOAP Connection...")
    try:
        client = SoapClient()
        # Test connection by attempting to sync (which won't do anything if no offline records exist)
        results = client.sync_offline_punches()
        print("SOAP Connection Test Results:")
        print(f"  Connection established: {'Yes' if results else 'No'}")
    except Exception as e:
        print(f"SOAP test failed: {e}")

def test_settings():
    print("\nTesting Settings File...")
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        print("Settings validation:")
        # Check required settings
        required_sections = ['soap', 'camera', 'ui', 'storage', 'logging']
        for section in required_sections:
            print(f"  {section}: {'Present' if section in settings else 'Missing'}")
    except Exception as e:
        print(f"Settings test failed: {e}")

def main():
    print("MSI Time Clock Component Test\n" + "="*30)
    
    # Test settings first
    test_settings()
    
    # Test SOAP connection
    test_soap()
    
    # Test camera
    test_camera()

if __name__ == "__main__":
    main()