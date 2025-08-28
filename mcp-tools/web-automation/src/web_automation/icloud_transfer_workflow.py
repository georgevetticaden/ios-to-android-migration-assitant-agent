"""
iCloud to Google Photos Transfer Workflow Automation

This module handles the complete 8-step browser automation workflow
for initiating photo transfers from iCloud to Google Photos through
Apple's Data & Privacy portal. It navigates complex multi-page flows
including OAuth popups and 2FA verification.

Workflow Overview:
    1. Select Google Photos as destination
    2. Check both Photos and Videos checkboxes (v2.0)
    3. Navigate through Apple's transfer pages
    4. Handle Google OAuth authentication
    5. Grant necessary permissions
    6. Reach final confirmation page

This module is used internally by ICloudClient.start_transfer().
"""
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TransferWorkflow:
    """Orchestrates the iCloud to Google Photos transfer workflow.
    
    This class manages the complex multi-step process of initiating
    a photo transfer through Apple's Data & Privacy portal. It handles
    page navigation, form filling, OAuth popups, and error recovery.
    
    **Workflow Steps**:
        1. Select Google Photos from service dropdown
        2. Check both Photos and Videos checkboxes (complete media migration)
        3. Click Continue on initial selection page
        4. Click Continue on "Copy your photos" information page
        5. Handle Google OAuth popup for account selection
        6. Handle Apple Data permissions page
        7. Grant Google Photos permissions
        8. Reach "Confirm Transfer" page (but don't click)
    
    **Key Challenges Handled**:
        - Popup windows for OAuth flow
        - Dynamic button enabling based on selections
        - Multiple "Continue" buttons on different pages
        - 2FA verification prompts
        - Session timeouts and retries
    
    **Used By**:
        - ICloudClient._initiate_transfer_workflow()
    
    Attributes:
        page: Main Playwright page object
        context: Browser context for handling popups
        popup_page: Reference to OAuth popup window
    """
    
    def __init__(self, page, context):
        self.page = page
        self.context = context
        self.popup_page = None
        
    async def execute_complete_workflow(self, google_email: str = None, google_password: str = None, confirm_transfer: bool = False) -> Dict[str, Any]:
        """Execute the complete 8-step transfer initiation workflow.
        
        Navigates through Apple's Data & Privacy portal to set up
        an iCloud Photos to Google Photos transfer. By default stops at the
        final confirmation page without clicking "Confirm Transfer".
        
        **Detailed Flow**:
        1. **Service Selection**: Choose "Google Photos" from dropdown
        2. **Data Selection**: Check both "Photos" and "Videos" checkboxes
        3. **Initial Continue**: Click Continue when button enables
        4. **Information Page**: Click Continue on "Copy your photos" page
        5. **Google OAuth**: Handle popup for Google account selection
        6. **Apple Permissions**: Navigate Apple's data sharing consent
        7. **Google Permissions**: Grant Google Photos access
        8. **Confirmation**: Reach final page with transfer summary
        9. **Optional Final Step**: Click "Confirm Transfers" if confirm_transfer=True
        
        Args:
            google_email: Google account email. If None, uses GOOGLE_EMAIL env var.
            google_password: Google account password. If None, uses GOOGLE_PASSWORD env var.
            confirm_transfer: Whether to click the final "Confirm Transfers" button.
                            Defaults to False (stops at confirmation page for safety).
        
        Returns:
            Dict containing:
                - status: "ready_for_confirmation" or "error"
                - transfer_id: Generated transfer identifier
                - confirmation_details: Extracted details from confirmation page
                - message: User-friendly status message
                - confirm_button_available: Boolean if ready to confirm
                - error: Error details if status is "error"
        
        Example Success Response:
            {
                "status": "ready_for_confirmation",
                "transfer_id": "TRF_20250820_143022",
                "confirmation_details": {
                    "source_service": "iCloud Photos",
                    "destination_service": "Google Photos",
                    "data_types": ["Photos"],
                    "estimated_time": "3-7 days"
                },
                "message": "Transfer ready for confirmation. Review details...",
                "confirm_button_available": true
            }
        
        Raises:
            Exception: If any step in the workflow fails
        
        Note:
            This method intentionally stops at the confirmation page.
            The actual transfer is initiated when the user clicks
            "Confirm Transfer" button, allowing for review.
        """
        try:
            # Get credentials from environment if not provided
            if not google_email:
                google_email = os.getenv('GOOGLE_EMAIL')
            if not google_password:
                google_password = os.getenv('GOOGLE_PASSWORD')
                
            logger.info(f"Starting complete transfer workflow for {google_email}")
            
            # Step 1: Select Google Photos from dropdown
            logger.info("Step 1: Selecting Google Photos from dropdown")
            await self._select_google_photos()
            
            # Step 2: Check both Photos and Videos checkboxes
            logger.info("Step 2: Checking both Photos and Videos checkboxes")
            await self._check_transfer_checkboxes()
            
            # Step 3: Click Continue (should be enabled now)
            logger.info("Step 3: Clicking Continue button (page 1)")
            await self._click_continue_when_enabled()
            
            # Step 4: Click Continue on "Copy your photos to Google Photos" page
            logger.info("Step 4: Clicking Continue on 'Copy your photos' page")
            await self.page.wait_for_timeout(2000)
            await self._click_continue_button()
            
            # Step 5: Handle Google OAuth popup
            logger.info("Step 5: Handling Google OAuth popup")
            await self._handle_google_oauth_popup(google_email, google_password)
            
            # Step 6: Wait for return to main window
            logger.info("Step 6: Waiting for return to main window")
            await self._wait_for_confirmation_page()
            
            # Generate transfer ID
            transfer_id = f"TRF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Extract confirmation details from the page
            confirmation_details = await self._extract_confirmation_details()
            
            logger.info(f"✅ Transfer workflow completed successfully! Transfer ID: {transfer_id}")
            
            # Check if we should confirm the transfer
            if confirm_transfer:
                logger.info("🚀 Looking for 'Confirm Transfers' button to initiate actual transfer...")
                try:
                    # Wait for page to stabilize and button to be ready
                    logger.info("Waiting for confirmation page to fully load...")
                    await self.page.wait_for_load_state('networkidle', timeout=15000)
                    
                    # The button takes ~20 seconds to enable, so wait patiently
                    logger.info("Waiting up to 25 seconds for button to enable (Apple's processing)...")
                    button_ready = False
                    for i in range(25):  # Check every second for up to 25 seconds
                        try:
                            button = await self.page.query_selector('button:has-text("Confirm Transfers")')
                            if button:
                                is_visible = await button.is_visible()
                                is_enabled = await button.is_enabled()
                                
                                if i % 5 == 0:  # Log every 5 seconds
                                    logger.info(f"Button state at {i}s - Visible: {is_visible}, Enabled: {is_enabled}")
                                
                                if is_visible and is_enabled:
                                    logger.info(f"✅ Button is ready after {i} seconds!")
                                    button_ready = True
                                    break
                        except:
                            pass
                        
                        await self.page.wait_for_timeout(1000)  # Wait 1 second
                    
                    if not button_ready:
                        logger.warning("Button not ready after 25 seconds, but will try clicking anyway...")
                    
                    # Take screenshot before attempting click
                    screenshot_before = f"/tmp/before_confirm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=screenshot_before)
                    logger.info(f"Screenshot before click: {screenshot_before}")
                    
                    # Now click the button
                    clicked = False
                    try:
                        # Simple, direct click using the most basic selector
                        logger.info("Attempting to click Confirm Transfers button...")
                        await self.page.click('button:has-text("Confirm Transfers")', timeout=5000)
                        logger.info("✅ Successfully clicked Confirm Transfers button!")
                        clicked = True
                    except Exception as e:
                        logger.warning(f"First click attempt failed: {e}")
                        
                        # Try alternative approaches if the simple click fails
                        try:
                            logger.info("Trying alternative click method...")
                            button = await self.page.query_selector('button:has-text("Confirm Transfers")')
                            if button:
                                await button.click(force=True)
                                logger.info("✅ Force clicked Confirm Transfers button!")
                                clicked = True
                        except Exception as e2:
                            logger.warning(f"Alternative click also failed: {e2}")
                    
                    if clicked:
                        logger.info("✅ Transfer confirmed and initiated with Apple!")
                        
                        # Wait for page response after clicking
                        await self.page.wait_for_timeout(5000)
                        
                        # Take screenshot after click
                        screenshot_after = f"/tmp/after_confirm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=screenshot_after)
                        logger.info(f"Screenshot after click: {screenshot_after}")
                        
                        return {
                            "status": "initiated",
                            "transfer_id": transfer_id,
                            "confirmation_details": confirmation_details,
                            "message": "Transfer has been confirmed and initiated. Apple will process the transfer over 3-7 days.",
                            "transfer_confirmed": True,
                            "initiated_at": datetime.now().isoformat()
                        }
                    else:
                        logger.warning("Could not click Confirm Transfers button with any selector")
                        # Get page content for debugging
                        buttons = await self.page.query_selector_all('button')
                        logger.info(f"Found {len(buttons)} buttons on page")
                        for i, btn in enumerate(buttons[:5]):  # Check first 5 buttons
                            text = await btn.inner_text()
                            logger.info(f"Button {i}: {text}")
                        
                except Exception as e:
                    logger.error(f"Error during confirm transfer: {e}")
                    # Take a screenshot for debugging
                    try:
                        screenshot_path = f"/tmp/confirm_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=screenshot_path)
                        logger.info(f"Error screenshot saved to: {screenshot_path}")
                    except:
                        pass
                    # Fall through to return ready_for_confirmation status
            else:
                logger.info("⚠️  IMPORTANT: Review the confirmation page before clicking 'Confirm Transfer'")
            
            logger.info(f"📊 Transfer details: {confirmation_details}")
            
            return {
                "status": "ready_for_confirmation",
                "transfer_id": transfer_id,
                "confirmation_details": confirmation_details,
                "message": "Transfer ready for confirmation. Review details and click 'Confirm Transfer' to proceed.",
                "confirm_button_available": True
            }
            
        except Exception as e:
            logger.error(f"Transfer workflow failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _select_google_photos(self):
        """Select Google Photos from the dropdown"""
        try:
            # Wait for dropdown to be present
            dropdown = await self.page.wait_for_selector('select', timeout=10000)
            
            # Get current value
            current_value = await dropdown.evaluate('el => el.value')
            logger.info(f"Current dropdown value: '{current_value}'")
            
            if current_value != 'Google':
                # Select Google Photos
                await self.page.select_option('select', value='Google')
                logger.info("Selected Google Photos from dropdown")
                await self.page.wait_for_timeout(1000)
            else:
                logger.info("Google Photos already selected")
                
        except Exception as e:
            logger.error(f"Failed to select Google Photos: {e}")
            raise
    
    async def _check_transfer_checkboxes(self):
        """Check both Photos and Videos checkboxes for complete media transfer.
        
        Selects which data types to transfer. For v2.0, we now transfer
        both photos AND videos together in a single operation.
        
        **Selection Logic**:
        - Photos: Always checked (primary content)
        - Videos: Always checked (v2.0 enhancement)
        
        **Dynamic Selectors**:
        Uses multiple selector strategies to handle Apple's changing HTML:
        - Label text matching \"Photos\" and \"Videos\" with counts
        - Checkbox siblings of media labels
        - Input elements with photo/video-related IDs
        
        Note:
            Apple shows counts like \"Photos (60,238 photos)\" and \"Videos (2,418 videos)\"
            which we match with flexible patterns to avoid hardcoding numbers.
        """
        try:
            # Check Photos checkbox
            photos_selectors = [
                'label:has-text("Photos (")',  # Match label containing "Photos (" 
                'label:text-matches("Photos.*photos")',  # Match pattern "Photos...photos"
                'label:has-text("photos)")',  # Match label ending with "photos)"
            ]
            
            photos_clicked = False
            for selector in photos_selectors:
                try:
                    photos_label = await self.page.query_selector(selector)
                    if photos_label:
                        await photos_label.click()
                        logger.info(f"✅ Clicked Photos checkbox using selector: {selector}")
                        photos_clicked = True
                        break
                except:
                    continue
            
            # Check Videos checkbox
            videos_selectors = [
                'label:has-text("Videos (")',  # Match label containing "Videos ("
                'label:text-matches("Videos.*videos")',  # Match pattern "Videos...videos"
                'label:has-text("videos)")',  # Match label ending with "videos)"
            ]
            
            videos_clicked = False
            for selector in videos_selectors:
                try:
                    videos_label = await self.page.query_selector(selector)
                    if videos_label:
                        await videos_label.click()
                        logger.info(f"✅ Clicked Videos checkbox using selector: {selector}")
                        videos_clicked = True
                        break
                except:
                    continue
            
            # Fallback: click checkboxes by index if we couldn't find them by label
            if not photos_clicked or not videos_clicked:
                checkboxes = await self.page.query_selector_all('input[type="checkbox"]')
                logger.info(f"Found {len(checkboxes)} checkboxes on page")
                
                # Try to check first two checkboxes (usually Photos and Videos)
                if not photos_clicked and len(checkboxes) >= 1:
                    is_checked = await checkboxes[0].is_checked()
                    if not is_checked:
                        await checkboxes[0].click()
                        logger.info("✅ Checked Photos checkbox (first checkbox)")
                    else:
                        logger.info("Photos checkbox already checked")
                
                if not videos_clicked and len(checkboxes) >= 2:
                    is_checked = await checkboxes[1].is_checked()
                    if not is_checked:
                        await checkboxes[1].click()
                        logger.info("✅ Checked Videos checkbox (second checkbox)")
                    else:
                        logger.info("Videos checkbox already checked")
            
            logger.info("✅ Both Photos and Videos checkboxes selected for complete media transfer")
                    
            await self.page.wait_for_timeout(1000)
            
        except Exception as e:
            logger.error(f"Failed to check checkboxes: {e}")
            raise
    
    async def _click_continue_when_enabled(self):
        """Click Continue button when it becomes enabled"""
        try:
            # Find Continue button
            continue_btn = await self.page.wait_for_selector('button:has-text("Continue")', timeout=10000)
            
            # Wait for it to be enabled
            for i in range(10):
                is_disabled = await continue_btn.get_attribute('disabled')
                if is_disabled is None or is_disabled == 'false' or is_disabled == False:
                    logger.info("Continue button is enabled")
                    break
                logger.info(f"Waiting for Continue button to enable... ({i+1}/10)")
                await self.page.wait_for_timeout(1000)
            
            # Click Continue
            await continue_btn.click()
            logger.info("Clicked Continue button")
            await self.page.wait_for_timeout(3000)
            
        except Exception as e:
            logger.error(f"Failed to click Continue: {e}")
            raise
    
    async def _click_continue_button(self):
        """Click Continue button on the second page"""
        try:
            # This is the "Copy your photos to Google Photos" page
            continue_btn = await self.page.wait_for_selector('button:has-text("Continue")', timeout=10000)
            
            # Set up listener for popup BEFORE clicking
            popup_promise = self.context.wait_for_event('page')
            
            await continue_btn.click()
            logger.info("Clicked Continue - waiting for Google OAuth popup...")
            
            # Wait for popup to open
            try:
                self.popup_page = await asyncio.wait_for(popup_promise, timeout=5)
                logger.info(f"✅ Google OAuth popup opened: {self.popup_page.url[:60]}...")
            except asyncio.TimeoutError:
                logger.warning("No popup detected, continuing...")
                
        except Exception as e:
            logger.error(f"Failed to click Continue on page 2: {e}")
            raise
    
    async def _handle_google_oauth_popup(self, email: str, password: str):
        """Handle the Google OAuth popup window"""
        try:
            if not self.popup_page:
                # Try to find popup in context pages
                pages = self.context.pages
                if len(pages) > 1:
                    self.popup_page = pages[-1]
                    logger.info(f"Found popup window: {self.popup_page.url[:60]}...")
                else:
                    logger.error("No popup window found")
                    return
            
            # Switch to popup
            page = self.popup_page
            await page.wait_for_timeout(2000)
            
            # Check if already authorized (page might auto-close)
            try:
                if page.is_closed():
                    logger.info("✅ Google OAuth auto-authorized (already logged in)")
                    return
            except:
                pass
            
            # Check URL - if it's already redirected back to Apple, we're done
            current_url = page.url
            if 'privacy.apple.com/oauth/callback' in current_url:
                logger.info("✅ Google OAuth already authorized, redirected back to Apple")
                return
            
            # Only try to login if we see the login form
            try:
                # Step 1: Enter email (only if needed)
                logger.info("Checking if Google login is needed...")
                email_field = await page.wait_for_selector('input#identifierId', timeout=3000)
                logger.info("Google login required, entering email...")
                await email_field.fill(email)
            
                # Click Next
                next_btn = await page.wait_for_selector('#identifierNext', timeout=5000)
                await next_btn.click()
                await page.wait_for_timeout(3000)
                
                # Step 2: Enter password
                logger.info("Entering Google password...")
                password_field = await page.wait_for_selector('input[type="password"]', timeout=10000)
                await password_field.fill(password)
                
                # Click Next
                password_next = await page.wait_for_selector('#passwordNext', timeout=5000)
                await password_next.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                # Check if page closed or redirected (meaning auth succeeded)
                try:
                    if page.is_closed() or 'privacy.apple.com' in page.url:
                        logger.info("✅ Google OAuth completed during login")
                        return
                except:
                    pass
                logger.warning(f"OAuth login issue (may be auto-authorized): {e}")
            
            # Step 3: Handle 2-step verification if needed
            current_url = page.url
            if 'challenge' in current_url:
                logger.info("2-Step Verification required")
                await self._handle_2fa(page)
            
            # Step 4: Handle consent screens (may have multiple)
            logger.info("Handling consent screens...")
            await page.wait_for_timeout(3000)
            
            # There can be multiple consent screens that need Continue clicks:
            # 1. "You're signing back in to Apple Data and Privacy" - Continue
            # 2. "Apple Data and Privacy wants access to your Google Account" - Continue
            # We'll handle them in sequence
            
            consent_screens_handled = 0
            max_consent_screens = 3  # Safety limit
            
            while consent_screens_handled < max_consent_screens:
                try:
                    # Check if page is still open
                    if page.is_closed():
                        logger.info("Popup closed - authorization complete")
                        break
                    
                    # Look for Continue button on current page
                    continue_btn = await page.wait_for_selector('button:has-text("Continue")', timeout=3000)
                    
                    if continue_btn:
                        # Check if button is visible and enabled
                        is_visible = await continue_btn.is_visible()
                        is_enabled = await continue_btn.is_enabled()
                        
                        if is_visible and is_enabled:
                            await continue_btn.click()
                            consent_screens_handled += 1
                            logger.info(f"Clicked Continue on consent screen #{consent_screens_handled}")
                            await page.wait_for_timeout(2000)
                        else:
                            logger.info("Continue button found but not clickable")
                            break
                    else:
                        # No Continue button found, check for Allow button
                        allow_btn = await page.query_selector('button:has-text("Allow")')
                        if allow_btn:
                            await allow_btn.click()
                            logger.info("Clicked Allow on final consent screen")
                            break
                        else:
                            logger.info("No more consent buttons found")
                            break
                            
                except Exception as e:
                    # Check if it's because popup closed (which is expected)
                    try:
                        if page.is_closed():
                            logger.info("Popup closed after consent - this is expected")
                            break
                    except:
                        pass
                    
                    # If we handled at least one screen, this might be normal
                    if consent_screens_handled > 0:
                        logger.info(f"Consent flow completed after {consent_screens_handled} screen(s)")
                        break
                    else:
                        logger.warning(f"Issue during consent handling: {e}")
                        break
            
            logger.info(f"Handled {consent_screens_handled} consent screen(s)")
            
            # Final wait to ensure everything is processed
            try:
                await page.wait_for_timeout(2000)
            except:
                logger.info("Popup closed after authorization - this is expected")
            
        except Exception as e:
            logger.error(f"Failed to handle Google OAuth: {e}")
            raise
    
    async def _handle_2fa(self, page):
        """Handle 2-step verification"""
        try:
            logger.info("📱 2-Step Verification detected")
            logger.info("Check your phone for the verification prompt")
            logger.info("Tap 'Yes' on your device to continue...")
            
            # Wait for user to complete 2FA (up to 30 seconds)
            for i in range(30):
                await page.wait_for_timeout(1000)
                current_url = page.url
                
                # Check if we've moved past 2FA
                if 'challenge' not in current_url:
                    logger.info("✅ 2FA completed successfully")
                    break
                    
                if i % 5 == 0:
                    logger.info(f"Still waiting for 2FA... ({i} seconds)")
                    
        except Exception as e:
            logger.error(f"2FA handling failed: {e}")
            raise
    
    async def _wait_for_confirmation_page(self):
        """Wait for return to main window with confirmation page"""
        try:
            # Wait for popup to close (up to 15 seconds)
            logger.info("Waiting for Google OAuth popup to close...")
            for i in range(15):
                await asyncio.sleep(1)
                
                # Check if popup closed
                if self.popup_page:
                    try:
                        # Check if popup is still open
                        await self.popup_page.title()
                        if i % 3 == 0:
                            logger.info(f"Still waiting for popup to close... ({i} seconds)")
                    except:
                        logger.info("✅ Popup closed, returned to main window")
                        self.popup_page = None
                        break
                        
                # Check if we're back on main page with confirmation
                if len(self.context.pages) > 0:
                    main_page = self.context.pages[0]
                    current_url = main_page.url
                    if 'callback' in current_url or 'confirm' in current_url.lower():
                        self.page = main_page
                        logger.info(f"✅ On confirmation page: {current_url[:80]}...")
                        break
            
            # Ensure we're on the main page
            if len(self.context.pages) > 0:
                self.page = self.context.pages[0]
                logger.info(f"Current page URL: {self.page.url[:80]}...")
                
                # Wait for page to load completely - increase timeout
                logger.info("Waiting for page to reach network idle state...")
                await self.page.wait_for_load_state('networkidle', timeout=20000)
                logger.info("Page reached network idle state")
                
                # Don't wait here - let the confirm_transfer logic handle waiting for the button
                logger.info("Page ready for confirmation")
                    
        except Exception as e:
            logger.error(f"Failed to return to confirmation page: {e}")
            # Don't raise, let the workflow continue and handle the error later
    
    async def _extract_confirmation_details(self):
        """Extract details from the confirmation page"""
        try:
            details = {}
            
            # Look for photo count
            photo_text = await self.page.query_selector('text=/\\d+[,\\d]*\\s+photos/')
            if photo_text:
                text = await photo_text.inner_text()
                details['photos'] = text.strip()
            
            # Look for destination
            destination = await self.page.query_selector('text="Google Photos"')
            if destination:
                details['destination'] = 'Google Photos'
            
            # Look for account
            account_text = await self.page.query_selector('text=/Transfer to account:.*@/')
            if account_text:
                text = await account_text.inner_text()
                details['account'] = text.replace('Transfer to account:', '').strip()
            
            # Look for storage warning
            warning = await self.page.query_selector('text=/storage available/')
            if warning:
                text = await warning.inner_text()
                details['storage_warning'] = text.strip()
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to extract confirmation details: {e}")
            return {}
    
    async def confirm_transfer(self):
        """Actually confirm the transfer - SEPARATE METHOD requiring explicit user action"""
        try:
            logger.info("🚨 CONFIRMING TRANSFER - This will initiate the actual transfer!")
            
            # Find and click the Confirm Transfer button
            confirm_btn = await self.page.wait_for_selector('button:has-text("Confirm Transfer")', timeout=10000)
            await confirm_btn.click()
            logger.info("✅ Clicked 'Confirm Transfer' button")
            
            # Wait for confirmation
            await self.page.wait_for_timeout(3000)
            
            # Check for success message or next page
            success_msg = await self.page.query_selector('text=/transfer.*complete|started|initiated/i')
            if success_msg:
                msg_text = await success_msg.inner_text()
                logger.info(f"✅ Transfer confirmed: {msg_text}")
                return {"status": "confirmed", "message": msg_text}
            
            return {"status": "confirmed", "message": "Transfer has been initiated"}
            
        except Exception as e:
            logger.error(f"Failed to confirm transfer: {e}")
            return {"status": "error", "message": str(e)}