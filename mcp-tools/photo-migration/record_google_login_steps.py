#!/usr/bin/env python3
"""
Record the exact steps needed to login to Google Dashboard
This will help us understand the exact flow and selectors needed
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from pathlib import Path

# Try to import playwright-stealth if available
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    print("Note: playwright-stealth not installed. Install with: pip install playwright-stealth")

async def record_login_steps():
    """
    Record the exact login flow step by step
    """
    
    print("=" * 60)
    print("GOOGLE DASHBOARD LOGIN RECORDER")
    print("=" * 60)
    print("\nThis will record the exact steps to login to Google Dashboard")
    print("\nIMPORTANT INSTRUCTIONS:")
    print("1. The browser will open to Google sign-in page")
    print("2. I will guide you through each step")
    print("3. We'll pause after each action to record what happened")
    print("4. This will help us understand the exact selectors and flow")
    
    print("\nYou'll need:")
    print("- Your Google email")
    print("- Your Google password")
    print("- Be ready for 2FA if needed")
    
    print("\nPress Enter to start...")
    input()
    
    async with async_playwright() as p:
        # Launch browser with stealth settings
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500,  # Slow down actions so they're visible
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            record_video_dir='recordings/login_flow/',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        
        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True)
        
        page = await context.new_page()
        
        # Apply stealth if available
        if STEALTH_AVAILABLE:
            await stealth_async(page)
            print("✅ Stealth mode enabled")
        
        steps = []
        
        # Step 1: Navigate to Google sign-in
        print("\n📍 STEP 1: Navigate to Google Sign-in")
        print("-" * 40)
        
        # Start directly at the signin page to avoid redirects
        signin_url = "https://accounts.google.com/v3/signin/identifier?continue=https://myaccount.google.com/dashboard&hl=en-US&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
        
        print(f"Navigating to: {signin_url[:60]}...")
        await page.goto(signin_url)
        await page.wait_for_load_state('networkidle')
        
        # Take screenshot
        await page.screenshot(path="screenshots/step1_signin_page.png")
        print("✅ Screenshot saved: step1_signin_page.png")
        
        # Record what we see
        print("\n🔍 Looking for email input field...")
        
        # Try to find the email field
        email_selectors = [
            'input#identifierId',
            'input[type="email"]',
            'input[name="identifier"]',
            'input[autocomplete="username"]'
        ]
        
        email_field = None
        for selector in email_selectors:
            try:
                email_field = await page.wait_for_selector(selector, timeout=2000)
                if email_field:
                    print(f"✅ Found email field with selector: {selector}")
                    steps.append(f"Email field selector: {selector}")
                    
                    # Get more info about the element
                    attrs = await email_field.evaluate('''el => {
                        return {
                            id: el.id,
                            name: el.name,
                            type: el.type,
                            placeholder: el.placeholder,
                            autocomplete: el.autocomplete
                        }
                    }''')
                    print(f"   Element attributes: {attrs}")
                    break
            except:
                continue
        
        if not email_field:
            print("❌ Could not find email field automatically")
            print("\nPlease click on the email field in the browser")
            print("Press Enter after clicking...")
            input()
        
        # Step 2: Find Next button
        print("\n📍 STEP 2: Find Next Button")
        print("-" * 40)
        
        next_selectors = [
            '#identifierNext',
            'button:has-text("Next")',
            'div#identifierNext',
            'button[jsname="LgbsSe"]',
            '//div[@id="identifierNext"]',
            '//button[contains(., "Next")]'
        ]
        
        next_button = None
        for selector in next_selectors:
            try:
                if selector.startswith('//'):
                    next_button = await page.wait_for_selector(f'xpath={selector}', timeout=2000)
                else:
                    next_button = await page.wait_for_selector(selector, timeout=2000)
                    
                if next_button:
                    print(f"✅ Found Next button with selector: {selector}")
                    steps.append(f"Next button selector: {selector}")
                    
                    # Check if it's visible and clickable
                    is_visible = await next_button.is_visible()
                    is_enabled = await next_button.is_enabled()
                    print(f"   Visible: {is_visible}, Enabled: {is_enabled}")
                    break
            except:
                continue
        
        if not next_button:
            print("❌ Could not find Next button")
            print("\nPlease point out the Next button")
        
        print("\n📍 MANUAL STEPS:")
        print("-" * 40)
        print("Now please manually:")
        print("1. Enter your email")
        print("2. Click Next")
        print("3. Enter your password")
        print("4. Click Next/Sign in")
        print("5. Complete 2FA if needed")
        print("\nPress Enter when you're on the dashboard...")
        input()
        
        # Check final URL
        final_url = page.url
        print(f"\n✅ Final URL: {final_url}")
        
        if 'myaccount.google.com' in final_url:
            print("✅ Successfully reached dashboard!")
            await page.screenshot(path="screenshots/step_final_dashboard.png")
            
            # Try to find photo count
            print("\n🔍 Looking for photo count on dashboard...")
            
            photo_selectors = [
                'text=/\\d+ photos?/i',
                '//div[contains(text(), "photos")]',
                '//span[contains(text(), "photos")]',
                '[aria-label*="Photos"]'
            ]
            
            for selector in photo_selectors:
                try:
                    if selector.startswith('//'):
                        element = await page.wait_for_selector(f'xpath={selector}', timeout=2000)
                    else:
                        element = await page.wait_for_selector(selector, timeout=2000)
                    
                    if element:
                        text = await element.text_content()
                        print(f"✅ Found photo element: {text}")
                        steps.append(f"Photo count selector: {selector}")
                        break
                except:
                    continue
        
        # Save the trace
        await context.tracing.stop(path="recordings/login_flow/trace.zip")
        
        # Print summary
        print("\n" + "=" * 60)
        print("RECORDING COMPLETE - SUMMARY")
        print("=" * 60)
        
        print("\n📝 Recorded Steps:")
        for i, step in enumerate(steps, 1):
            print(f"{i}. {step}")
        
        print("\n💡 Key Findings:")
        print("1. Login starts at: accounts.google.com/v3/signin/identifier")
        print("2. Email field selector: input#identifierId")
        print("3. Next button needs careful selection")
        print("4. Password page loads after email submission")
        print("5. Dashboard loads after successful login")
        
        print("\n📂 Recordings saved in:")
        print("- screenshots/step*.png")
        print("- recordings/login_flow/trace.zip")
        
        print("\nPress Enter to close browser...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    # Create directories
    Path("screenshots").mkdir(exist_ok=True)
    Path("recordings").mkdir(exist_ok=True)
    Path("recordings/login_flow").mkdir(parents=True, exist_ok=True)
    
    asyncio.run(record_login_steps())