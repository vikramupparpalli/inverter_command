#!/usr/bin/env python3
"""
Analyze Motor Controller Command Flow

Outputs:
  - Command distribution with target speeds
  - Timeline in CSV format
  - Optional: Plot (matplotlib)
"""

import csv
import sys
from datetime import datetime
import struct
from collections import defaultdict, Counter


def parse_command_id(cmd_id_str):
    """Parse command ID from enum string or numeric value"""
    if not cmd_id_str:
        return None
    try:
        return int(cmd_id_str)
    except:
        name_to_id = {
            'Stop': 2, 'Agitate': 3, 'ClosedLoopSpin': 4, 'OpenLoop': 5,
            'DryLoadSense': 6, 'Coast': 7, 'Brake': 8, 'OpenLoopAngle': 9,
            'ChildSafety': 10, 'DoNothing': 1,
        }
        for name, id_val in name_to_id.items():
            if name in cmd_id_str:
                return id_val
    return None


def extract_target_speed(hex_data, cmd_id, cmd_name=None):
    """Extract target speed from command hex data (all command types)
    
    Uses BIG-ENDIAN byte order
    """
    if not hex_data or cmd_id is None:
        return None
    
    hex_str = hex_data.strip().replace(' ', '')
    if len(hex_str) < 4:
        return None
    
    try:
        # Map by command ID or name
        if cmd_id == 4 or cmd_name == 'ClosedLoopSpin':
            # ClosedLoopSpin: bytes 2-3
            speed_hex = hex_str[4:8]
        elif cmd_id == 3 or cmd_name == 'Agitate':
            # Agitate: first entry at bytes 4+, speed at 6-7
            speed_hex = hex_str[12:16]
        elif cmd_id == 6 or cmd_name == 'DryLoadSense':
            # DryLoadSense: bytes 2-3
            speed_hex = hex_str[4:8]
        elif cmd_id == 8 or cmd_name == 'Brake':
            # Brake: bytes 0-1
            speed_hex = hex_str[0:4]
        elif cmd_id == 7 or cmd_name == 'Coast':
            # Coast: bytes 4-5
            speed_hex = hex_str[8:12]
        elif cmd_id == 5 or cmd_name == 'OpenLoop':
            # OpenLoop: first entry at bytes 4+, speed at 6-7
            speed_hex = hex_str[12:16]
        else:
            return None
        
        target_speed_bytes = bytes.fromhex(speed_hex)
        return struct.unpack('>h', target_speed_bytes)[0]  # BIG-ENDIAN
    except:
        return None


def extract_ramp_rate(hex_data, cmd_id, cmd_name=None):
    """Extract ramp rate from command hex data (all command types)
    
    Uses BIG-ENDIAN byte order
    """
    if not hex_data or cmd_id is None:
        return None
    
    hex_str = hex_data.strip().replace(' ', '')
    if len(hex_str) < 4:
        return None
    
    try:
        if cmd_id == 4 or cmd_name == 'ClosedLoopSpin':
            # ClosedLoopSpin: bytes 0-1
            ramp_hex = hex_str[0:4]
        elif cmd_id == 3 or cmd_name == 'Agitate':
            # Agitate: first entry at bytes 4+, ramp at 4-5
            ramp_hex = hex_str[8:12]
        elif cmd_id == 6 or cmd_name == 'DryLoadSense':
            # DryLoadSense: bytes 0-1
            ramp_hex = hex_str[0:4]
        elif cmd_id == 5 or cmd_name == 'OpenLoop':
            # OpenLoop: first entry at bytes 4+, amplitude at 4-5
            ramp_hex = hex_str[8:12]
        else:
            return None
        
        ramp_bytes = bytes.fromhex(ramp_hex)
        return struct.unpack('>H', ramp_bytes)[0]  # BIG-ENDIAN unsigned
    except:
        return None


