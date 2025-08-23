# Mobile-MCP Setup Guide

This directory contains the mobile-mcp server for controlling Android devices via natural language commands through Claude Desktop.

## Prerequisites

1. **Android Device**
   - USB debugging enabled
   - Connected via USB cable
   - Device unlocked and screen on

2. **Development Tools**
   - Node.js 18+
   - ADB (Android Debug Bridge) installed
   - npm or yarn

## Installation

```bash
# From this directory (mcp-tools/mobile-mcp)
npm install
npm run build
```

## Testing Connection

```bash
# Verify ADB sees your device
adb devices
# Expected output: 
# List of devices attached
# DEVICE_ID    device

# Run tests
npm test
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mobile-mcp": {
      "command": "node",
      "args": [
        "/full/path/to/your/project/mcp-tools/mobile-mcp/lib/index.js",
        "--stdio"
      ],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

Replace `/full/path/to/your/project` with your actual project path.

## Usage Examples

After restarting Claude Desktop, you can use natural language commands:

- "Take a screenshot of the current screen"
- "Open the Play Store"
- "Search for WhatsApp and install it"
- "Open WhatsApp"
- "Create a new group called 'Family'"
- "Navigate to Settings"
- "Enable location sharing in Google Maps"

## Troubleshooting

### Device Not Found
```bash
# Kill and restart ADB
adb kill-server
adb start-server
adb devices
```

### Permission Issues
- Ensure USB debugging is enabled
- Accept any permission prompts on the device
- Try unplugging and reconnecting the USB cable

### Tests Failing
- Some tests may fail if specific apps aren't installed
- The core functionality tests (screenshot, screen size) should pass
- UI element detection tests may vary based on screen content

## Notes for Galaxy Z Fold Devices

The Galaxy Z Fold has dual displays. Mobile-mcp will default to the main display. You may see warnings about multiple displays - this is normal and doesn't affect functionality.

## Original Repository

This is a vendored copy of [mobile-next/mobile-mcp](https://github.com/mobile-next/mobile-mcp) included directly in this project for easier setup and version control.