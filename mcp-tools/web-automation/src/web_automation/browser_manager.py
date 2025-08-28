"""
Browser Manager for CDP Connection and Tab Reuse

Manages connection to an existing Chromium browser instance via Chrome DevTools Protocol.
This enables reusing browser windows and tabs during demos instead of launching new instances.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Optional, Any, List
from pathlib import Path
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages browser connections and tab reuse for demo mode.
    
    In demo mode, connects to an already-running Chromium instance
    via CDP (Chrome DevTools Protocol) and reuses tabs for different
    services instead of launching new browser windows.
    
    Features:
        - Connect to existing browser via CDP
        - Reuse tabs for different services
        - Maintain tab state across operations
        - Fallback to normal browser launch
    """
    
    _instance = None
    _browser: Optional[Browser] = None
    _playwright = None
    _tabs: Dict[str, Page] = {}
    _demo_mode: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure one browser connection."""
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize browser manager."""
        if not hasattr(self, 'initialized'):
            self.cdp_url = os.getenv("CDP_URL", "http://localhost:9222")
            self.demo_mode = os.getenv("DEMO_MODE", "").lower() == "true"
            self.initialized = True
            logger.info(f"BrowserManager initialized. Demo mode: {self.demo_mode}")
    
    async def ensure_playwright(self):
        """Ensure playwright is started."""
        if not self._playwright:
            self._playwright = await async_playwright().start()
        return self._playwright
    
    async def check_browser_cdp(self) -> bool:
        """
        Check if a browser is already running with CDP enabled.
        
        Returns:
            True if browser is accessible via CDP, False otherwise
        """
        import urllib.request
        try:
            with urllib.request.urlopen(f"{self.cdp_url}/json/version", timeout=1) as response:
                if response.status == 200:
                    logger.info(f"Found existing browser with CDP on {self.cdp_url}")
                    return True
        except Exception:
            return False
        return False
    
    async def connect_to_existing_browser(self) -> Optional[Browser]:
        """
        Connect to an existing browser instance via CDP.
        Launches browser if not already running in demo mode.
        
        Returns:
            Browser instance if connection successful, None otherwise
        """
        try:
            playwright = await self.ensure_playwright()
            
            logger.info(f"Attempting to connect to browser at {self.cdp_url}")
            
            # Check if browser is already running with CDP
            browser_running = await self.check_browser_cdp()
            
            if not browser_running:
                if self.demo_mode:
                    logger.error(
                        "\n" +
                        "="*60 + "\n" +
                        "DEMO MODE: Browser Not Found\n" +
                        "\n" +
                        "Please launch Chromium with CDP enabled:\n" +
                        "\n" +
                        "  /Applications/Chromium.app/Contents/MacOS/Chromium \\\n" +
                        "    --remote-debugging-port=9222\n" +
                        "\n" +
                        "Or if using Chrome:\n" +
                        "\n" +
                        "  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n" +
                        "    --remote-debugging-port=9222\n" +
                        "\n" +
                        "="*60
                    )
                    return None
                else:
                    logger.debug("No existing browser found with CDP")
                    return None
            
            try:
                self._browser = await playwright.chromium.connect_over_cdp(
                    self.cdp_url
                )
            except Exception as e:
                logger.error(f"Failed to connect to browser: {e}")
                return None
            
            # Get existing contexts
            contexts = self._browser.contexts
            if contexts:
                logger.info(f"Connected to browser with {len(contexts)} context(s)")
                # Use the default context
                context = contexts[0]
                
                # Log existing pages
                pages = context.pages
                logger.info(f"Found {len(pages)} existing page(s)")
                for i, page in enumerate(pages):
                    logger.info(f"  Page {i}: {page.url}")
            else:
                logger.warning("No contexts found in connected browser")
            
            return self._browser
            
        except Exception as e:
            logger.error(f"Failed to connect to browser via CDP: {e}")
            return None
    
    async def get_browser(self) -> Optional[Browser]:
        """
        Get browser instance, connecting if necessary.
        
        In demo mode: Connects to existing browser via CDP
        In normal mode: Returns None (caller should launch new browser)
        """
        if not self.demo_mode:
            return None
        
        if not self._browser:
            self._browser = await self.connect_to_existing_browser()
        
        return self._browser
    
    async def get_or_create_tab(self, 
                                service_name: str, 
                                url: Optional[str] = None,
                                reuse: bool = True) -> Optional[Page]:
        """
        Get existing tab or create new one for a service.
        
        Args:
            service_name: Name of the service (e.g., "icloud", "google")
            url: Optional URL to navigate to
            reuse: Whether to reuse existing tab for this service
        
        Returns:
            Page object if in demo mode, None otherwise (caller creates own)
        """
        if not self.demo_mode:
            return None
        
        browser = await self.get_browser()
        if not browser:
            return None
        
        # Check for existing tab
        if reuse and service_name in self._tabs:
            page = self._tabs[service_name]
            try:
                # Check if page is still valid
                await page.title()
                logger.info(f"Reusing existing tab for {service_name}")
                
                # Navigate to new URL if provided
                if url and page.url != url:
                    logger.info(f"Navigating {service_name} tab to {url}")
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(1000)
                
                return page
            except Exception as e:
                logger.warning(f"Existing tab for {service_name} is invalid: {e}")
                del self._tabs[service_name]
        
        # Create new tab
        try:
            contexts = browser.contexts
            if not contexts:
                logger.error("No browser contexts available")
                return None
            
            context = contexts[0]
            page = await context.new_page()
            
            # Store reference
            self._tabs[service_name] = page
            
            # Navigate to URL if provided
            if url:
                logger.info(f"Creating new tab for {service_name} at {url}")
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1000)
            else:
                logger.info(f"Created new tab for {service_name}")
            
            return page
            
        except Exception as e:
            logger.error(f"Failed to create tab for {service_name}: {e}")
            return None
    
    async def close_tab(self, service_name: str):
        """Close a specific service tab."""
        if service_name in self._tabs:
            try:
                await self._tabs[service_name].close()
                del self._tabs[service_name]
                logger.info(f"Closed tab for {service_name}")
            except Exception as e:
                logger.error(f"Error closing tab for {service_name}: {e}")
    
    async def list_tabs(self) -> List[Dict[str, str]]:
        """List all managed tabs."""
        tabs = []
        for name, page in self._tabs.items():
            try:
                tabs.append({
                    "service": name,
                    "url": page.url,
                    "title": await page.title()
                })
            except:
                tabs.append({
                    "service": name,
                    "url": "unknown",
                    "title": "invalid"
                })
        return tabs
    
    async def cleanup(self):
        """Clean up browser connection."""
        # Close all managed tabs
        for service_name in list(self._tabs.keys()):
            await self.close_tab(service_name)
        
        # Don't close the browser in demo mode (it's external)
        if self.demo_mode and self._browser:
            logger.info("Disconnecting from browser (keeping it open)")
            self._browser = None
        
        # Stop playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    @classmethod
    async def get_instance(cls) -> 'BrowserManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Convenience functions
async def get_demo_page(service_name: str, url: Optional[str] = None) -> Optional[Page]:
    """
    Convenience function to get a page for demo mode.
    
    Returns None if not in demo mode, allowing caller to handle normally.
    """
    manager = await BrowserManager.get_instance()
    return await manager.get_or_create_tab(service_name, url)


async def is_demo_mode() -> bool:
    """Check if running in demo mode."""
    return os.getenv("DEMO_MODE", "").lower() == "true"