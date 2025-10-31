#!/usr/bin/env python3
"""
Test the user management system and login functionality
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.user_management import UserDatabase

def test_user_management():
    """Test user management functionality"""
    print("Testing User Management System...")
    
    # Initialize user database
    user_db = UserDatabase()
    
    # Test admin user creation
    admin_user = user_db.get_user('admin')
    if admin_user:
        print(f"✓ Admin user exists: {admin_user.username}")
        print(f"  - Role: {admin_user.role}")
        print(f"  - Assigned cameras: {admin_user.assigned_cameras}")
    else:
        print("✗ Admin user not found")
        return False
    
    # Test password verification
    if user_db.verify_password('admin', 'admin@123'):
        print("✓ Admin password verification successful")
    else:
        print("✗ Admin password verification failed")
        return False
    
    # Test creating a subadmin user
    success = user_db.create_user(
        user_id='test_user',
        username='test_subadmin',
        password_hash=user_db._hash_password('test123'),
        role='subadmin',
        assigned_cameras=[0, 1]
    )
    
    if success:
        print("✓ Test subadmin user created successfully")
    else:
        print("✗ Failed to create test subadmin user")
        return False
    
    # Test getting subadmin user
    test_user = user_db.get_user('test_user')
    if test_user:
        print(f"✓ Test user retrieved: {test_user.username}")
        print(f"  - Role: {test_user.role}")
        print(f"  - Assigned cameras: {test_user.assigned_cameras}")
    else:
        print("✗ Test user not found")
        return False
    
    # Test getting all subadmins
    subadmins = user_db.get_all_subadmins()
    print(f"✓ Found {len(subadmins)} subadmin users")
    
    # Clean up - delete test user
    user_db.delete_user('test_user')
    print("✓ Test user cleaned up")
    
    return True

def test_database_creation():
    """Test database creation and initialization"""
    print("\nTesting Database Creation...")
    
    # Check if database file exists
    db_path = Path("data/users.db")
    if db_path.exists():
        print("✓ User database file exists")
    else:
        print("✗ User database file not found")
        return False
    
    # Check if database is accessible
    try:
        user_db = UserDatabase()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("=" * 50)
    print("NetraSena User Management System Test")
    print("=" * 50)
    
    success = True
    
    # Test 1: Database creation
    if not test_database_creation():
        success = False
    
    # Test 2: User management
    if not test_user_management():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\nSystem is ready for role-based access control!")
        print("\nDefault admin credentials:")
        print("  Username: admin")
        print("  Password: admin@123")
        print("\nTo run the secure application:")
        print("  python main_secure.py")
    else:
        print("✗ Some tests failed!")
        print("Please check the errors above.")
    
    print("=" * 50)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
