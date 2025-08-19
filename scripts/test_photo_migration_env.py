#!/usr/bin/env python3.11
"""
Test that photo-migration tool can load environment from root .env
Quick verification that the consolidation worked correctly
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def test_env_loading():
    """Test that environment variables are loaded from root .env"""
    print("\n" + "="*60)
    print("Photo Migration Environment Test")
    print("="*60)
    
    # Load env using same method as photo-migration
    from dotenv import load_dotenv
    root_dir = Path(__file__).parent.parent
    env_file = root_dir / '.env'
    
    print(f"\n📁 Loading .env from: {env_file}")
    
    if not env_file.exists():
        print(f"❌ .env file not found at {env_file}")
        print("\nPlease create .env file at project root with:")
        print("  APPLE_ID=your.email@icloud.com")
        print("  APPLE_PASSWORD=your_password")
        return False
    
    # Load the environment
    load_dotenv(env_file)
    
    # Check for required variables
    apple_id = os.getenv('APPLE_ID')
    apple_password = os.getenv('APPLE_PASSWORD')
    
    print("\n🔍 Checking environment variables:")
    
    if apple_id:
        print(f"  ✅ APPLE_ID found: {apple_id[:3]}***")
    else:
        print(f"  ❌ APPLE_ID not found")
    
    if apple_password:
        print(f"  ✅ APPLE_PASSWORD found: ***")
    else:
        print(f"  ❌ APPLE_PASSWORD not found")
    
    # Check new shared infrastructure variables
    migration_db = os.getenv('MIGRATION_DB_PATH')
    log_level = os.getenv('LOG_LEVEL')
    
    print("\n📦 Shared infrastructure variables:")
    print(f"  MIGRATION_DB_PATH: {migration_db or 'Not set (will use default)'}")
    print(f"  LOG_LEVEL: {log_level or 'Not set (will use default)'}")
    
    # Test that photo-migration modules can be imported
    print("\n📚 Testing photo-migration imports:")
    try:
        # Add photo-migration src to path for imports
        import sys
        photo_migration_src = root_dir / 'mcp-tools' / 'photo-migration' / 'src'
        if str(photo_migration_src) not in sys.path:
            sys.path.insert(0, str(photo_migration_src))
        
        from photo_migration import icloud_client
        print("  ✅ Can import icloud_client")
        
        from photo_migration import server
        print("  ✅ Can import server")
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    
    # Overall result
    if apple_id and apple_password:
        print("\n" + "="*60)
        print("✅ Photo-migration environment is correctly configured!")
        print("\nYou can now run:")
        print("  cd mcp-tools/photo-migration")
        print("  python test_client.py")
        print("="*60)
        return True
    else:
        print("\n" + "="*60)
        print("⚠️  Missing required credentials")
        print("\nPlease ensure your root .env file contains:")
        print("  APPLE_ID=your.email@icloud.com")
        print("  APPLE_PASSWORD=your_password")
        print("="*60)
        return False

if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)