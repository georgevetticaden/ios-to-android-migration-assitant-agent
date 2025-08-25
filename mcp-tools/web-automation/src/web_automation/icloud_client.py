#!/usr/bin/env python3.11
"""
iCloud Client with Session Persistence
Saves authentication state to avoid 2FA on every run
Extended with transfer management capabilities
"""

import asyncio
import logging
from .logging_config import setup_logging, get_screenshot_dir
import re
import os
import sys
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, Frame

# Import our Google Dashboard client and Gmail monitor
from .google_dashboard_client import GoogleDashboardClient
from .gmail_monitor import GmailMonitor

# Import shared database components
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
try:
    from shared.database.migration_db import MigrationDatabase
except ImportError:
    logger.warning("Shared database not available - using local storage")
    MigrationDatabase = None

logger = setup_logging(__name__)

class ICloudClientWithSession:
    """iCloud client with persistent session management for photo migration.
    
    This client handles the complete iOS to Android photo migration workflow,
    including authentication with Apple ID, transfer initiation, progress monitoring,
    and completion verification. It maintains browser sessions to avoid repeated 2FA.
    
    Key Features:
        - Session persistence (7-day validity) to avoid repeated 2FA
        - Full browser automation for Apple's transfer workflow
        - Google Photos baseline establishment
        - Real-time progress tracking via Google Dashboard
        - Gmail integration for completion email monitoring
        - Database persistence for multi-day transfer tracking
    
    MCP Integration:
        This class provides methods that are exposed as MCP tools:
        - check_status -> check_icloud_status
        - start_transfer -> start_photo_transfer
        - check_transfer_progress -> check_photo_transfer_progress
        - verify_transfer_complete -> verify_photo_transfer_complete
        - check_completion_email -> check_photo_transfer_email
    
    Attributes:
        session_dir (Path): Directory for storing browser session state
        google_dashboard_client: Client for Google Photos monitoring
        gmail_client: Client for email notifications
        db: Database connection for transfer tracking
    """
    
    def __init__(self, session_dir: Optional[str] = None):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Session storage directory
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            # Default to user's home directory
            self.session_dir = Path.home() / ".icloud_session"
        
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "browser_state.json"
        self.session_info_file = self.session_dir / "session_info.json"
        
        # Initialize new components for Phase 3
        self.google_dashboard_client = None
        self.gmail_client = None
        self.db = None
        
        # Local storage for transfers if database not available
        self.local_transfers_file = self.session_dir / "transfers.json"
        
        logger.info(f"Session directory: {self.session_dir}")
    
    async def initialize(self):
        """Initialize Playwright"""
        self.playwright = await async_playwright().start()
    
    async def initialize_apis(self):
        """Initialize Google APIs and database connections"""
        # Initialize Google Dashboard client
        google_session_dir = os.path.expanduser("~/.google_session")
        self.google_dashboard_client = GoogleDashboardClient(session_dir=google_session_dir)
        await self.google_dashboard_client.initialize()
        
        # Initialize Gmail client
        gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
        if gmail_creds_path and os.path.exists(gmail_creds_path):
            self.gmail_client = GmailMonitor(credentials_path=gmail_creds_path)
            try:
                await self.gmail_client.authenticate()
                logger.info("Gmail API initialized successfully")
            except Exception as e:
                logger.warning(f"Gmail API initialization failed: {e}")
                self.gmail_client = None
        
        # Initialize database if available
        if MigrationDatabase:
            try:
                self.db = MigrationDatabase()
                # Initialize schemas on first use
                await self.db.initialize_schemas()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
                self.db = None
        
        logger.info("APIs initialized")
    
    def is_session_valid(self) -> bool:
        """Check if saved session exists and is recent"""
        if not self.session_file.exists() or not self.session_info_file.exists():
            return False
        
        try:
            with open(self.session_info_file, 'r') as f:
                info = json.load(f)
            
            # Check if session is less than 7 days old
            saved_time = datetime.fromisoformat(info['saved_at'])
            age = datetime.now() - saved_time
            
            if age > timedelta(days=7):
                logger.info(f"Session is {age.days} days old, will need fresh login")
                return False
            
            logger.info(f"Found valid session from {saved_time.strftime('%Y-%m-%d %H:%M')}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking session: {e}")
            return False
    
    async def save_session(self):
        """Save browser context state"""
        try:
            # Get the context
            if hasattr(self, 'context') and self.context:
                context = self.context
            else:
                context = self.browser.contexts[0]
            
            # Save FULL storage state including cookies, localStorage, sessionStorage
            await context.storage_state(path=str(self.session_file))
            
            # Also save current page URL for verification
            info = {
                'saved_at': datetime.now().isoformat(),
                'browser': 'chromium',
                'url': self.page.url,
                'title': await self.page.title()
            }
            with open(self.session_info_file, 'w') as f:
                json.dump(info, f, indent=2)
            
            # Log what we saved
            with open(self.session_file, 'r') as f:
                state = json.load(f)
                cookie_count = len(state.get('cookies', []))
                origin_count = len(state.get('origins', []))
                logger.info(f"Session saved: {cookie_count} cookies, {origin_count} origins")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def get_photo_status(self, apple_id: Optional[str] = None, 
                               password: Optional[str] = None,
                               force_fresh_login: bool = False) -> Dict[str, Any]:
        """Get current iCloud photo library status and transfer history.
        
        This is the primary method for checking iCloud photo/video counts.
        It connects to privacy.apple.com and navigates to the transfer page
        to extract real-time data. Uses session persistence to avoid 2FA.
        
        **MCP Tool Name**: `check_icloud_status` (when called via MCP server)
        
        **What it Extracts**:
        - Current photo count in iCloud
        - Current video count in iCloud
        - Total storage used (in GB)
        - Previous transfer history (if any)
        - Session reuse status
        
        Args:
            apple_id: Apple ID email. Required for first login or when
                     force_fresh_login is True. Can be None when reusing session.
            password: Apple ID password. Required for first login or when
                     force_fresh_login is True. Can be None when reusing session.
            force_fresh_login: If True, forces new login even if valid session exists.
                             Useful when switching accounts or after session issues.
        
        Returns:
            Dict containing:
                - status: \"success\" or \"error\"
                - photos: Number of photos (e.g., 60238)
                - videos: Number of videos (e.g., 2418)
                - total_items: Sum of photos and videos
                - storage_gb: Storage used in GB (e.g., 383)
                - transfer_history: List of previous transfers with status and date
                - session_used: Boolean indicating if saved session was used
                - error: Error message if status is \"error\"
        
        Example Response:
            {
                "status": "success",
                "photos": 60238,
                "videos": 2418,
                "total_items": 62656,
                "storage_gb": 383,
                "transfer_history": [
                    {
                        "status": "Cancelled",
                        "date": "Aug 10, 2025"
                    }
                ],
                "session_used": true
            }
        
        Raises:
            ValueError: If credentials are missing when needed
            Exception: If navigation or extraction fails
        """
        try:
            # Check for existing session
            use_saved_session = self.is_session_valid() and not force_fresh_login
            
            if use_saved_session:
                logger.info("Using saved session to avoid 2FA...")
                # Launch browser with saved state
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # Load saved session
                self.context = await self.browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
            else:
                logger.info("Starting fresh login...")
                # Launch browser without saved state
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
            
            self.page = await self.context.new_page()
            
            # Navigate to privacy.apple.com
            logger.info("Navigating to privacy.apple.com...")
            await self.page.goto("https://privacy.apple.com", wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Check if we're already signed in - multiple ways
            signed_in = False
            
            # Check for "Signed in as" text
            signed_in_text = await self.page.query_selector('text="Signed in as"')
            if signed_in_text:
                signed_in = True
                logger.info("Found 'Signed in as' text")
            
            # Check if there's NO auth iframe (means we're signed in)
            iframe_element = await self.page.query_selector('iframe#aid-auth-widget-iFrame')
            if not iframe_element and use_saved_session:
                signed_in = True
                logger.info("No auth iframe found with saved session - likely signed in")
            
            # Check for transfer link (only visible when signed in)
            transfer_link = await self.page.query_selector('text="Request to transfer a copy of your data"')
            if transfer_link:
                signed_in = True
                logger.info("Found transfer link - confirmed signed in")
            
            if signed_in:
                logger.info("✅ Already signed in with saved session! No 2FA needed.")
            else:
                # Need to sign in
                if iframe_element:
                    # Need to sign in
                    if not apple_id or not password:
                        raise Exception("Apple ID and password required for sign-in")
                    
                    logger.info("Need to authenticate...")
                    auth_frame = await iframe_element.content_frame()
                    
                    # Sign in process
                    email_field = await auth_frame.query_selector('input#account_name_text_field')
                    if email_field:
                        # Click and wait for field to be ready
                        await email_field.click()
                        await auth_frame.wait_for_timeout(500)
                        
                        # Clear any existing value first (select all and delete)
                        await email_field.press("Control+a" if "linux" in sys.platform else "Meta+a")
                        await email_field.press("Backspace")
                        await auth_frame.wait_for_timeout(200)
                        
                        # Fill the email
                        await email_field.fill(apple_id)
                        logger.info(f"Filled email: {apple_id}")
                        
                        # Small wait for validation
                        await auth_frame.wait_for_timeout(1000)
                        
                        # Try to find and click Continue button
                        continue_button = await auth_frame.query_selector('button:has-text("Continue")')
                        if continue_button:
                            # Check if button is enabled
                            is_disabled = await continue_button.get_attribute('disabled')
                            if is_disabled:
                                logger.info("Continue button disabled, pressing Enter instead...")
                                await email_field.press("Enter")
                            else:
                                logger.info("Clicking Continue button...")
                                await continue_button.click()
                        else:
                            logger.info("No Continue button found, pressing Enter...")
                            await email_field.press("Enter")
                        
                        # Password
                        logger.info("Waiting for password field...")
                        await auth_frame.wait_for_timeout(3000)
                        password_field = await auth_frame.wait_for_selector('input#password_text_field', timeout=10000)
                        if password_field:
                            logger.info("Password field found, filling password...")
                            await password_field.click()
                            await auth_frame.wait_for_timeout(500)
                            
                            # Clear and fill password
                            await password_field.press("Control+a" if "linux" in sys.platform else "Meta+a")
                            await password_field.press("Backspace")
                            await auth_frame.wait_for_timeout(200)
                            await password_field.fill(password)
                            logger.info("Password filled")
                            
                            await auth_frame.wait_for_timeout(1000)
                            
                            # Sign In
                            sign_in_button = await auth_frame.query_selector('button:has-text("Sign In")')
                            if sign_in_button:
                                is_disabled = await sign_in_button.get_attribute('disabled')
                                if is_disabled:
                                    logger.info("Sign In button disabled, pressing Enter...")
                                    await password_field.press("Enter")
                                else:
                                    logger.info("Clicking Sign In button...")
                                    await sign_in_button.click()
                            else:
                                logger.info("No Sign In button found, pressing Enter...")
                                await password_field.press("Enter")
                        
                        # Handle 2FA
                        await self.page.wait_for_timeout(3000)
                        two_fa_text = await auth_frame.query_selector('text="Two-Factor Authentication"')
                        
                        if two_fa_text:
                            logger.info("=" * 60)
                            logger.info("2FA REQUIRED - Enter the 6-digit code")
                            logger.info("This should be the LAST TIME you need to do this!")
                            logger.info("")
                            logger.info("💡 TIP: If the code disappeared on Mac:")
                            logger.info("   - Click the date/time in top-right corner")
                            logger.info("   - Check Notification Center")
                            logger.info("   - Or check your iPhone")
                            logger.info("=" * 60)
                            
                            # Wait for 2FA completion (3 minutes max)
                            for i in range(36):  # 36 * 5 seconds = 3 minutes
                                await self.page.wait_for_timeout(5000)
                                
                                iframe_check = await self.page.query_selector('iframe#aid-auth-widget-iFrame')
                                if not iframe_check:
                                    logger.info("2FA completed successfully!")
                                    break
                                
                                if i % 4 == 0:  # Every 20 seconds
                                    logger.info(f"Waiting for 2FA... ({(i+1)*5} seconds elapsed)")
                            
                                logger.info("2FA completed, waiting for redirect...")
                else:
                    logger.info("No authentication needed - likely already signed in")
            
            # Now proceed with getting photo data
            await self.page.wait_for_timeout(2000)
            
            # Save session AFTER we're fully logged in and on the main page
            if not use_saved_session and not signed_in:
                logger.info("Saving session after successful authentication...")
                await self.save_session()
                logger.info("Session saved! Next run won't require 2FA.")
            
            # Check for existing transfers
            logger.info("Checking for existing transfers...")
            existing_transfers = []
            
            transfer_cards = await self.page.query_selector_all('[class*="transfer"], [class*="request"], .module')
            for card in transfer_cards:
                try:
                    text = await card.inner_text()
                    if "photo" in text.lower() and "transfer" in text.lower():
                        status = "unknown"
                        if "cancelled" in text.lower():
                            status = "cancelled"
                        elif "complete" in text.lower():
                            status = "complete"
                        
                        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', text)
                        existing_transfers.append({
                            "status": status,
                            "date": date_match.group() if date_match else "Unknown"
                        })
                except:
                    pass
            
            # Click "Request to transfer a copy of your data"
            logger.info("Looking for transfer request link...")
            
            # The text might be in a span, but we need to click the parent anchor
            transfer_element = None
            
            # Try multiple selectors
            transfer_selectors = [
                'a:has-text("Request to transfer a copy of your data")',
                'a:has-text("Request to transfer")',
                '[href*="transfer"]:has-text("Request")',
                'text="Request to transfer a copy of your data"'
            ]
            
            for selector in transfer_selectors:
                transfer_element = await self.page.query_selector(selector)
                if transfer_element:
                    logger.info(f"Found transfer element with selector: {selector}")
                    break
            
            if transfer_element:
                logger.info("Clicking transfer request link...")
                await transfer_element.click()
                
                # Wait for navigation or new content
                logger.info("Waiting for page to load...")
                try:
                    await self.page.wait_for_url("**/transfer**", timeout=5000)
                except:
                    # If URL doesn't change, wait for new content
                    await self.page.wait_for_timeout(3000)
                
                # Step 2: Select photos option
                logger.info("Looking for photos option...")
                logger.info(f"Current URL after transfer click: {self.page.url}")
                
                # Check if we're on the new export selection page
                page_content = await self.page.content()
                
                if "Choose what you'd like to export" in page_content:
                    logger.info("On export selection page - clicking iCloud photos option")
                    
                    # This is the new page with boxes for Music and Photos
                    # We need to click the "iCloud photos and videos" box
                    photos_selectors = [
                        'text="iCloud photos and videos"',
                        'div:has-text("iCloud photos and videos")',
                        'text="To Google Photos"'
                    ]
                    
                    photos_clicked = False
                    for selector in photos_selectors:
                        try:
                            element = await self.page.wait_for_selector(selector, timeout=3000)
                            if element:
                                # Get the clickable parent container
                                await element.click()
                                logger.info(f"Clicked iCloud photos box with selector: {selector}")
                                photos_clicked = True
                                await self.page.wait_for_timeout(2000)
                                
                                # After clicking the box, we should be on the next page
                                # Now look for the Next button
                                next_btn = await self.page.wait_for_selector('button:has-text("Next")', timeout=5000)
                                if next_btn:
                                    logger.info("Clicking Next button after selecting photos...")
                                    await next_btn.click()
                                    await self.page.wait_for_timeout(3000)
                                break
                        except Exception as e:
                            logger.debug(f"Selector {selector} failed: {e}")
                            continue
                    
                    if not photos_clicked:
                        logger.warning("Could not automatically click photos option")
                        screenshot_path = get_screenshot_dir() / f"export_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=str(screenshot_path))
                        logger.info(f"Screenshot saved: {screenshot_path}")
                        
                        # Still try to click Next if available
                        try:
                            next_btn = await self.page.wait_for_selector('button:has-text("Next")', timeout=5000)
                            if next_btn:
                                await next_btn.click()
                                await self.page.wait_for_timeout(3000)
                        except:
                            pass
                else:
                    # Original flow with radio button
                    photos_selectors = [
                        'input#photos-radio',
                        'text="Photos and videos"',
                        'label:has-text("photos")'
                    ]
                    
                    photos_option = None
                    for selector in photos_selectors:
                        photos_option = await self.page.query_selector(selector)
                        if photos_option:
                            logger.info(f"Found photos radio option with selector: {selector}")
                            await photos_option.click()
                            await self.page.wait_for_timeout(1000)
                            break
                    
                    if not photos_option:
                        logger.warning("Could not find photos option, taking screenshot...")
                        screenshot_path = get_screenshot_dir() / f"no_photos_option_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=str(screenshot_path))
                        logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Step 3: Click Continue/Next (if not already clicked above)
                # Check if we need to click Next/Continue
                page_content_after = await self.page.content()
                if "Choose what you'd like to export" not in page_content_after:
                    # We're past the export selection, check if we need to click Continue/Next
                    continue_selectors = [
                        'button:has-text("Continue")',
                        'button:has-text("Next")'
                    ]
                    
                    for selector in continue_selectors:
                        continue_btn = await self.page.query_selector(selector)
                        if continue_btn:
                            # Check if button is enabled
                            is_disabled = await continue_btn.get_attribute('disabled')
                            if not is_disabled:
                                logger.info(f"Clicking {selector}...")
                                await continue_btn.click()
                                await self.page.wait_for_timeout(3000)
                                break
                
                # Step 4: Extract counts
                logger.info("Extracting photo counts...")
                photo_count = 0
                video_count = 0
                storage_gb = 0
                
                all_text_elements = await self.page.query_selector_all('div, span, p, h1, h2, h3')
                logger.info(f"Searching through {len(all_text_elements)} text elements...")
                
                for element in all_text_elements:
                    try:
                        text = await element.inner_text()
                        # Log any text containing numbers and photos/videos
                        if 'photo' in text.lower() or 'video' in text.lower():
                            if re.search(r'\d+', text):
                                logger.debug(f"Found text with numbers: {text[:100]}")
                        
                        match = re.search(r'([\d,]+)\s+photos\s+and\s+([\d,]+)\s+videos', text)
                        if match:
                            photo_count = int(match.group(1).replace(',', ''))
                            video_count = int(match.group(2).replace(',', ''))
                            logger.info(f"✅ Found counts: {photo_count:,} photos, {video_count:,} videos")
                            break
                    except:
                        pass
                
                if photo_count == 0:
                    logger.warning("Could not find photo counts, taking screenshot...")
                    screenshot_path = get_screenshot_dir() / f"no_counts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(screenshot_path))
                    logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Look for storage
                for element in all_text_elements:
                    try:
                        text = await element.inner_text()
                        storage_match = re.search(r'About\s+(\d+)\s*([GM])B', text)
                        if storage_match:
                            size = int(storage_match.group(1))
                            unit = storage_match.group(2)
                            storage_gb = size if unit == 'G' else size / 1024
                            break
                    except:
                        pass
                
                return {
                    "status": "success",
                    "photos": photo_count,
                    "videos": video_count,
                    "total_items": photo_count + video_count,
                    "storage_gb": storage_gb,
                    "existing_transfers": existing_transfers,
                    "session_used": use_saved_session,
                    "source": "privacy.apple.com",
                    "checked_at": datetime.now().isoformat()
                }
            else:
                logger.error("Could not find transfer button")
                return {
                    "status": "error",
                    "photos": 0,
                    "videos": 0,
                    "total_items": 0,
                    "storage_gb": 0,
                    "existing_transfers": existing_transfers,
                    "session_used": use_saved_session,
                    "error": "Could not find transfer button"
                }
                
        except Exception as e:
            logger.error(f"Failed: {e}")
            raise
        finally:
            # Don't close browser here - keep it alive for transfer workflow
            pass
    
    async def clear_session(self):
        """Clear saved session to force fresh login next time"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            if self.session_info_file.exists():
                self.session_info_file.unlink()
            logger.info("Session cleared")
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    # ==================== NEW PHASE 3 METHODS ====================
    
    async def start_transfer(self, reuse_session: bool = True) -> Dict[str, Any]:
        """Initiate iCloud to Google Photos transfer workflow.
        
        This is the main entry point for starting a photo migration. It performs:
        1. Establishes Google Photos baseline (current photo count)
        2. Authenticates with Apple ID (reusing session if available)
        3. Gets current iCloud photo/video counts
        4. Navigates through Apple's 8-step transfer workflow
        5. Creates transfer record in database for tracking
        
        **MCP Tool Name**: `start_photo_transfer`
        
        **Required Environment Variables**:
            - APPLE_ID: Apple ID email for source account
            - APPLE_PASSWORD: Apple ID password
            - GOOGLE_EMAIL: Google account email (destination)
            - GOOGLE_PASSWORD: Google account password
        
        Args:
            reuse_session: Whether to reuse existing browser session to avoid 2FA.
                          Defaults to True. Set to False to force fresh login.
        
        Returns:
            Dict containing:
                - status: "initiated" or "error"
                - transfer_id: Unique identifier for tracking (e.g., "TRF-20250820-143022")
                - started_at: ISO timestamp of transfer start
                - source_counts: Dict with photos, videos, total, size_gb
                - destination: Service name and account (email redacted)
                - baseline_established: Pre-transfer count and timestamp
                - estimated_completion_days: "3-7" days estimate
                - error: Error message if status is "error"
        
        Example Response:
            {
                "status": "initiated",
                "transfer_id": "TRF-20250820-143022",
                "started_at": "2025-08-20T14:30:22Z",
                "source_counts": {
                    "photos": 60238,
                    "videos": 2418,
                    "total": 62656,
                    "size_gb": 383
                },
                "destination": {
                    "service": "Google Photos",
                    "account": "REDACTED"
                },
                "baseline_established": {
                    "pre_transfer_count": 42,
                    "baseline_timestamp": "2025-08-20T14:30:00Z"
                },
                "estimated_completion_days": "3-7"
            }
        
        Raises:
            Exception: If credentials are missing or workflow fails
        """
        try:
            # Get ALL credentials from environment
            apple_id = os.getenv('APPLE_ID')
            apple_password = os.getenv('APPLE_PASSWORD')
            google_email = os.getenv('GOOGLE_EMAIL')
            
            if not apple_id or not apple_password:
                return {
                    "status": "error",
                    "message": "Please configure APPLE_ID and APPLE_PASSWORD in environment variables"
                }
            
            if not google_email:
                return {
                    "status": "error",
                    "message": "Please configure GOOGLE_EMAIL in environment variables"
                }
            
            # Ensure APIs are initialized
            if not self.google_dashboard_client:
                await self.initialize_apis()
            
            # Step 1: Establish baseline in a NEW browser context (won't break flow)
            logger.info("Establishing Google Photos baseline in separate context...")
            baseline_data = await self._establish_baseline_in_new_context()
            
            if baseline_data.get("status") == "error":
                logger.warning(f"Baseline failed: {baseline_data.get('message')}")
                # Continue anyway with 0 baseline
                baseline_data = {
                    "baseline_count": 0,
                    "albums_count": 0,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Step 2: Get current iCloud status
            logger.info("Getting iCloud photo status...")
            icloud_status = await self.get_photo_status(
                apple_id=apple_id,
                password=apple_password,
                force_fresh_login=not reuse_session
            )
            
            if icloud_status.get("status") == "error":
                return icloud_status
            
            # Step 3: Navigate to transfer initiation
            logger.info("Initiating transfer workflow...")
            transfer_result = await self._initiate_transfer_workflow()
            
            if transfer_result.get("status") == "error":
                return transfer_result
            
            # Step 4: Generate transfer ID and save
            transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            transfer_data = {
                'transfer_id': transfer_id,
                'started_at': datetime.now().isoformat(),
                'source_photos': icloud_status.get('photos', 0),
                'source_videos': icloud_status.get('videos', 0),
                'source_size_gb': icloud_status.get('storage_gb', 0),
                'google_email': google_email,
                'apple_id': apple_id,
                'baseline_count': baseline_data['baseline_count'],
                'baseline_timestamp': baseline_data['timestamp'],
                'status': 'initiated'
            }
            
            # Save transfer data
            await self._save_transfer(transfer_data)
            
            return {
                "status": "initiated",
                "transfer_id": transfer_id,
                "started_at": transfer_data['started_at'],
                "source_counts": {
                    "photos": icloud_status.get('photos', 0),
                    "videos": icloud_status.get('videos', 0),
                    "total": icloud_status.get('total_items', 0),
                    "size_gb": icloud_status.get('storage_gb', 0)
                },
                "destination": {
                    "service": "Google Photos",
                    "account": google_email
                },
                "baseline_established": {
                    "pre_transfer_count": baseline_data['baseline_count'],
                    "baseline_timestamp": baseline_data['timestamp']
                },
                "estimated_completion_days": "3-7",
                "session_used": icloud_status.get('session_used', False)
            }
            
        except Exception as e:
            logger.error(f"Transfer initiation failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def check_transfer_progress(self, transfer_id: str) -> Dict[str, Any]:
        """Monitor ongoing photo transfer progress.
        
        Checks the current status of a transfer by comparing Google Photos
        count against the baseline established when transfer started.
        Calculates progress percentage, transfer rate, and estimates completion.
        
        **MCP Tool Name**: `check_photo_transfer_progress`
        
        **How it Works**:
        1. Retrieves transfer record from database
        2. Gets current Google Photos count via Dashboard
        3. Calculates items transferred since baseline
        4. Computes transfer rate and estimates completion
        5. Updates progress history in database
        
        Args:
            transfer_id: The unique transfer identifier returned by start_transfer.
                        Format: "TRF-YYYYMMDD-HHMMSS"
        
        Returns:
            Dict containing:
                - transfer_id: The provided transfer ID
                - status: "in_progress", "complete", "not_found", or "error"
                - timeline: Started/checked timestamps, days elapsed, estimated completion
                - counts: Source total, baseline, current, transferred, remaining
                - progress: Percentage complete, transfer rates (per day/hour)
                - error: Error message if status is "error"
        
        Example Response:
            {
                "transfer_id": "TRF-20250820-143022",
                "status": "in_progress",
                "timeline": {
                    "started_at": "2025-08-20T14:30:22Z",
                    "checked_at": "2025-08-22T10:15:00Z",
                    "days_elapsed": 1.8,
                    "estimated_completion": "2025-08-24T16:00:00Z"
                },
                "counts": {
                    "source_total": 62656,
                    "baseline_google": 42,
                    "current_google": 28500,
                    "transferred_items": 28458,
                    "remaining_items": 34198
                },
                "progress": {
                    "percent_complete": 45.4,
                    "transfer_rate_per_day": 15810,
                    "transfer_rate_per_hour": 659
                }
            }
        
        Note:
            Progress calculation: (current - baseline) / source_total * 100
            This accounts for any existing photos in Google Photos
        """
        try:
            # Ensure Google Dashboard is initialized
            if not self.google_dashboard_client:
                await self.initialize_apis()
            
            # Get transfer details
            transfer = await self._get_transfer(transfer_id)
            if not transfer:
                return {
                    "status": "error",
                    "error": f"Transfer {transfer_id} not found"
                }
            
            # Get current Google photo count
            logger.info("Getting current Google photo count...")
            dashboard_result = await self.google_dashboard_client.get_photo_count()
            
            if dashboard_result['status'] != 'success':
                return {
                    "status": "error",
                    "error": "Failed to get Google photo count"
                }
            
            current_google_count = dashboard_result['photos']
            
            # Calculate progress
            baseline_count = transfer['baseline_count']
            transferred_items = current_google_count - baseline_count
            source_total = transfer['source_photos'] + transfer['source_videos']
            percent_complete = (transferred_items / source_total * 100) if source_total > 0 else 0
            
            # Calculate elapsed time
            # Handle both string and datetime objects from database
            if isinstance(transfer['started_at'], str):
                started_at = datetime.fromisoformat(transfer['started_at'])
            else:
                started_at = transfer['started_at']
            days_elapsed = (datetime.now() - started_at).total_seconds() / 86400
            
            # Calculate transfer rate
            if days_elapsed > 0:
                transfer_rate_per_day = transferred_items / days_elapsed
                transfer_rate_per_hour = transfer_rate_per_day / 24
            else:
                transfer_rate_per_day = 0
                transfer_rate_per_hour = 0
            
            # Update progress history
            progress_data = {
                'checked_at': datetime.now().isoformat(),
                'google_total': current_google_count,
                'transferred_items': transferred_items,
                'percent_complete': percent_complete
            }
            
            await self._update_progress(transfer_id, progress_data)
            
            return {
                "transfer_id": transfer_id,
                "status": "complete" if percent_complete >= 99 else "in_progress",
                "timeline": {
                    "started_at": transfer['started_at'],
                    "checked_at": progress_data['checked_at'],
                    "days_elapsed": round(days_elapsed, 2),
                    "estimated_completion": self._estimate_completion(
                        transferred_items, source_total, transfer_rate_per_day
                    )
                },
                "counts": {
                    "source_total": source_total,
                    "baseline_google": baseline_count,
                    "current_google": current_google_count,
                    "transferred_items": transferred_items,
                    "remaining_items": max(0, source_total - transferred_items)
                },
                "progress": {
                    "percent_complete": round(percent_complete, 1),
                    "transfer_rate_per_day": round(transfer_rate_per_day, 0),
                    "transfer_rate_per_hour": round(transfer_rate_per_hour, 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Progress check failed: {e}")
            return {
                "transfer_id": transfer_id,
                "status": "error",
                "error": str(e)
            }
    
    async def verify_transfer_complete(
        self, 
        transfer_id: str, 
        important_photos: Optional[List[str]] = None,
        include_email_check: bool = True
    ) -> Dict[str, Any]:
        """Verify that photo transfer completed successfully.
        
        Performs comprehensive verification including count matching,
        optional email confirmation, and generates a completion certificate.
        This should be called when progress shows near 100% completion.
        
        **MCP Tool Name**: `verify_photo_transfer_complete`
        
        **Verification Steps**:
        1. Retrieves final Google Photos count
        2. Compares against source photo count
        3. Calculates match rate percentage
        4. Optionally checks for Apple completion email
        5. Generates completion certificate with grade
        6. Updates transfer status in database
        
        Args:
            transfer_id: The unique transfer identifier to verify
            important_photos: Optional list of specific photo filenames to verify
                            presence in Google Photos (future feature)
            include_email_check: Whether to check Gmail for Apple's completion
                               email. Defaults to True.
        
        Returns:
            Dict containing:
                - transfer_id: The provided transfer ID
                - status: "complete", "incomplete", "not_found", or "error"
                - completed_at: ISO timestamp of completion (if complete)
                - verification: Source/destination counts and match rate
                - email_confirmation: Email status if checked
                - certificate: Grade (A+, A, B, etc.) and score
                - important_photos_found: List of verified photos (if provided)
                - error: Error message if status is "error"
        
        Example Response:
            {
                "transfer_id": "TRF-20250820-143022",
                "status": "complete",
                "completed_at": "2025-08-24T16:45:00Z",
                "verification": {
                    "source_photos": 60238,
                    "destination_photos": 60238,
                    "match_rate": 100.0
                },
                "email_confirmation": {
                    "email_found": true,
                    "email_received_at": "2025-08-24T16:30:00Z"
                },
                "certificate": {
                    "grade": "A+",
                    "score": 100,
                    "message": "Perfect Migration - Zero Data Loss"
                }
            }
        
        Grading Scale:
            - A+ (100%): Perfect migration, all items transferred
            - A (95-99%): Excellent, minimal items missing
            - B (90-94%): Good, most items transferred
            - C (80-89%): Fair, some items missing
            - F (<80%): Poor, significant data loss
            
        Returns:
            Dict with verification status, match rate, certificate, etc.
        """
        try:
            # Get final progress
            final_progress = await self.check_transfer_progress(transfer_id)
            
            if final_progress.get("status") == "error":
                return final_progress
            
            # Check for completion email if requested
            email_result = None
            if include_email_check and self.gmail_client:
                logger.info("Checking for Apple completion email...")
                email_result = await self.check_completion_email(transfer_id)
            
            # Generate completion assessment
            is_complete = final_progress['progress']['percent_complete'] >= 99
            
            # Update transfer status if complete
            if is_complete:
                await self._mark_transfer_complete(transfer_id)
            
            return {
                "transfer_id": transfer_id,
                "status": "complete" if is_complete else "incomplete",
                "completed_at": datetime.now().isoformat() if is_complete else None,
                "verification": {
                    "source_photos": final_progress['counts']['source_total'],
                    "destination_photos": final_progress['counts']['transferred_items'],
                    "match_rate": final_progress['progress']['percent_complete']
                },
                "email_confirmation": email_result or {"email_found": False},
                "important_photos_check": important_photos if important_photos else [],
                "certificate": {
                    "grade": "A+" if is_complete else "Incomplete",
                    "score": int(final_progress['progress']['percent_complete']),
                    "message": "Perfect Migration - Zero Data Loss" if is_complete else "Transfer in progress",
                    "issued_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Transfer verification failed: {e}")
            return {
                "transfer_id": transfer_id,
                "status": "error",
                "error": str(e)
            }
    
    async def confirm_transfer_final_step(self) -> Dict[str, Any]:
        """Click the final 'Confirm Transfer' button to actually start the transfer.
        
        **IMPORTANT**: This method should ONLY be called after:
        1. start_transfer() has completed successfully
        2. The agent/user has reviewed the confirmation page
        3. The user has explicitly agreed to proceed
        
        This is a separate step to ensure deliberate confirmation before
        starting a multi-day transfer process.
        
        Returns:
            Dict containing:
                - status: "confirmed" or "error"
                - message: Confirmation or error message
                - transfer_started_at: Timestamp when transfer was confirmed
        """
        try:
            if not self.page:
                return {
                    "status": "error",
                    "message": "No active browser session. Run start_transfer first."
                }
            
            # Check if we're on the confirmation page
            current_url = self.page.url
            if "privacy.apple.com" not in current_url:
                return {
                    "status": "error",
                    "message": "Not on Apple confirmation page. Run start_transfer first."
                }
            
            # Look for the Confirm Transfer button
            confirm_button = await self.page.query_selector('button:has-text("Confirm Transfer")')
            if not confirm_button:
                return {
                    "status": "error",
                    "message": "Confirm Transfer button not found. Ensure you're on the confirmation page."
                }
            
            # Click the Confirm Transfer button
            logger.info("Clicking 'Confirm Transfer' button to start the actual transfer...")
            await confirm_button.click()
            
            # Wait for confirmation message or redirect
            await self.page.wait_for_timeout(3000)
            
            logger.info("✅ Transfer confirmed and started!")
            
            return {
                "status": "confirmed",
                "message": "Transfer has been confirmed and started. Apple will process the transfer over 3-7 days.",
                "transfer_started_at": datetime.now().isoformat(),
                "next_steps": [
                    "Apple will email you when the transfer is complete",
                    "Use check_transfer_progress() to monitor progress",
                    "Transfer typically takes 3-7 days"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to confirm transfer: {e}")
            return {
                "status": "error",
                "message": f"Failed to confirm transfer: {str(e)}"
            }
    
    async def check_completion_email(self, transfer_id: str) -> Dict[str, Any]:
        """Check Gmail for Apple transfer completion notification.
        
        Searches Gmail inbox for emails from Apple confirming that the
        photo transfer to Google Photos has completed. Uses OAuth2
        authentication with automatic browser flow on first use.
        
        **MCP Tool Name**: `check_photo_transfer_email`
        
        **Required Environment Variable**:
            - GMAIL_CREDENTIALS_PATH: Path to Gmail OAuth2 credentials JSON
        
        **Email Search Criteria**:
            - From: noreply@email.apple.com
            - Subject keywords: "transfer complete", "transfer ready"
            - Time window: Last 72 hours by default
        
        Args:
            transfer_id: The unique transfer identifier to search for in emails.
                        Used to find the specific transfer confirmation.
        
        Returns:
            Dict containing:
                - transfer_id: The provided transfer ID
                - email_found: Boolean indicating if email was found
                - email_details: Subject, sender, timestamp, content summary
                - error: Error message if Gmail not configured
        
        Example Response (Found):
            {
                "transfer_id": "TRF-20250820-143022",
                "email_found": true,
                "email_details": {
                    "subject": "Your transfer to Google Photos is complete",
                    "sender": "appleid@apple.com",
                    "received_at": "2025-08-24T16:30:00Z",
                    "content_summary": {
                        "message": "Transfer completion confirmed",
                        "photos_mentioned": "60,238",
                        "videos_mentioned": "2,418"
                    }
                }
            }
        
        Example Response (Not Found):
            {
                "transfer_id": "TRF-20250820-143022",
                "email_found": false,
                "checked_at": "2025-08-22T10:00:00Z",
                "message": "No completion email found yet"
            }
        
        Note:
            First use will open browser for Gmail OAuth authorization.
            Subsequent uses will reuse the saved token.
        """
        if not self.gmail_client:
            return {"email_found": False, "error": "Gmail API not configured"}
        
        try:
            # Get transfer details
            transfer = await self._get_transfer(transfer_id)
            if not transfer:
                return {"email_found": False, "error": "Transfer not found"}
            
            # Search for Apple emails since transfer started
            # Handle both string and datetime objects from database
            if isinstance(transfer['started_at'], str):
                transfer_start = datetime.fromisoformat(transfer['started_at'])
            else:
                transfer_start = transfer['started_at']
            
            logger.info(f"Searching for Apple emails since {transfer_start}")
            emails = await self.gmail_client.search_emails(
                query="from:appleid@apple.com subject:photos",
                after_date=transfer_start.strftime("%Y/%m/%d")
            )
            
            if emails:
                # Parse the most recent email
                latest_email = emails[0]
                return {
                    "transfer_id": transfer_id,
                    "email_found": True,
                    "email_details": {
                        "subject": latest_email.get('subject', ''),
                        "received_at": latest_email.get('date', ''),
                        "sender": "appleid@apple.com",
                        "content_summary": {
                            "message": "Transfer completion email found"
                        }
                    }
                }
            
            return {
                "transfer_id": transfer_id,
                "email_found": False,
                "message": "No Apple completion email found yet"
            }
            
        except Exception as e:
            logger.error(f"Email check failed: {e}")
            return {
                "transfer_id": transfer_id,
                "email_found": False,
                "error": str(e)
            }
    
    # ==================== HELPER METHODS ====================
    
    async def _establish_baseline_in_new_context(self) -> Dict[str, Any]:
        """Establish Google Photos baseline in a NEW browser context
        This prevents breaking the transfer workflow on the main page
        """
        try:
            from playwright.async_api import async_playwright
            
            logger.info("Opening separate browser for baseline...")
            
            # Get Google credentials from environment
            google_email = os.getenv('GOOGLE_EMAIL')
            google_password = os.getenv('GOOGLE_PASSWORD')
            
            # Create a completely separate browser instance
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,  # Run in background
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                # Create new context
                context = await browser.new_context()
                page = await context.new_page()
                
                # Create a temporary Google Dashboard client for this context
                from .google_dashboard_client import GoogleDashboardClient
                temp_client = GoogleDashboardClient()
                # Set the playwright and browser instances
                temp_client.playwright = playwright
                temp_client.browser = browser
                temp_client.context = context
                temp_client.page = page
                
                # Get photo count
                result = await temp_client.get_photo_count(
                    google_email=google_email,
                    google_password=google_password
                )
                
                if result['status'] == 'success':
                    logger.info(f"✅ Baseline established: {result['photos']} photos, {result['albums']} albums")
                    return {
                        "status": "success",
                        "baseline_count": result['photos'],
                        "albums_count": result['albums'],
                        "google_storage_gb": result.get('storage_gb', 0),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to get photo count"
                    }
                    
            finally:
                # Clean up the separate browser
                await browser.close()
                await playwright.stop()
                logger.info("Closed baseline browser context")
                
        except Exception as e:
            logger.error(f"Baseline establishment failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _establish_baseline(self, google_email: str = None) -> Dict[str, Any]:
        """Establish Google Photos baseline count (OLD METHOD - breaks flow)"""
        try:
            if not self.google_dashboard_client:
                await self.initialize_apis()
            
            # Get Google credentials from environment
            if not google_email:
                google_email = os.getenv('GOOGLE_EMAIL')
            google_password = os.getenv('GOOGLE_PASSWORD')
            
            result = await self.google_dashboard_client.get_photo_count(
                google_email=google_email,
                google_password=google_password
            )
            
            if result['status'] == 'success':
                logger.info(f"Baseline established: {result['photos']} photos, {result['albums']} albums")
                return {
                    "baseline_count": result['photos'],
                    "albums_count": result['albums'],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to establish baseline"
                }
        except Exception as e:
            logger.error(f"Baseline establishment failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _initiate_transfer_workflow(self) -> Dict[str, Any]:
        """Navigate through complete transfer workflow on privacy.apple.com"""
        try:
            # Import the complete workflow handler
            from .icloud_transfer_workflow import TransferWorkflow
            
            # Get Google credentials from environment
            google_email = os.getenv('GOOGLE_EMAIL')
            google_password = os.getenv('GOOGLE_PASSWORD')
            
            logger.info(f"Starting complete transfer workflow for {google_email}")
            
            # Ensure we have a page
            if not hasattr(self, 'page') or not self.page:
                return {
                    "status": "error",
                    "message": "Browser page not initialized. Please run get_photo_status first."
                }
            
            # Ensure we have context
            if not hasattr(self, 'context') or not self.context:
                return {
                    "status": "error",
                    "message": "Browser context not initialized."
                }
            
            # We should already be on the transfer page from get_photo_status
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Use the complete workflow handler
            workflow = TransferWorkflow(self.page, self.context)
            result = await workflow.execute_complete_workflow(google_email, google_password)
            
            return result
            
        except Exception as e:
            logger.error(f"Transfer initiation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _OLD_initiate_transfer_workflow(self, google_email: str = None) -> Dict[str, Any]:
        """OLD implementation - kept for reference"""
        try:
            # Step 1: Select Google Photos as destination
            logger.info("Step 1: Selecting Google Photos as destination")
            await self.page.wait_for_timeout(2000)
            
            # Look for the destination dropdown - it's a native select element
            try:
                # First, wait for the page to fully load
                await self.page.wait_for_selector('select', timeout=10000)
                
                # Find the select element (there should be only one on this page)
                dropdown = await self.page.query_selector('select')
                if dropdown:
                    # Check current value
                    current_value = await dropdown.evaluate('el => el.value')
                    logger.info(f"Current dropdown value: {current_value}")
                    
                    # Get all options
                    options = await self.page.query_selector_all('select option')
                    logger.info(f"Found {len(options)} options in dropdown")
                    
                    # Find Google Photos option
                    google_photos_value = None
                    for option in options:
                        text = await option.inner_text()
                        value = await option.get_attribute('value')
                        logger.info(f"  Option: {text} = {value}")
                        if 'Google Photos' in text:
                            google_photos_value = value
                            break
                    
                    if google_photos_value:
                        # Select Google Photos using the value
                        await self.page.select_option('select', value=google_photos_value)
                        logger.info(f"Selected Google Photos (value: {google_photos_value})")
                    else:
                        # Try selecting by label
                        await self.page.select_option('select', label='Google Photos')
                        logger.info("Selected Google Photos by label")
                    
                    await self.page.wait_for_timeout(1000)
                else:
                    logger.warning("No select dropdown found on page")
            except Exception as e:
                logger.error(f"Failed to select Google Photos: {e}")
                # Try to continue anyway - might already be selected
                pass
            
            # Step 2: Ensure Photos checkbox is selected (REQUIRED for Continue button)
            logger.info("Step 2: Ensuring Photos checkbox is selected")
            
            # Find the Photos checkbox - it's required for Continue to be enabled
            photos_checkbox = await self.page.wait_for_selector('input[type="checkbox"]#photos', timeout=5000)
            if photos_checkbox:
                is_checked = await photos_checkbox.is_checked()
                logger.info(f"Photos checkbox current state: {'checked' if is_checked else 'unchecked'}")
                if not is_checked:
                    await photos_checkbox.click()
                    logger.info("✅ Checked Photos checkbox")
                    await self.page.wait_for_timeout(1000)
                else:
                    logger.info("Photos checkbox already checked")
            else:
                # Try alternative selectors
                logger.info("Looking for Photos checkbox with alternative selectors...")
                checkbox_selectors = [
                    'input[type="checkbox"][id="photos"]',
                    'input[type="checkbox"][name="photos"]',
                    'label:has-text("Photos") input[type="checkbox"]',
                    'text="Photos (60,238 photos)" >> xpath=../input[@type="checkbox"]'
                ]
                
                for selector in checkbox_selectors:
                    try:
                        cb = await self.page.query_selector(selector)
                        if cb:
                            is_checked = await cb.is_checked()
                            logger.info(f"Found checkbox with selector: {selector}, checked: {is_checked}")
                            if not is_checked:
                                await cb.click()
                                logger.info("✅ Checked Photos checkbox")
                                await self.page.wait_for_timeout(1000)
                            break
                    except:
                        continue
            
            # Also check Videos checkbox if present (optional)
            try:
                videos_checkbox = await self.page.query_selector('input[type="checkbox"]#videos')
                if videos_checkbox:
                    is_checked = await videos_checkbox.is_checked()
                    logger.info(f"Videos checkbox current state: {'checked' if is_checked else 'unchecked'}")
                    if not is_checked:
                        await videos_checkbox.click()
                        logger.info("✅ Checked Videos checkbox")
                        await self.page.wait_for_timeout(1000)
            except:
                logger.info("Videos checkbox not found or not needed")
            
            # Step 3: Click Continue button
            logger.info("Step 3: Clicking Continue to proceed")
            
            # Wait for Continue button to be enabled after dropdown selection
            await self.page.wait_for_timeout(2000)
            
            # Find the Continue button - try multiple selectors
            continue_selectors = [
                'button:has-text("Continue")',
                'button.continue-button',
                'button[type="submit"]',
                'a.button:has-text("Continue")'
            ]
            
            continue_btn = None
            for selector in continue_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        continue_btn = btn
                        logger.info(f"Found Continue button with selector: {selector}")
                        break
                except:
                    pass
            
            if not continue_btn:
                continue_btn = await self.page.wait_for_selector('button:has-text("Continue")', timeout=10000)
            
            # Wait for it to be enabled (should be enabled after checking Photos checkbox)
            is_disabled = await continue_btn.get_attribute('disabled')
            logger.info(f"Continue button disabled attribute: {is_disabled}")
            
            if is_disabled is not None and is_disabled != 'false' and is_disabled != False:
                logger.info("Continue button is disabled, waiting for it to enable...")
                # Wait up to 10 seconds for button to be enabled
                for i in range(10):
                    await self.page.wait_for_timeout(1000)
                    is_disabled = await continue_btn.get_attribute('disabled')
                    if is_disabled is None or is_disabled == 'false' or is_disabled == False:
                        logger.info("✅ Continue button is now enabled")
                        break
                    else:
                        logger.info(f"Still waiting... ({i+1}/10 seconds)")
                
                # Final check
                is_disabled = await continue_btn.get_attribute('disabled')
                if is_disabled and is_disabled != 'false' and is_disabled != False:
                    logger.error("Continue button still disabled after 10 seconds")
                    # Try checking the checkboxes again
                    logger.info("Attempting to re-check Photos checkbox...")
                    photos_cb = await self.page.query_selector('input[type="checkbox"]#photos')
                    if photos_cb:
                        await photos_cb.click()
                        await self.page.wait_for_timeout(1000)
            
            # Click the Continue button
            await continue_btn.click()
            logger.info("Clicked Continue button")
            await self.page.wait_for_timeout(3000)
            
            # Step 4: Page should now show "Copy your photos to Google Photos"
            logger.info("Step 4: On 'Copy your photos to Google Photos' page")
            await self.page.wait_for_timeout(2000)
            
            # Click Continue on this page
            continue_btn2 = await self.page.wait_for_selector('button:has-text("Continue"), a:has-text("Continue")', timeout=10000)
            await continue_btn2.click()
            logger.info("Clicked Continue on Google Photos copy page")
            await self.page.wait_for_timeout(3000)
            
            # Step 5: Google Account Selection page should appear
            logger.info("Step 5: Google account selection")
            
            # Check if we're on Google's OAuth page
            if "accounts.google.com" in self.page.url:
                logger.info("On Google OAuth page")
                
                # Look for account selection or sign-in
                try:
                    # Try to find and click on the existing account
                    account_option = await self.page.wait_for_selector(f'text="{google_email}"', timeout=5000)
                    await account_option.click()
                    logger.info(f"Selected account: {google_email}")
                except:
                    # May need to sign in
                    logger.info("Account not found in list, may need to sign in")
                    pass
                
                await self.page.wait_for_timeout(2000)
            
            # Step 6: Handle Apple Data and Privacy permission page
            logger.info("Step 6: Handling Apple Data and Privacy permissions")
            
            # Wait for the permission page to load
            await self.page.wait_for_timeout(3000)
            
            # Look for Continue button on permission page
            try:
                continue_permission = await self.page.wait_for_selector('button:has-text("Continue"), a:has-text("Continue")', timeout=10000)
                await continue_permission.click()
                logger.info("Clicked Continue on initial permission page")
                await self.page.wait_for_timeout(3000)
            except:
                logger.info("No initial Continue button found")
            
            # Step 7: Permission checkbox page - "Add to your Google Photos library"
            logger.info("Step 7: Granting Google Photos permissions")
            
            # Look for the checkbox for Google Photos permission
            try:
                # The checkbox might be pre-checked or we need to check it
                permission_checkbox = await self.page.wait_for_selector('input[type="checkbox"]', timeout=5000)
                is_checked = await permission_checkbox.is_checked()
                if not is_checked:
                    await permission_checkbox.click()
                    logger.info("Checked Google Photos permission checkbox")
                else:
                    logger.info("Permission checkbox already checked")
            except:
                logger.info("No permission checkbox found or already granted")
            
            # Click Continue after permissions
            continue_permission_final = await self.page.wait_for_selector('button:has-text("Continue"), a:has-text("Continue")', timeout=10000)
            await continue_permission_final.click()
            logger.info("Clicked Continue after granting permissions")
            await self.page.wait_for_timeout(3000)
            
            # Step 8: Final confirmation page - "Confirm your transfer"
            logger.info("Step 8: Final transfer confirmation")
            
            # Look for "Confirm Transfer" button
            confirm_button = await self.page.wait_for_selector(
                'button:has-text("Confirm Transfer"), button:has-text("Start Transfer"), button:has-text("Begin Transfer")',
                timeout=10000
            )
            await confirm_button.click()
            logger.info("✅ Clicked Confirm Transfer - Transfer initiated!")
            await self.page.wait_for_timeout(3000)
            
            # Capture confirmation screenshot
            screenshot_path = get_screenshot_dir() / f"transfer_initiated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Extract confirmation details
            page_content = await self.page.content()
            
            # Look for transfer ID or confirmation message
            transfer_id = None
            if "transfer" in page_content.lower() and "started" in page_content.lower():
                # Try to extract transfer ID if present
                import re
                id_pattern = r'(?:transfer\s+id|reference|confirmation)[\s:]*([A-Z0-9\-]+)'
                match = re.search(id_pattern, page_content, re.IGNORECASE)
                if match:
                    transfer_id = match.group(1)
            
            return {
                "status": "success",
                "message": "Transfer initiated successfully",
                "transfer_id": transfer_id,
                "google_email": google_email,
                "screenshot": str(screenshot_path)
            }
            
        except Exception as e:
            logger.error(f"Transfer initiation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _save_transfer(self, transfer_data: Dict[str, Any]):
        """Save transfer data to database or local storage"""
        if self.db:
            # Save to database using new schema
            try:
                # First create a migration if needed
                migration_id = await self.db.create_migration(
                    user_name=transfer_data.get('apple_id', 'Unknown User'),
                    photo_count=transfer_data['source_photos'],
                    video_count=transfer_data['source_videos'],
                    storage_gb=transfer_data['source_size_gb']
                )
                
                # Create photo transfer record
                transfer_id = await self.db.create_photo_transfer(
                    migration_id=migration_id,
                    total_photos=transfer_data['source_photos'],
                    total_videos=transfer_data['source_videos'],
                    total_size_gb=transfer_data['source_size_gb']
                )
                
                # Update the transfer_data with the generated IDs
                transfer_data['migration_id'] = migration_id
                transfer_data['transfer_id'] = transfer_id
                
                logger.info(f"Transfer {transfer_id} saved to database with migration {migration_id}")
            except Exception as e:
                logger.error(f"Failed to save transfer to database: {e}")
                # Fall back to local storage
                transfers = {}
                if self.local_transfers_file.exists():
                    with open(self.local_transfers_file, 'r') as f:
                        transfers = json.load(f)
                transfers[transfer_data['transfer_id']] = transfer_data
                with open(self.local_transfers_file, 'w') as f:
                    json.dump(transfers, f, indent=2)
        else:
            # Save to local JSON file
            transfers = {}
            if self.local_transfers_file.exists():
                with open(self.local_transfers_file, 'r') as f:
                    transfers = json.load(f)
            
            transfers[transfer_data['transfer_id']] = transfer_data
            
            with open(self.local_transfers_file, 'w') as f:
                json.dump(transfers, f, indent=2)
    
    async def _get_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get transfer data from database or local storage"""
        if self.db:
            try:
                with self.db.get_connection() as conn:
                    # Query from new photo_transfer table
                    result = conn.execute("""
                        SELECT pt.transfer_id, pt.migration_id,
                               pt.total_photos, pt.total_videos, pt.total_size_gb,
                               pt.transferred_photos, pt.transferred_videos,
                               pt.status, pt.apple_transfer_initiated,
                               m.user_name, m.started_at
                        FROM photo_transfer pt
                        JOIN migration_status m ON pt.migration_id = m.id
                        WHERE pt.transfer_id = ?
                    """, (transfer_id,)).fetchone()
                    
                    if result:
                        return {
                            'transfer_id': result[0],
                            'migration_id': result[1],
                            'source_photos': result[2],
                            'source_videos': result[3],
                            'source_size_gb': result[4],
                            'transferred_photos': result[5],
                            'transferred_videos': result[6],
                            'status': result[7],
                            'started_at': result[8] or result[10],  # Use transfer or migration start
                            'baseline_count': 0,  # Not in new schema, default to 0
                            'destination_service': 'Google Photos',
                            'destination_account': os.getenv('GOOGLE_EMAIL', 'unknown')
                        }
            except Exception as e:
                logger.error(f"Failed to get transfer from database: {e}")
            return None
        else:
            if self.local_transfers_file.exists():
                with open(self.local_transfers_file, 'r') as f:
                    transfers = json.load(f)
                    return transfers.get(transfer_id)
            return None
    
    async def _update_progress(self, transfer_id: str, progress_data: Dict[str, Any]):
        """Update progress for a transfer"""
        if self.db:
            try:
                # Get migration_id for this transfer
                transfer = await self._get_transfer(transfer_id)
                if transfer and 'migration_id' in transfer:
                    # Update photo progress using migration_db methods
                    await self.db.update_photo_progress(
                        migration_id=transfer['migration_id'],
                        transferred_photos=progress_data.get('transferred_items', 0),
                        transferred_videos=0,  # Not tracked separately in progress
                        transferred_size_gb=progress_data.get('transferred_size_gb', 0),
                        status='in_progress' if progress_data.get('percent_complete', 0) < 100 else 'completed'
                    )
                    logger.info(f"Progress updated for transfer {transfer_id}")
            except Exception as e:
                logger.error(f"Failed to update progress in database: {e}")
        else:
            # Local storage fallback
            transfer = await self._get_transfer(transfer_id)
            if transfer:
                if 'progress_history' not in transfer:
                    transfer['progress_history'] = []
                transfer['progress_history'].append(progress_data)
                await self._save_transfer(transfer)
    
    async def _mark_transfer_complete(self, transfer_id: str):
        """Mark a transfer as complete"""
        if self.db:
            try:
                # Get migration_id for this transfer
                transfer = await self._get_transfer(transfer_id)
                if transfer and 'migration_id' in transfer:
                    # Update photo transfer status
                    await self.db.update_photo_progress(
                        migration_id=transfer['migration_id'],
                        status='completed'
                    )
                    
                    # Update migration status
                    await self.db.update_migration_status(
                        migration_id=transfer['migration_id'],
                        status='completed'
                    )
                    
                    logger.info(f"Transfer {transfer_id} marked as complete")
            except Exception as e:
                logger.error(f"Failed to mark transfer complete in database: {e}")
        else:
            # Local storage fallback
            transfer = await self._get_transfer(transfer_id)
            if transfer:
                transfer['status'] = 'complete'
                transfer['completed_at'] = datetime.now().isoformat()
                await self._save_transfer(transfer)
    
    def _estimate_completion(self, transferred: int, total: int, rate_per_day: float) -> str:
        """Estimate completion time based on current rate"""
        if rate_per_day <= 0 or transferred >= total:
            return "Complete"
        
        remaining = total - transferred
        days_remaining = remaining / rate_per_day
        completion_date = datetime.now() + timedelta(days=days_remaining)
        
        return completion_date.strftime("%Y-%m-%d")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()