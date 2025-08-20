#!/usr/bin/env python3
"""
Google Dashboard Client with Session Persistence
Gets photo counts from myaccount.google.com/dashboard using Playwright
Saves session to avoid repeated logins
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Try to import playwright-stealth for better success rate
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

logger = logging.getLogger(__name__)

class GoogleDashboardClient:
    """Google Dashboard client that saves session to avoid repeated logins"""
    
    def __init__(self, session_dir: Optional[str] = None):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Session storage directory
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            # Default to user's home directory
            self.session_dir = Path.home() / ".google_session"
        
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "browser_state.json"
        self.session_info_file = self.session_dir / "session_info.json"
        
        logger.info(f"Google session directory: {self.session_dir}")
    
    async def initialize(self):
        """Initialize Playwright"""
        self.playwright = await async_playwright().start()
    
    def is_session_valid(self) -> bool:
        """Check if saved session exists and is recent (7 days like iCloud)"""
        if not self.session_file.exists() or not self.session_info_file.exists():
            return False
        
        try:
            with open(self.session_info_file, 'r') as f:
                info = json.load(f)
            
            # Check if session is less than 7 days old
            saved_time = datetime.fromisoformat(info.get('saved_at', ''))
            age = datetime.now() - saved_time
            
            if age < timedelta(days=7):
                logger.info(f"Found valid Google session from {saved_time.strftime('%Y-%m-%d %H:%M')}")
                return True
            else:
                logger.info(f"Google session too old ({age.days} days)")
                return False
                
        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False
    
    async def save_session(self):
        """Save browser session for reuse"""
        try:
            # Save browser state
            state = await self.context.storage_state()
            with open(self.session_file, 'w') as f:
                json.dump(state, f)
            
            # Save session metadata
            info = {
                'saved_at': datetime.now().isoformat(),
                'user_agent': self.context._impl_obj._options.get('user_agent')
            }
            with open(self.session_info_file, 'w') as f:
                json.dump(info, f)
            
            logger.info("Google session saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def clear_session(self):
        """Clear saved session"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            if self.session_info_file.exists():
                self.session_info_file.unlink()
            logger.info("Google session cleared")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
    
    async def get_photo_count(self, 
                            google_email: str = None,
                            google_password: str = None,
                            force_fresh_login: bool = False) -> Dict[str, Any]:
        """
        Get photo and album counts from Google Dashboard
        
        Args:
            google_email: Google account email (from env if not provided)
            google_password: Google account password (from env if not provided) 
            force_fresh_login: Force fresh login even if session exists
            
        Returns:
            Dictionary with photo/album counts and metadata
        """
        import os
        
        # Get credentials from environment if not provided
        if not google_email:
            google_email = os.getenv('GOOGLE_EMAIL')
        if not google_password:
            google_password = os.getenv('GOOGLE_PASSWORD')
        
        if not google_email or not google_password:
            return {
                "status": "error",
                "message": "Google credentials not provided. Set GOOGLE_EMAIL and GOOGLE_PASSWORD in .env"
            }
        
        try:
            # Check if we should use saved session
            use_saved_session = not force_fresh_login and self.is_session_valid()
            
            # Launch browser with stealth settings
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Show browser for transparency
                slow_mo=100,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Create or restore context
            if use_saved_session:
                logger.info("Using saved Google session")
                # Restore session from saved state
                with open(self.session_file, 'r') as f:
                    state = json.load(f)
                self.context = await self.browser.new_context(
                    storage_state=state,
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                session_used = True
            else:
                logger.info("Creating new Google browser session")
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                session_used = False
            
            self.page = await self.context.new_page()
            
            # Apply stealth if available
            if STEALTH_AVAILABLE:
                await stealth_async(self.page)
                logger.info("Stealth mode applied")
            
            # Start at signin page directly to ensure proper login flow
            logger.info("Navigating to Google Sign-in...")
            signin_url = "https://accounts.google.com/v3/signin/identifier?continue=https://myaccount.google.com/dashboard&hl=en-US&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
            await self.page.goto(signin_url)
            
            # Wait a bit for page to load
            await self.page.wait_for_timeout(2000)
            
            # Check if we need to login
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # We should always be on the signin page with fresh login
            if 'accounts.google.com' in current_url or 'identifier' in current_url:
                logger.info("Login page detected, performing login...")
                
                if use_saved_session:
                    logger.warning("Saved session expired, need fresh login")
                    session_used = False
                
                # Perform login
                await self._perform_login(google_email, google_password)
                
                # After login, wait for navigation
                await self.page.wait_for_load_state('networkidle')
                
                # Check where we are after login
                current_url = self.page.url
                logger.info(f"URL after login: {current_url}")
                
                # Navigate to the actual dashboard page (not intro)
                if 'dashboard' not in current_url or 'intro' in current_url:
                    logger.info("Navigating to actual dashboard...")
                    await self.page.goto('https://myaccount.google.com/dashboard')
                    await self.page.wait_for_load_state('networkidle')
                    await self.page.wait_for_timeout(2000)
            elif 'myaccount.google.com/dashboard' in current_url and 'intro' not in current_url:
                # Already on dashboard with saved session
                logger.info("Already on dashboard")
            else:
                # We're on some other page, navigate to dashboard
                logger.info("Navigating to dashboard...")
                await self.page.goto('https://myaccount.google.com/dashboard')
                await self.page.wait_for_load_state('networkidle')
            
            # Final check and wait
            await self.page.wait_for_timeout(2000)
            final_url = self.page.url
            logger.info(f"Final URL: {final_url}")
            
            # Extract photo counts
            logger.info("Extracting photo counts...")
            result = await self._extract_photo_counts()
            
            # Add metadata
            result.update({
                'session_used': session_used,
                'checked_at': datetime.now().isoformat(),
                'google_account': google_email
            })
            
            # Save session if this was a fresh login
            if not session_used and result.get('status') == 'success':
                await self.save_session()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get photo count: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    async def _perform_login(self, email: str, password: str):
        """Perform Google login"""
        logger.info(f"Performing Google login for {email}...")
        
        try:
            # First wait for page to load fully
            await self.page.wait_for_load_state('domcontentloaded')
            await self.page.wait_for_timeout(1000)
            
            # Take screenshot of initial page
            await self.page.screenshot(path="screenshots/login_1_initial.png")
            logger.info("Initial login page screenshot saved")
            
            # Look for email input - Google uses identifierId specifically
            logger.info("Looking for email input field...")
            
            # Try multiple strategies to find email field
            email_input = None
            selectors_to_try = [
                'input#identifierId',
                'input[type="email"]',
                'input[name="identifier"]',
                'input[autocomplete="username"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    email_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if email_input:
                        logger.info(f"Found email field with selector: {selector}")
                        break
                except:
                    continue
            
            if not email_input:
                raise Exception("Could not find email input field")
            
            # Clear and type email slowly
            await email_input.click()
            await self.page.wait_for_timeout(500)
            await email_input.fill('')
            await self.page.wait_for_timeout(500)
            
            # Type email character by character for more natural input
            for char in email:
                await email_input.type(char, delay=50)
            
            logger.info(f"Entered email: {email}")
            await self.page.screenshot(path="screenshots/login_2_email_entered.png")
            
            # Find Next button - try multiple selectors
            next_button = None
            next_selectors = [
                '#identifierNext',
                'button:has-text("Next")',
                'div[id="identifierNext"]',
                'button[jsname="LgbsSe"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if next_button:
                        logger.info(f"Found Next button with selector: {selector}")
                        break
                except:
                    continue
            
            if not next_button:
                raise Exception("Could not find Next button")
            
            # Click Next button
            await next_button.click()
            logger.info("Clicked Next after email")
            
            # Wait for page transition
            await self.page.wait_for_timeout(2000)
            await self.page.screenshot(path="screenshots/login_3_after_email_next.png")
            
            # Wait for navigation after email submission
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Check current URL to see where we are
            current_url = self.page.url
            logger.info(f"URL after email next: {current_url}")
            
            # Look for password field (standard flow)
            logger.info("Looking for password field...")
            password_input = None
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]', 
                'input[name="Passwd"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=3000, state='visible')
                    if password_input:
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                # Check if we're already logged in or on a different page
                current_url = self.page.url
                if 'myaccount.google.com' in current_url:
                    logger.info("Already logged in, skipping password entry")
                    return
                else:
                    logger.warning(f"Could not find password field, current URL: {current_url}")
            
            # Only enter password if we found the password field
            if password_input:
                # Enter password
                await password_input.click()
                await self.page.wait_for_timeout(500)
                await password_input.fill('')
                await self.page.wait_for_timeout(500)
                
                # Type password character by character
                for char in password:
                    await password_input.type(char, delay=50)
                
                logger.info("Entered password")
                await self.page.screenshot(path="screenshots/login_4_password_entered.png")
                
                # Find password Next button
                password_next = None
                password_next_selectors = [
                    '#passwordNext',
                    'button:has-text("Next")',
                    'div[id="passwordNext"]',
                    'button[jsname="LgbsSe"]'
                ]
                
                for selector in password_next_selectors:
                    try:
                        password_next = await self.page.wait_for_selector(selector, timeout=2000)
                        if password_next:
                            logger.info(f"Found password Next button with selector: {selector}")
                            break
                    except:
                        continue
                
                if password_next:
                    await password_next.click()
                    logger.info("Clicked Next after password")
                
                # Wait for navigation
                await self.page.wait_for_timeout(3000)
            
            # Check current URL after login attempt (or after email if no password)
            current_url = self.page.url
            logger.info(f"URL after login attempt: {current_url}")
            await self.page.screenshot(path="screenshots/login_5_after_password.png")
            
            # Check for 2-Step Verification page
            if 'challenge' in current_url or 'signin/v2/challenge' in current_url or 'signin/challenge' in current_url or '2-step verification' in await self.page.title().lower():
                logger.info("2-Step Verification page detected")
                await self._handle_2step_verification()
                
                # After 2FA, wait for the page to load
                await self.page.wait_for_load_state('networkidle')
                await self.page.screenshot(path="screenshots/login_6_after_2fa.png")
            
            # Final check - wait for redirect to complete
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            final_url = self.page.url
            logger.info(f"Final URL after login: {final_url}")
            
            if 'myaccount.google.com' in final_url:
                logger.info("Login completed successfully - on Google account page")
            else:
                logger.warning(f"Login may not be complete - unexpected URL: {final_url}")
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Take error screenshot
            await self.page.screenshot(path="screenshots/login_error.png")
            logger.error("Error screenshot saved as screenshots/login_error.png")
            
            # Log current page URL and title for debugging
            try:
                current_url = self.page.url
                current_title = await self.page.title()
                logger.error(f"Current page URL: {current_url}")
                logger.error(f"Current page title: {current_title}")
            except:
                pass
            
            raise
    
    async def _handle_2step_verification(self):
        """Handle 2-Step Verification page"""
        logger.info("Handling 2-Step Verification...")
        
        # Take screenshot
        await self.page.screenshot(path="screenshots/2step_verification.png")
        
        # Wait a moment for the page to fully load
        await self.page.wait_for_timeout(2000)
        
        # Check page content to understand what 2FA method is being shown
        page_content = await self.page.content()
        page_text = await self.page.text_content('body')
        
        # Check if it's already showing the phone prompt (Samsung Galaxy Z Fold7)
        if 'check your' in page_text.lower() and ('galaxy' in page_text.lower() or 'phone' in page_text.lower() or 'tap yes' in page_text.lower()):
            logger.info("Phone verification prompt detected (Tap Yes on device)")
            
            print("\n" + "="*60)
            print("📱 CHECK YOUR PHONE/TABLET")
            print("="*60)
            print("\nGoogle sent a notification to your device")
            print("1. Look for 'Trying to sign in?' notification")
            print("2. Tap 'Yes' on the notification to verify it's you")
            print("\nWaiting for you to tap Yes on your device...")
            
            # Wait for the user to tap Yes (Google will auto-redirect)
            for i in range(60):  # Wait up to 2 minutes
                await self.page.wait_for_timeout(2000)
                current_url = self.page.url
                
                # Check if we've been redirected to dashboard
                if 'myaccount.google.com' in current_url and 'challenge' not in current_url and 'signin' not in current_url:
                    logger.info(f"Successfully authenticated! Redirected to: {current_url}")
                    print("\n✅ Authentication successful!")
                    return True
                    
                if i % 5 == 0 and i > 0:  # Every 10 seconds
                    print(f"Still waiting... ({i*2} seconds)")
            
            logger.warning("Timeout waiting for phone verification")
            print("\n⚠️ Timeout waiting for phone verification")
            print("If you haven't received the notification, click 'Try another way' in the browser")
            print("Press Enter to continue...")
            input()
            
        # Check for "Try another way" link if default method isn't working
        elif 'try another way' in page_text.lower():
            logger.info("'Try another way' link found, may need to select different 2FA method")
            print("\n⚠️ Please manually select your preferred 2FA method")
            print("Click 'Try another way' if you want to use a different verification method")
            print("Press Enter after completing 2FA...")
            input()
        else:
            # Generic 2FA handler
            logger.info("Generic 2FA page detected")
            print("\n" + "="*60)
            print("2-STEP VERIFICATION REQUIRED")
            print("="*60)
            print("\nPlease complete the 2-step verification in the browser")
            print("This might be:")
            print("- Tap Yes on your phone")
            print("- Enter a code from your authenticator app")
            print("- Enter a backup code")
            print("\nPress Enter after completing 2FA...")
            input()
    
    async def _extract_photo_counts(self) -> Dict[str, Any]:
        """Extract photo and album counts from dashboard"""
        try:
            # Wait for Photos section to appear
            await self.page.wait_for_selector('text=/Photos/i', timeout=10000)
            
            # Initialize counts
            photos = 0
            albums = 0
            
            # Look for photo count using regex
            photo_elements = await self.page.query_selector_all('text=/\d+\s*photos?/i')
            for element in photo_elements:
                text = await element.text_content()
                match = re.search(r'(\d+)\s*photos?', text, re.IGNORECASE)
                if match:
                    photos = int(match.group(1))
                    logger.info(f"Found {photos} photos")
                    break
            
            # Look for album count
            album_elements = await self.page.query_selector_all('text=/\d+\s*albums?/i')
            for element in album_elements:
                text = await element.text_content()
                match = re.search(r'(\d+)\s*albums?', text, re.IGNORECASE)
                if match:
                    albums = int(match.group(1))
                    logger.info(f"Found {albums} albums")
                    break
            
            # Take screenshot for verification
            screenshot_dir = Path('screenshots')
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / f"google_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            
            return {
                'status': 'success',
                'photos': photos,
                'albums': albums,
                'total_items': photos,  # For compatibility with requirements
                'screenshot': str(screenshot_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to extract counts: {e}")
            return {
                'status': 'error',
                'message': f'Could not extract photo counts: {e}',
                'photos': 0,
                'albums': 0
            }
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Convenience function for testing
async def test_dashboard_client():
    """Test the Google Dashboard client"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    print("\n=== Testing Google Dashboard Client ===")
    print("With session persistence (like iCloud)\n")
    
    client = GoogleDashboardClient()
    await client.initialize()
    
    try:
        # Test getting photo count
        result = await client.get_photo_count()
        
        if result['status'] == 'success':
            print(f"\n✅ Successfully retrieved counts:")
            print(f"   📸 Photos: {result['photos']:,}")
            print(f"   📚 Albums: {result['albums']:,}")
            print(f"   📅 Checked at: {result['checked_at']}")
            
            if result.get('session_used'):
                print(f"\n✅ Used saved session - no login needed!")
            else:
                print(f"\n✅ New session created and saved for next time")
        else:
            print(f"\n❌ Failed: {result.get('message')}")
        
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_dashboard_client())