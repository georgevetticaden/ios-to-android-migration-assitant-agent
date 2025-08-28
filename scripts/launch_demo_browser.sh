#!/bin/bash
#
# Launch Chromium with CDP enabled for demo mode
# This script launches Chromium with remote debugging enabled
# so that the web-automation tools can connect to it
#

echo "============================================================"
echo "           Launching Chromium for Demo Mode"
echo "============================================================"
echo ""

# Kill any existing Chromium with debugging port
echo "🧹 Cleaning up any existing CDP browsers..."
pkill -f "remote-debugging-port=9222" 2>/dev/null

# Wait a moment for cleanup
sleep 1

# Check if Chromium exists
CHROMIUM_PATH="/Applications/Chromium.app/Contents/MacOS/Chromium"
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ -f "$CHROMIUM_PATH" ]; then
    BROWSER_PATH="$CHROMIUM_PATH"
    BROWSER_NAME="Chromium"
elif [ -f "$CHROME_PATH" ]; then
    BROWSER_PATH="$CHROME_PATH"
    BROWSER_NAME="Chrome"
else
    echo "❌ Neither Chromium nor Chrome found!"
    echo "   Please install Chromium from: https://www.chromium.org/"
    exit 1
fi

echo "🚀 Launching $BROWSER_NAME with CDP on port 9222..."
echo ""

# Create a temporary user data directory to ensure fresh instance
TEMP_DIR="/tmp/chrome-demo-$$"
mkdir -p "$TEMP_DIR"

echo "📁 Using temporary profile: $TEMP_DIR"
echo ""

# Launch browser with CDP enabled and new profile
"$BROWSER_PATH" \
    --remote-debugging-port=9222 \
    --user-data-dir="$TEMP_DIR" \
    --no-first-run \
    --disable-default-apps \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --new-window \
    about:blank &

# Wait for browser to start
sleep 2

# Check if CDP is accessible
MAX_ATTEMPTS=10
ATTEMPT=0
CDP_READY=false

echo "⏳ Waiting for CDP to be ready..."
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
        CDP_READY=true
        break
    fi
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
done
echo ""

if [ "$CDP_READY" = true ]; then
    echo "✅ Browser launched successfully!"
    echo "   CDP available at: http://localhost:9222"
    echo ""
    echo "📍 Position the browser window where you want it for your demo"
    echo "   (Bottom right of your 4K recording area)"
    echo ""
    echo "🎬 You're ready to run your demo with:"
    echo "   DEMO_MODE=true python test_mcp_server.py"
    echo ""
    echo "🧹 To stop the demo browser, run:"
    echo "   pkill -f 'remote-debugging-port=9222'"
    echo "   rm -rf $TEMP_DIR"
else
    echo "❌ CDP failed to start after $MAX_ATTEMPTS attempts"
    echo "   Try running the command manually:"
    echo "   $BROWSER_PATH --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-demo"
fi

echo ""
echo "============================================================"