# Motor Controller Command Flow Dashboard

Interactive dashboard for analyzing Motor Controller inverter commands from CSV logs with full support for all command types.

## Quick Start

Requirements: Python 3.10 or newer, with the `venv` module available. On some Linux distributions, install it with `sudo apt install python3-venv`.

Clone the repository, enter its directory, and start the dashboard:

```bash
git clone <repository-url>
cd inverter_command
./run_dashboard.sh
```

The launcher creates a local `.venv`, installs the required packages, and starts the dashboard. Open http://localhost:8501 in your browser and upload your CSV file. Run `./run_dashboard.sh` again to start it later; dependencies are checked on each launch.

## Files

- **dashboard.py** - Main Streamlit web application (30+ KB)
- **analyze_command_flow.py** - Command-line analysis tool (10+ KB)
- **run_dashboard.sh** - Launcher script (executable)
- **9thNovember_1019Unit.csv** - Sample test data (188 MB)
- **README.md** - This file

## Features

### Dashboard (Web UI)
- Upload and parse CSV files with Motor Controller commands
- 4 visualization tabs:
  1. **Command Flow** - Timeline of commands with timestamps
  2. **Statistics** - Distribution of command types and speeds
  3. **Target Speeds** - Detailed analysis of all commands with target speeds
  4. **Data Table** - Raw data with filtering and CSV export

### Supported Command Types
- ✅ **Stop** - Stop motor
- ✅ **Agitate** - Agitation with multiple speed entries
- ✅ **ClosedLoopSpin** - Closed-loop spin control
- ✅ **OpenLoop** - Open-loop control with amplitude
- ✅ **OpenLoopAngle** - Open-loop angle control
- ✅ **DryLoadSense** - Dry load sensing
- ✅ **Brake** - Brake command
- ✅ **Coast** - Coast with measurement speeds
- ✅ **ChildSafety** - Child safety lockout
- ✅ **DoNothing** - No-op command

### Parsed Data (varies by command type)
- **TargetSpeed** - Target speed in RPM (±800 range)
- **RampRate** - Speed ramp rate (RPM/sec)
- **Amplitude** - Amplitude percentage (OpenLoop commands)
- **Details** - Command-specific details (entries count, measurement speeds, etc.)

### Real-time Filtering
- Filter by command type (multi-select)
- Filter by time range
- Filter by sequence number range

### Analysis
- Target speed parsing for all applicable commands
- RampRate display
- Command statistics and distribution
- Interactive Plotly charts
- Timeline visualization

### Data Export
- Export filtered results as CSV
- Pagination for large datasets
- Sortable columns

## Command-Line Tool

For batch processing without GUI:
```bash
python3 analyze_command_flow.py <csv_file> [--plot] [--csv=output.csv]
```

Options:
- `--plot` - Generate timeline plot
- `--csv=FILE` - Export parsed commands to CSV

Output includes:
- Command distribution with speed ranges
- Per-command statistics
- Time range summary

## CSV Format

Expected columns (with namespace prefix support):
- `SummitWasherPmsm-diagnostics::Erd_InverterCommand.header.commandId`
- `SummitWasherPmsm-diagnostics::Erd_InverterCommand.header.commandSequenceNumber`
- `SummitWasherPmsm-diagnostics::Erd_InverterCommand.data`
- `Timestamp` (optional)

The parser automatically detects column names with flexible prefix matching.

## Technical Details

### Byte Order
- All InverterCommand data uses **big-endian** byte order
- Parsing uses `struct.unpack('>...')` format

### Command Structures

**ClosedLoopSpin / DryLoadSense:**
- Bytes 0-1: rampRate (uint16_t)
- Bytes 2-3: targetSpeed (int16_t)

**Agitate / OpenLoop:**
- Byte 0: numberOfEntries
- Byte 1: repeatCount (0xFF = repeat indefinitely)
- Bytes 2-3: padding
- Bytes 4+: entries (each 8 bytes)
  - Entry rampRate: bytes 4-5
  - Entry targetSpeed: bytes 6-7
  - Entry onTime: bytes 8-9
  - Entry offTime: bytes 10-11

**OpenLoopAngle:**
- Byte 0: numberOfEntries
- Byte 1: repeatCount (0xFF = repeat indefinitely)
- Bytes 2-3: padding
- Bytes 4+: entries (each 8 bytes)
  - Entry amplitude: bytes 4-5
  - Entry arcLength: bytes 6-7
  - Entry maxStrokeTime: bytes 8-9
  - Entry postPauseTime: bytes 10-11

**Brake:**
- Bytes 0-1: targetSpeed (int16_t)

**Coast:**
- Bytes 0-1: upperCoastMeasurementSpeed (uint16_t)
- Bytes 2-3: lowerCoastMeasurementSpeed (uint16_t)
- Bytes 4-5: targetSpeed (int16_t)

### RPM Range
Maximum target speed: ±800 RPM (test data shows -652 to 651 for Agitate)

## Dependencies

- Python 3.10+
- Packages listed in [requirements.txt](requirements.txt)
- `struct` (Python standard library)

To install the packages manually instead of using the launcher:
```bash
python3 -m pip install -r requirements.txt
```

## Usage Examples

### View all commands in web dashboard
```bash
./run_dashboard.sh
# Upload CSV file and explore 4 visualization tabs
```

### Analyze commands from CLI
```bash
python3 analyze_command_flow.py 9thNovember_1019Unit.csv

# With CSV export
python3 analyze_command_flow.py 9thNovember_1019Unit.csv --csv=output.csv

# With plot
python3 analyze_command_flow.py 9thNovember_1019Unit.csv --plot
```

### Filter and export specific commands
Use the dashboard to filter by command type, time range, and export to CSV

## Example Output

From test data (9thNovember_1019Unit.csv):
```
Command Type            Count Percentage Details
Stop                    35864      23.3%
Agitate                108214      70.2% Speeds: -652 to -652 RPM (avg=-652)
ClosedLoopSpin           7394       4.8% Speeds: -25 to 0 RPM (avg=-25)
OpenLoop                 2662       1.7% Speeds: 10 to 10 RPM (avg=10)

Total: 154,186 commands over ~25 hours
```
