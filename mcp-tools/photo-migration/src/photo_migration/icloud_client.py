#!/usr/bin/env python3.11
"""
iCloud Client with Session Persistence
Saves authentication state to avoid 2FA on every run
"""

import asyncio
import logging
import re
import os
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, Frame

logger = logging.getLogger(__name__)

class ICloudClientWithSession:
    """iCloud client that saves session to avoid repeated 2FA"""
    
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
        
        logger.info(f"Session directory: {self.session_dir}")
    
    async def initialize(self):
        """Initialize Playwright"""
        self.playwright = await async_playwright().start()
    
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
        """
        Get photo counts from privacy.apple.com
        
        Args:
            apple_id: Apple ID (required for first login)
            password: Password (required for first login)
            force_fresh_login: Force a fresh login even if session exists
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
                context = await self.browser.new_context(
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
                
                context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
            
            self.page = await context.new_page()
            
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
                
                photos_selectors = [
                    'input#photos-radio',
                    'text="iCloud photos and videos"',
                    'text="Photos and videos"',
                    'label:has-text("photos")'
                ]
                
                photos_option = None
                for selector in photos_selectors:
                    photos_option = await self.page.query_selector(selector)
                    if photos_option:
                        logger.info(f"Found photos option with selector: {selector}")
                        await photos_option.click()
                        await self.page.wait_for_timeout(1000)
                        break
                
                if not photos_option:
                    logger.warning("Could not find photos option, taking screenshot...")
                    screenshot_path = f"/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/logs/no_photos_option_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Step 3: Click Continue/Next
                continue_selectors = [
                    'button:has-text("Continue")',
                    'button:has-text("Next")'
                ]
                
                for selector in continue_selectors:
                    continue_btn = await self.page.query_selector(selector)
                    if continue_btn:
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
                    screenshot_path = f"/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/logs/no_counts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=screenshot_path)
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
            if self.browser:
                await self.browser.close()
    
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
    
    async def cleanup(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()