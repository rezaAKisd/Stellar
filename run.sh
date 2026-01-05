#!/bin/bash
# MyHighlights Launcher Script

echo "🚀 Starting MyHighlights..."
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Check dependencies
echo ""
echo "Checking dependencies..."

python -c "import qtpy" 2>/dev/null || { echo "❌ qtpy not found. Run: pip install qtpy pyside6"; exit 1; }
python -c "import qasync" 2>/dev/null || { echo "❌ qasync not found. Run: pip install qasync"; exit 1; }
python -c "import aiograpi" 2>/dev/null || { echo "❌ aiograpi not found. Run: pip install aiograpi"; exit 1; }
python -c "import moviepy" 2>/dev/null || { echo "❌ moviepy not found. Run: pip install moviepy"; exit 1; }

echo "✓ All dependencies installed"
echo ""
echo "Starting application..."
echo ""

# Run the app
python main.py
