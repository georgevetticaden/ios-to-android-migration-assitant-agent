#!/usr/bin/env python3
"""
Setup Google Session for Headless Operations

This script creates and saves a Google session that can be used
by the headless Google Storage client. Run this once to authenticate,
and the session will be valid for about 7 days.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright

async def setup_google_session():
    """Setup and save Google session for headless operations"""
    
    session_dir = Path.home() / '.google_session'
    session_dir.mkdir(exist_ok=True)
    session_file = session_dir / 'session_state.json'
    
    print("=" * 60)
    print("GOOGLE SESSION SETUP")
    print("=" * 60)
    print()
    print("This will open a browser window for you to login to Google.")
    print("Once logged in, the session will be saved for headless use.")
    print()
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with saved session if it exists
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        if session_file.exists():
            print("Found existing session, loading...")
            with open(session_file, 'r') as f:
                storage_state = json.load(f)
            context_options['storage_state'] = storage_state
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        # Navigate to Google One Storage
        print("Navigating to Google One Storage...")
        await page.goto('https://one.google.com/storage')
        
        # Wait for user to login if needed
        print()
        print("Please login to your Google account if prompted.")
        print("Once you see your storage information, press Enter here...")
        input()
        
        # Verify we're logged in by checking for storage info
        try:
            await page.wait_for_selector('text=/GB of.*TB used/', timeout=5000)
            print("✅ Successfully logged in!")
            
            # Save the session
            state = await context.storage_state()
            with open(session_file, 'w') as f:
                json.dump(state, f)
            
            # Save session metadata
            info_file = session_dir / 'session_info.json'
            info = {
                'saved_at': datetime.now().isoformat(),
                'email': os.getenv('GOOGLE_EMAIL', 'unknown')
            }
            with open(info_file, 'w') as f:
                json.dump(info, f)
            
            print(f"✅ Session saved to: {session_file}")
            print("✅ This session will work for ~7 days")
            print()
            print("You can now run tests in headless mode!")
            
        except Exception as e:
            print(f"❌ Failed to verify login: {e}")
            print("Please make sure you're logged in and can see your storage info")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(setup_google_session())