#!/usr/bin/env python3
"""
Google One Storage Client with Session Persistence
Gets storage metrics from one.google.com/storage using Playwright
Saves session to avoid repeated logins
"""

import asyncio
import logging
import json
import re
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from .logging_config import setup_logging, get_screenshot_dir

# Try to import playwright-stealth for better success rate
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

logger = setup_logging(__name__)

class GoogleStorageClient:
    """Google One Storage client for monitoring storage during migration.
    
    This client provides access to Google One storage statistics via 
    one.google.com/storage using browser automation. It's used to track
    the actual storage growth in Google Photos during the transfer process.
    
    **Why Storage Instead of Photo Count**:
        - Storage growth provides more accurate progress tracking
        - Can differentiate between photos and videos based on storage
        - Works around Google Photos API limitations
        - Provides real-time transfer progress based on actual data
    
    **Key Features**:
        - Session persistence (7-day validity) to avoid repeated logins
        - Handles 2-Step Verification ("Tap Yes" on phone)
        - Extracts storage breakdown by service (Photos, Drive, Gmail)
        - Calculates transfer progress based on storage growth
        - Screenshots for verification and debugging
    
    **Used By**:
        - ICloudClient.start_transfer() - Establishes baseline storage
        - ICloudClient.check_transfer_progress() - Gets current storage
        - Storage snapshot recording for progress calculation
    
    Attributes:
        session_dir (Path): Directory for storing browser session state
        playwright: Playwright instance for browser automation
        browser: Chrome browser instance
        context: Browser context with saved session
        page: Current page being automated
    """
    
    def __init__(self, session_dir: Optional[str] = None):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Share the same session directory as GoogleDashboardClient
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            # Use the same directory as dashboard client for session reuse
            self.session_dir = Path.home() / ".google_session"
        
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "browser_state.json"
        self.session_info_file = self.session_dir / "session_info.json"
        
        logger.info(f"Google One storage session directory: {self.session_dir}")
    
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
    
    def parse_storage_value(self, text: str) -> float:
        """Parse storage value from text like '13.88 GB' or '2 TB'"""
        try:
            # Remove any extra spaces and split
            parts = text.strip().split()
            if len(parts) >= 2:
                value = float(parts[0].replace(',', ''))
                unit = parts[1].upper()
                
                # Convert to GB
                if unit == 'TB':
                    return value * 1024
                elif unit == 'GB':
                    return value
                elif unit == 'MB':
                    return value / 1024
                elif unit == 'KB':
                    return value / (1024 * 1024)
                else:
                    return value  # Assume GB if no unit
            return 0.0
        except Exception as e:
            logger.warning(f"Could not parse storage value '{text}': {e}")
            return 0.0
    
    async def get_storage_metrics(self, 
                                google_email: str = None,
                                google_password: str = None,
                                force_fresh_login: bool = False) -> Dict[str, Any]:
        """Get current storage metrics from Google One.
        
        Navigates to one.google.com/storage and extracts the storage
        breakdown by service. This is used for tracking transfer progress
        based on actual storage growth in Google Photos.
        
        **Authentication Flow**:
        1. Tries to use saved session if valid (<7 days old)
        2. Falls back to fresh login if needed
        3. Handles 2-Step Verification
        4. Saves session for future use
        
        Args:
            google_email: Google account email (required for fresh login)
            google_password: Google account password (required for fresh login)
            force_fresh_login: Force new login even if session exists
        
        Returns:
            Dict containing:
                - status: "success" or "error"
                - total_storage_gb: Total available storage (e.g., 2048 for 2TB)
                - used_storage_gb: Total storage used
                - available_storage_gb: Storage remaining
                - google_photos_gb: Storage used by Google Photos
                - google_drive_gb: Storage used by Google Drive
                - gmail_gb: Storage used by Gmail
                - device_backup_gb: Storage used by device backups
                - timestamp: When the data was captured
                - session_used: Whether saved session was used
                - error: Error message if status is "error"
        
        Example Response:
            {
                "status": "success",
                "total_storage_gb": 2048.0,
                "used_storage_gb": 99.75,
                "available_storage_gb": 1948.25,
                "google_photos_gb": 13.88,
                "google_drive_gb": 52.52,
                "gmail_gb": 33.26,
                "device_backup_gb": 0.06,
                "timestamp": "2025-08-26T10:00:00",
                "session_used": true
            }
        """
        try:
            # Check for existing session
            use_saved_session = self.is_session_valid() and not force_fresh_login
            
            if not self.playwright:
                await self.initialize()
            
            # Launch browser
            # Always run headless in demo mode, show browser in normal mode for debugging
            is_demo = os.getenv("DEMO_MODE", "").lower() == "true"
            self.browser = await self.playwright.chromium.launch(
                headless=is_demo,  # Headless in demo mode, visible otherwise
                args=['--disable-blink-features=AutomationControlled']
            )
            
            if is_demo:
                logger.info("Demo mode: Google Storage client running headless")
            
            if use_saved_session:
                logger.info("Using saved Google session")
                # Create context with saved state
                self.context = await self.browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1920, "height": 1080}
                )
            else:
                logger.info("Creating new Google browser context")
                # Create new context
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
            
            self.page = await self.context.new_page()
            
            # Apply stealth if available
            if STEALTH_AVAILABLE:
                await stealth_async(self.page)
            
            # Navigate to Google One Storage
            logger.info("Navigating to Google One Storage...")
            await self.page.goto("https://one.google.com/storage", wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Check if we need to sign in
            if "accounts.google.com" in current_url or "signin" in current_url.lower():
                if not google_email or not google_password:
                    return {
                        "status": "error",
                        "error": "Google credentials required for sign-in"
                    }
                
                logger.info("Need to sign in to Google...")
                
                # Enter email
                email_input = await self.page.wait_for_selector('input[type="email"]', timeout=10000)
                await email_input.fill(google_email)
                await self.page.press('input[type="email"]', 'Enter')
                
                # Wait for password field
                await self.page.wait_for_timeout(2000)
                
                # Enter password
                password_input = await self.page.wait_for_selector('input[type="password"]', timeout=10000)
                await password_input.fill(google_password)
                await self.page.press('input[type="password"]', 'Enter')
                
                # Wait for 2FA or redirect
                await self.page.wait_for_timeout(5000)
                
                # Check if 2-Step Verification is needed
                if "signin/v2/challenge" in self.page.url:
                    logger.info("2-Step Verification required - check your phone")
                    # Wait for user to complete 2FA (up to 2 minutes)
                    await self.page.wait_for_url("**/storage**", timeout=120000)
                
                # Save session after successful login
                if not use_saved_session:
                    await self.save_session()
            
            # Wait for storage page to load
            await self.page.wait_for_timeout(3000)
            
            # Now extract storage metrics
            logger.info("Extracting storage metrics...")
            
            # Initialize result
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "session_used": use_saved_session
            }
            
            # Try multiple selectors for storage information
            # Google One shows storage in various formats
            
            # Get total and used storage from the main heading
            try:
                # First try to find the main storage text like "86.91 GB of 2 TB used"
                storage_text = None
                
                # Try more specific selectors first
                storage_selectors = [
                    'h1',  # Main heading usually contains storage info
                    '[class*="storage"]',  # Any element with storage in class
                    '[aria-label*="storage"]',  # Accessibility labels
                    'div[role="heading"]',  # Heading roles
                ]
                
                for selector in storage_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            try:
                                text = await element.inner_text()
                                # Look for pattern like "X GB of Y TB"
                                if re.search(r'\d+\.?\d*\s*(GB|TB|MB)\s+of\s+\d+\.?\d*\s*(GB|TB|MB)', text):
                                    storage_text = text
                                    logger.info(f"Found storage text via {selector}: {text}")
                                    break
                            except:
                                continue
                        if storage_text:
                            break
                    except:
                        continue
                
                # If not found, search all text elements
                if not storage_text:
                    all_text_elements = await self.page.query_selector_all('div, span, h1, h2, h3, p')
                    for element in all_text_elements[:100]:  # Limit to first 100 elements
                        try:
                            text = await element.inner_text()
                            # Look for the storage pattern
                            if re.search(r'\d+\.?\d*\s*(GB|TB|MB)\s+of\s+\d+\.?\d*\s*(GB|TB|MB)', text):
                                storage_text = text
                                logger.info(f"Found storage text: {text}")
                                break
                        except:
                            continue
                
                # Parse the storage text
                if storage_text:
                    # Extract pattern like "86.91 GB of 2 TB used"
                    match = re.search(r'([\d.]+)\s*(GB|TB|MB)\s+of\s+([\d.]+)\s*(GB|TB|MB)', storage_text)
                    if match:
                        used_value = float(match.group(1))
                        used_unit = match.group(2).upper()
                        total_value = float(match.group(3))
                        total_unit = match.group(4).upper()
                        
                        # Convert to GB
                        if used_unit == 'TB':
                            used_value *= 1024
                        elif used_unit == 'MB':
                            used_value /= 1024
                            
                        if total_unit == 'TB':
                            total_value *= 1024
                        elif total_unit == 'MB':
                            total_value /= 1024
                        
                        result["used_storage_gb"] = round(used_value, 2)
                        result["total_storage_gb"] = round(total_value, 2)
                        result["available_storage_gb"] = round(total_value - used_value, 2)
                        logger.info(f"Parsed storage: {used_value:.2f}GB of {total_value:.2f}GB")
                else:
                    logger.warning("Could not find storage text on page")
            except Exception as e:
                logger.warning(f"Could not extract total storage: {e}")
            
            # Get service breakdown from the storage details section
            # Looking for patterns like "Google Photos" followed by storage amount
            try:
                # Wait a bit for dynamic content to load
                await self.page.wait_for_timeout(1000)
                
                service_data = {}
                
                # Look for service names and their corresponding values
                # The page structure shows service names and values as separate elements
                service_mappings = [
                    ('Google Photos', 'google_photos_gb'),
                    ('Google Drive', 'google_drive_gb'),
                    ('Gmail', 'gmail_gb'),
                    ('Device backup', 'device_backup_gb'),
                    ('Family storage', 'family_storage_gb')
                ]
                
                for service_name, field_name in service_mappings:
                    try:
                        # Try to find elements containing the service name
                        elements = await self.page.query_selector_all(f'text="{service_name}"')
                        for element in elements:
                            try:
                                # Get the parent element
                                parent = await element.evaluate_handle('el => el.parentElement')
                                if parent:
                                    parent_text = await parent.inner_text()
                                    # Look for storage value in the parent element
                                    # Pattern matches values like "52.52 GB" but not "2 TB of storage"
                                    match = re.search(r'^([\d.]+)\s*(GB|MB|TB)$', parent_text.strip(), re.MULTILINE)
                                    if match:
                                        value = self.parse_storage_value(match.group(0))
                                        service_data[field_name] = value
                                        logger.info(f"Found {service_name}: {match.group(0)}")
                                        break
                                    
                                    # Also try to get next sibling
                                    next_sibling = await parent.evaluate_handle('el => el.nextElementSibling')
                                    if next_sibling:
                                        sibling_text = await next_sibling.inner_text()
                                        match = re.search(r'^([\d.]+)\s*(GB|MB|TB)$', sibling_text.strip(), re.MULTILINE)
                                        if match:
                                            value = self.parse_storage_value(match.group(0))
                                            service_data[field_name] = value
                                            logger.info(f"Found {service_name}: {match.group(0)}")
                                            break
                            except:
                                continue
                    except:
                        continue
                
                # If we didn't find services with the above method, try a different approach
                # Look for the STORAGE DETAILS section
                if not service_data:
                    try:
                        # Get all text content and find the STORAGE DETAILS section
                        page_text = await self.page.content()
                        
                        # Look for patterns in the storage details section
                        # These patterns appear to be service name followed by amount on the next line
                        patterns = [
                            (r'Google Drive[\s\n]+([\d.]+)\s*(GB|MB|TB)', 'google_drive_gb'),
                            (r'Gmail[\s\n]+([\d.]+)\s*(GB|MB|TB)', 'gmail_gb'),
                            (r'Google Photos[\s\n]+([\d.]+)\s*(GB|MB|TB)', 'google_photos_gb'),
                            (r'Device backup[\s\n]+([\d.]+)\s*(GB|MB|TB)', 'device_backup_gb'),
                            (r'Family storage[\s\n]+.*?[\s\n]+([\d.]+)\s*(GB|MB|TB)', 'family_storage_gb'),
                        ]
                        
                        for pattern, field_name in patterns:
                            match = re.search(pattern, page_text)
                            if match:
                                value_str = f"{match.group(1)} {match.group(2)}"
                                value = self.parse_storage_value(value_str)
                                service_data[field_name] = value
                                logger.info(f"Found {field_name}: {value_str}")
                    except:
                        pass
                
                # Update result with found service data
                if service_data:
                    result.update(service_data)
                    logger.info(f"Service breakdown found: {service_data}")
                else:
                    logger.warning("Could not extract service breakdown")
                
            except Exception as e:
                logger.warning(f"Could not extract service breakdown: {e}")
            
            # Set defaults for any missing values
            result.setdefault("google_photos_gb", 0.0)
            result.setdefault("google_drive_gb", 0.0)
            result.setdefault("gmail_gb", 0.0)
            result.setdefault("device_backup_gb", 0.0)
            
            # Take a screenshot for verification
            screenshot_path = get_screenshot_dir() / f"google_one_storage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            # Don't close browser - keep it open for reuse
            # Browser will be closed in cleanup() method when done
            pass
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# For backwards compatibility with existing code
GoogleOneClient = GoogleStorageClient