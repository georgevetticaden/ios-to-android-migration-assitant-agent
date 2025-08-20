#!/usr/bin/env python3
"""
Clear saved Google OAuth tokens (Gmail only now)
Use this when you need to re-authenticate
"""

import os
from pathlib import Path

def clear_tokens():
    """Remove saved Google OAuth tokens"""
    token_dir = Path.home() / '.ios_android_migration'
    
    tokens = [
        token_dir / 'gmail_token.pickle',
        # Legacy tokens from old approach
        token_dir / 'google_photos_token.pickle',
        token_dir / 'google_photos_token_2025.pickle',
        token_dir / 'google_photos_2025.pickle',
        token_dir / 'google_photos_baseline.json',
        token_dir / 'token.pickle'
    ]
    
    print("Clearing Google OAuth tokens...")
    
    found_any = False
    for token_file in tokens:
        if token_file.exists():
            token_file.unlink()
            print(f"  ✅ Removed: {token_file.name}")
            found_any = True
    
    if not found_any:
        print("  ℹ️  No tokens found to clear")
    else:
        print("\n✅ Tokens cleared. Next run will require fresh authorization.")

if __name__ == "__main__":
    clear_tokens()