def analyze_command_flow(csv_file, output_csv=None, plot=False):
    """Analyze command flow and optionally plot"""
    
    print(f"Analyzing: {csv_file}\n")
    
    # Parse CSV
    timestamps = []
    cmd_ids = []
    seq_nums = []
    speeds = []
    
    cmd_names = {
        0: 'Invalid', 1: 'DoNothing', 2: 'Stop', 3: 'Agitate', 4: 'ClosedLoopSpin',
        5: 'OpenLoop', 6: 'DryLoadSense', 7: 'Coast', 8: 'Brake', 9: 'OpenLoopAngle',
        10: 'ChildSafety',
    }
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            # Find columns
            ts_col = [n for n in reader.fieldnames if 'Timestamp' in n][0]
            id_col = [n for n in reader.fieldnames if 'commandId' in n and 'header' in n][0]
            seq_col = [n for n in reader.fieldnames if 'commandSequenceNumber' in n and 'header' in n][0]
            hex_col = [n for n in reader.fieldnames if 'InverterCommand.data' in n][0]
            
            print(f"Parsing: {csv_file}")
            count = 0
            for row in reader:
                ts_str = (row.get(ts_col) or "").strip()
                id_str = (row.get(id_col) or "").strip()
                seq_str = (row.get(seq_col) or "").strip()
                hex_str = (row.get(hex_col) or "").strip()
                
                if not all([ts_str, id_str, seq_str]):
                    continue
                
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    cmd_id = parse_command_id(id_str)
                    if cmd_id is None:
                        continue
                    seq = int(seq_str)
                    cmd_name = cmd_names.get(cmd_id)
                    speed = extract_target_speed(hex_str, cmd_id, cmd_name)
                    
                    timestamps.append(ts)
                    cmd_ids.append(cmd_id)
                    seq_nums.append(seq)
                    speeds.append(speed)
                    
                    count += 1
                    if count % 50000 == 0:
                        print(f"  Parsed {count:6d} commands...")
                except:
                    pass
    
    except FileNotFoundError:
        print(f"Error: File not found: {csv_file}")
        return
    
    if not timestamps:
        print("No commands found")
        return
    
    print(f"\n✓ Parsed {len(timestamps)} commands\n")
    
    # Analyze
    print("=" * 80)
    print("COMMAND FLOW ANALYSIS")
    print("=" * 80)
    
    id_counts = Counter(cmd_ids)
    print(f"\n{'Command Type':<20} {'Count':>8} {'Percentage':>10} {'Details':<40}")
    print("-" * 80)
    
    for cmd_id in sorted(id_counts.keys()):
        count = id_counts[cmd_id]
        pct = 100 * count / len(cmd_ids)
        name = cmd_names.get(cmd_id, f'Unknown({cmd_id})')
        
        # Get speeds for this type
        speeds_for_id = [s for c, s in zip(cmd_ids, speeds) if c == cmd_id and s is not None]
        
        if speeds_for_id:
            min_speed = min(speeds_for_id)
            max_speed = max(speeds_for_id)
            avg_speed = sum(speeds_for_id) // len(speeds_for_id)
            details = f"Speeds: {min_speed} to {max_speed} RPM (avg={avg_speed})"
        else:
            details = ""
        
        print(f"{name:<20} {count:>8} {pct:>9.1f}% {details:<40}")
    
    print("-" * 80)
    print(f"\nTime range: {timestamps[0]} to {timestamps[-1]}")
    
    # Save CSV if requested
    if output_csv:
        print(f"\nExporting to: {output_csv}")
        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'CommandId', 'CommandName', 'SequenceNumber', 'TargetSpeed(RPM)'])
            
            for ts, cmd_id, seq, speed in zip(timestamps, cmd_ids, seq_nums, speeds):
                cmd_name = cmd_names.get(cmd_id, f'Unknown({cmd_id})')
                speed_str = str(speed) if speed is not None else ""
                writer.writerow([ts.isoformat(), cmd_id, cmd_name, seq, speed_str])
        
        print(f"✓ CSV exported with {len(timestamps)} commands")
    
    # Plot if requested
    if plot:
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.patches import Patch
            
            print("\nGenerating plot...")
            
            color_map = {
                0: '#888888', 1: '#AAAAAA', 2: '#FF0000', 3: '#0000FF', 4: '#00AA00',
                5: '#AA00AA', 6: '#FF69B4', 7: '#FFA500', 8: '#8B4513', 9: '#00FFFF',
                10: '#FF00FF',
            }
            
            fig, ax = plt.subplots(figsize=(18, 8))
            
            # Plot with sampling for performance
            sample_rate = max(1, len(timestamps) // 5000)  # Target ~5000 points
            
            for i, (ts, cmd_id, seq, speed) in enumerate(zip(timestamps, cmd_ids, seq_nums, speeds)):
                if i % sample_rate != 0:
                    continue
                
                color = color_map.get(cmd_id, '#000000')
                
                if speed is not None:
                    marker = 'o'
                    size = 120
                else:
                    marker = 's'
                    size = 80
                
                ax.scatter(ts, cmd_id, c=color, marker=marker, s=size, alpha=0.6, 
                          edgecolors='black', linewidth=0.5)
            
            # Format
            ax.set_xlabel('Time', fontsize=12, fontweight='bold')
            ax.set_ylabel('Command ID', fontsize=12, fontweight='bold')
            ax.set_title('Motor Controller Command Flow - CommandID with Target Speed', fontsize=14, fontweight='bold')
            
            ax.set_ylim(-0.5, 10.5)
            ax.set_yticks(range(11))
            
            # X-axis format
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
            plt.xticks(rotation=45, ha='right')
            
            # Grid
            ax.grid(True, alpha=0.2, axis='y')
            for i in range(11):
                ax.axhline(y=i, color='lightgray', linestyle=':', alpha=0.2, linewidth=0.5)
            
            # Legend
            legend_elements = []
            for cmd_id in sorted(id_counts.keys()):
                count = id_counts[cmd_id]
                color = color_map.get(cmd_id, '#000000')
                name = cmd_names.get(cmd_id, f'Unknown({cmd_id})')
                legend_elements.append(Patch(facecolor=color, label=f'{name} ({count})'))
            
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            
            plt.tight_layout()
            plt.savefig('command_flow.png', dpi=150, bbox_inches='tight')
            print(f"✓ Plot saved to: command_flow.png")
            
        except ImportError:
            print("Error: matplotlib not installed. Install with: pip install matplotlib")
        except Exception as e:
            print(f"Error generating plot: {e}")


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "/home/vikramupparpalli/inverter_command/9thNovember_1019Unit.csv"
    
    # Check for --plot flag
    do_plot = '--plot' in sys.argv
    
    # Check for --csv flag
    output_csv = None
    for arg in sys.argv:
        if arg.startswith('--csv='):
            output_csv = arg.split('=', 1)[1]
    
    analyze_command_flow(csv_file, output_csv=output_csv, plot=do_plot)
