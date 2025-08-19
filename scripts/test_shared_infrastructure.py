#!/usr/bin/env python3.11
"""
Test the shared infrastructure components
Verifies that all shared modules are working correctly
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Test that all shared modules can be imported"""
    print("\n📦 Testing module imports...")
    
    try:
        # Test database import
        from shared.database import get_migration_db
        print("  ✅ Database module imported")
        
        # Test config import
        from shared.config import get_settings
        print("  ✅ Config module imported")
        
        # Test utils import
        from shared.utils import CredentialManager, setup_logging
        print("  ✅ Utils module imported")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_settings():
    """Test settings configuration"""
    print("\n⚙️  Testing settings configuration...")
    
    try:
        from shared.config import get_settings
        settings = get_settings()
        
        print(f"  📁 Database path: {settings.MIGRATION_DB_PATH}")
        print(f"  📁 Session dir: {settings.ICLOUD_SESSION_DIR}")
        print(f"  📁 Log dir: {settings.LOG_DIR}")
        print(f"  📊 Log level: {settings.LOG_LEVEL}")
        
        # Check if Apple credentials are configured
        if settings.APPLE_ID:
            print(f"  ✅ Apple ID configured: {settings.APPLE_ID[:3]}***")
        else:
            print(f"  ⚠️  Apple ID not configured (set APPLE_ID in .env)")
        
        return True
    except Exception as e:
        print(f"  ❌ Settings error: {e}")
        return False

def test_logging():
    """Test logging configuration"""
    print("\n📝 Testing logging configuration...")
    
    try:
        from shared.utils import setup_logging
        
        # Create a test logger
        logger = setup_logging(name='test', file=False)
        logger.info("Test log message")
        print("  ✅ Logger created and tested")
        
        return True
    except Exception as e:
        print(f"  ❌ Logging error: {e}")
        return False

def test_database_connection():
    """Test database connection (without creating schemas)"""
    print("\n🗄️  Testing database connection...")
    
    try:
        from shared.database import get_migration_db
        
        # Get database instance
        db = get_migration_db()
        print(f"  📁 Database path: {db.db_path}")
        
        # Test connection
        with db.get_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            if result[0] == 1:
                print("  ✅ Database connection successful")
                return True
            else:
                print("  ❌ Database query failed")
                return False
                
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def main():
    """Run all infrastructure tests"""
    print("\n" + "="*60)
    print("Shared Infrastructure Test Suite")
    print("="*60)
    
    # Track test results
    all_passed = True
    
    # Run tests
    if not test_imports():
        all_passed = False
    
    if not test_settings():
        all_passed = False
    
    if not test_logging():
        all_passed = False
    
    if not test_database_connection():
        all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ All infrastructure tests passed!")
        print("\nNext steps:")
        print("1. Run 'python scripts/setup_database.py' to initialize the database")
        print("2. Configure your .env file with credentials")
        print("3. Start implementing the photo migration extensions")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)