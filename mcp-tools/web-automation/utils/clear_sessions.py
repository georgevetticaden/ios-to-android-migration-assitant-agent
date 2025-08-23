#!/usr/bin/env python3
"""
Utility to clear saved sessions for fresh testing
"""
import os
import shutil
from pathlib import Path

def clear_sessions():
    """Clear all saved session data"""
    
    sessions_to_clear = [
        # iCloud session
        Path.home() / ".icloud_session",
        # Google session
        Path.home() / ".google_session",
        # Gmail token
        Path.home() / ".ios_android_migration" / "gmail_token.pickle",
    ]
    
    print("Session Cleanup Utility")
    print("=" * 50)
    
    for session_path in sessions_to_clear:
        if session_path.exists():
            if session_path.is_file():
                print(f"Found file: {session_path}")
                response = input(f"Delete {session_path.name}? (y/n): ").strip().lower()
                if response == 'y':
                    os.remove(session_path)
                    print(f"✅ Deleted: {session_path}")
                else:
                    print(f"⏭️  Skipped: {session_path}")
            else:
                print(f"Found directory: {session_path}")
                response = input(f"Delete {session_path.name} directory? (y/n): ").strip().lower()
                if response == 'y':
                    shutil.rmtree(session_path)
                    print(f"✅ Deleted: {session_path}")
                else:
                    print(f"⏭️  Skipped: {session_path}")
        else:
            print(f"❌ Not found: {session_path}")
    
    print("\n" + "=" * 50)
    print("Session cleanup complete!")
    print("Next login will require full authentication.")

if __name__ == "__main__":
    clear_sessions()