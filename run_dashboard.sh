#!/bin/bash
# Motor Controller Command Flow Dashboard Launcher

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
	python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo "🚀 Starting Motor Controller Command Flow Dashboard..."
echo ""
echo "📊 Dashboard Features:"
echo "  • Upload CSV files"
echo "  • Interactive command flow visualization"
echo "  • Command statistics and distribution"
echo "  • Target speed analysis"
echo "  • Filterable data table"
echo "  • Download filtered results"
echo ""
echo "🌐 Dashboard will open at: http://localhost:8501"
echo ""
echo "📝 To stop the dashboard: Press Ctrl+C"
echo ""

exec "$VENV_DIR/bin/python" -m streamlit run "$SCRIPT_DIR/dashboard.py"
