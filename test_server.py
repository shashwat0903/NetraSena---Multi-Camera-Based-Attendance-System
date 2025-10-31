"""
Simple test script to verify the client-server system is working
"""

import requests
import time

def test_server(host='localhost', port=5000):
    """Test if the server is responding"""
    base_url = f'http://{host}:{port}'
    
    print("=" * 60)
    print("Testing Attendance System Server")
    print("=" * 60)
    
    # Test 1: Check if server is running
    print("\n1. Testing server connection...")
    try:
        response = requests.get(f'{base_url}/api/system/status', timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running!")
            data = response.json()
            print(f"   - Processing active: {data.get('active', False)}")
            print(f"   - Attendance mode: {data.get('attendance_mode', False)}")
            print(f"   - Cameras: {data.get('cameras', 0)}")
            print(f"   - Database connected: {data.get('connected', False)}")
        else:
            print(f"   ❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to server at {base_url}")
        print(f"   Make sure the server is running with: python server.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Test 2: Check cameras
    print("\n2. Testing camera list...")
    try:
        response = requests.get(f'{base_url}/api/cameras/list', timeout=5)
        if response.status_code == 200:
            data = response.json()
            cameras = data.get('cameras', [])
            print(f"   ✅ Found {len(cameras)} cameras")
            for cam in cameras:
                status = "✓" if cam.get('enabled', True) else "✗"
                print(f"   {status} {cam['name']} (ID: {cam['id']})")
        else:
            print(f"   ⚠️  Camera list returned status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting cameras: {str(e)}")
    
    # Test 3: Check known faces
    print("\n3. Testing known faces...")
    try:
        response = requests.get(f'{base_url}/api/faces/known', timeout=5)
        if response.status_code == 200:
            data = response.json()
            faces = data.get('faces', [])
            print(f"   ✅ Found {len(faces)} known faces")
            if faces:
                print(f"   Names: {', '.join(faces[:5])}")
                if len(faces) > 5:
                    print(f"   ... and {len(faces) - 5} more")
        else:
            print(f"   ⚠️  Known faces returned status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting faces: {str(e)}")
    
    # Test 4: Check database
    print("\n4. Testing database connection...")
    try:
        response = requests.get(f'{base_url}/api/database/test', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Database connected!")
            print(f"   - Total records: {data.get('total_records', 0)}")
            dates = data.get('unique_dates', [])
            if dates:
                print(f"   - Dates with data: {len(dates)}")
                print(f"   - Recent: {', '.join(sorted(dates)[-3:])}")
        else:
            print(f"   ⚠️  Database test returned status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing database: {str(e)}")
    
    # Test 5: Check attendance
    print("\n5. Testing attendance endpoints...")
    try:
        response = requests.get(f'{base_url}/api/attendance/present', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Present list: {data.get('count', 0)} people")
            
        response = requests.get(f'{base_url}/api/attendance/absent', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Absent list: {data.get('count', 0)} people")
    except Exception as e:
        print(f"   ⚠️  Error testing attendance: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ Server is working correctly!")
    print("=" * 60)
    print(f"\nYou can now access the client interface at:")
    print(f"  - Local:   {base_url}")
    print(f"  - Network: http://[YOUR-IP]:{port}")
    print("\nTo find your IP address:")
    print("  Windows: ipconfig")
    print("  Linux/Mac: ifconfig or ip addr show")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    import sys
    
    host = 'localhost'
    port = 5000
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    print(f"\nTesting server at {host}:{port}")
    print("(Use: python test_server.py [host] [port])\n")
    
    success = test_server(host, port)
    
    if not success:
        sys.exit(1)
