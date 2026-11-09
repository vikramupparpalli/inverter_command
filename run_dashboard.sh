#!/bin/bash
# Motor Controller Command Flow Dashboard Launcher

cd /home/vikramupparpalli/inverter_command

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

python3 -m streamlit run dashboard.py
