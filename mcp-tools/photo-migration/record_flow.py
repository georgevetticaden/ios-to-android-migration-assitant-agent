#!/usr/bin/env python3.11
"""
Interactive recorder to capture the complete flow and generate selectors
Run this script and manually complete the flow - it will capture everything needed
"""

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

class FlowRecorder:
    def __init__(self):
        self.steps = []
        self.screenshot_dir = "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/logs/flow_recording"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    async def record(self):
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=self.screenshot_dir
        )
        page = await context.new_page()
        
        print("=" * 80)
        print("FLOW RECORDER - INSTRUCTIONS")
        print("=" * 80)
        print("1. The browser will open to privacy.apple.com")
        print("2. Complete the ENTIRE flow manually:")
        print("   - Sign in with Apple ID")
        print("   - Complete 2FA")
        print("   - Navigate to photo transfer")
        print("   - Get to the page showing photo counts")
        print("3. At each major step, press ENTER in this terminal")
        print("4. Type 'done' when you've completed the entire flow")
        print("=" * 80)
        
        # Start recording
        await page.goto("https://privacy.apple.com")
        
        step_num = 1
        while True:
            user_input = input(f"\nStep {step_num} - Press ENTER after completing action (or type 'done' to finish): ")
            
            if user_input.lower() == 'done':
                break
                
            # Capture current state
            step_data = await self.capture_page_state(page, step_num)
            self.steps.append(step_data)
            print(f"✓ Captured step {step_num}: {step_data['title']}")
            step_num += 1
        
        # Save the recording
        output_file = os.path.join(self.screenshot_dir, f"flow_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(self.steps, f, indent=2)
        
        print(f"\n✅ Recording saved to: {output_file}")
        print("\nSummary of captured steps:")
        for i, step in enumerate(self.steps, 1):
            print(f"  {i}. {step['title']} ({step['url']})")
            if step['inputs']:
                print(f"     - Found {len(step['inputs'])} input fields")
            if step['buttons']:
                print(f"     - Found {len(step['buttons'])} buttons")
        
        await browser.close()
        await playwright.stop()
    
    async def capture_page_state(self, page, step_num):
        """Capture all important elements on the current page"""
        
        # Take screenshot
        screenshot_path = os.path.join(self.screenshot_dir, f"step_{step_num}.png")
        await page.screenshot(path=screenshot_path)
        
        # Get page info
        url = page.url
        title = await page.title()
        
        # Find all inputs
        inputs = []
        all_inputs = await page.query_selector_all('input')
        for inp in all_inputs:
            try:
                input_data = {
                    'type': await inp.get_attribute('type'),
                    'id': await inp.get_attribute('id'),
                    'name': await inp.get_attribute('name'),
                    'placeholder': await inp.get_attribute('placeholder'),
                    'aria-label': await inp.get_attribute('aria-label'),
                    'aria-labelledby': await inp.get_attribute('aria-labelledby'),
                    'visible': await inp.is_visible(),
                    'selector': None
                }
                
                # Determine best selector
                if input_data['id']:
                    input_data['selector'] = f"input#{input_data['id']}"
                elif input_data['name']:
                    input_data['selector'] = f"input[name='{input_data['name']}']"
                
                if input_data['visible'] and input_data['selector']:
                    inputs.append(input_data)
            except:
                pass
        
        # Find all buttons
        buttons = []
        all_buttons = await page.query_selector_all('button, input[type="submit"], a.button, [role="button"]')
        for btn in all_buttons:
            try:
                text = await btn.inner_text()
                if text and await btn.is_visible():
                    buttons.append({
                        'text': text.strip(),
                        'selector': f"button:has-text('{text.strip()}')"
                    })
            except:
                pass
        
        # Find text patterns (for photo counts)
        photo_patterns = []
        try:
            # Look for elements containing photo/video counts
            all_elements = await page.query_selector_all('div, span, p, h1, h2, h3, h4, h5, h6')
            for elem in all_elements:
                try:
                    text = await elem.inner_text()
                    if text and ('photo' in text.lower() or 'video' in text.lower()):
                        # Check if it contains numbers
                        import re
                        if re.search(r'\d+[,\d]*\s*(photo|video)', text, re.IGNORECASE):
                            photo_patterns.append(text.strip())
                except:
                    pass
        except:
            pass
        
        # Get page HTML (first 5000 chars for analysis)
        html = await page.content()
        
        return {
            'step': step_num,
            'url': url,
            'title': title,
            'screenshot': screenshot_path,
            'inputs': inputs,
            'buttons': buttons,
            'photo_patterns': photo_patterns,
            'html_sample': html[:5000],
            'timestamp': datetime.now().isoformat()
        }

async def main():
    recorder = FlowRecorder()
    await recorder.record()

if __name__ == "__main__":
    asyncio.run(main())