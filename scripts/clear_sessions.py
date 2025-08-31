#!/usr/bin/env python3
"""
Clear saved authentication sessions for fresh testing.

This utility removes stored sessions for:
- iCloud (.icloud_session)
- Google (.google_session)
- Gmail token (.ios_android_migration/gmail_token.pickle)

Use this when you need to:
- Test fresh authentication flows
- Clear expired sessions
- Switch between different accounts
- Troubleshoot authentication issues
"""
import os
import shutil
from pathlib import Path
import sys

def clear_sessions():
    """Clear all saved session data"""
    
    sessions_to_clear = [
        # iCloud session
        Path.home() / ".icloud_session",
        # Google session
        Path.home() / ".google_session",
        # Gmail token
        Path.home() / ".ios_android_migration" / "gmail_token.pickle",
        # Chrome demo profile (if exists)
        Path("/tmp") / "chrome-demo-profile",
    ]
    
    print("\n" + "=" * 60)
    print("          Session Cleanup Utility")
    print("=" * 60)
    print("\nThis will clear saved authentication sessions.")
    print("You will need to re-authenticate on next use.")
    print("\nSessions to clear:")
    for session in sessions_to_clear[:3]:  # Don't show temp chrome profile in list
        print(f"  • {session}")
    
    print("\n" + "=" * 60)
    
    # Ask for confirmation
    confirm = input("\nDo you want to proceed with clearing sessions? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n❌ Cancelled. No sessions were cleared.")
        sys.exit(0)
    
    print("\nClearing sessions...")
    cleared_count = 0
    
    for session_path in sessions_to_clear:
        if session_path.exists():
            try:
                if session_path.is_file():
                    os.remove(session_path)
                    print(f"  ✅ Cleared: {session_path.name}")
                    cleared_count += 1
                else:
                    shutil.rmtree(session_path)
                    print(f"  ✅ Cleared: {session_path.name} directory")
                    cleared_count += 1
            except Exception as e:
                print(f"  ❌ Error clearing {session_path.name}: {e}")
        else:
            # Don't show "not found" for temp directories
            if "chrome-demo" not in str(session_path):
                print(f"  ⏭️  Not found: {session_path.name}")
    
    print("\n" + "=" * 60)
    if cleared_count > 0:
        print(f"✅ Session cleanup complete! Cleared {cleared_count} session(s).")
        print("📝 Next login will require full authentication.")
    else:
        print("ℹ️  No sessions found to clear.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        clear_sessions()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
        sys.exit(1)