#!/usr/bin/env python3
"""
Motor Controller Command Flow Dashboard
Interactive visualization and analysis of inverter commands
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import struct
import io

# Page config
st.set_page_config(
    page_title="MC Command Flow Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚙️ Motor Controller Command Flow Dashboard")
st.markdown("---")

# Command ID mapping
COMMAND_NAMES = {
    0: "Invalid",
    1: "DoNothing",
    2: "Stop",
    3: "Agitate",
    4: "ClosedLoopSpin",
    5: "OpenLoop",
    6: "DryLoadSense",
    7: "Coast",
    8: "Brake",
    9: "OpenLoopAngle",
    10: "ChildSafety"
}

COMMAND_COLORS = {
    "Invalid": "#808080",
    "DoNothing": "#CCCCCC",
    "Stop": "#FF4444",
    "Agitate": "#4444FF",
    "ClosedLoopSpin": "#44FF44",
    "OpenLoop": "#FFAA00",
    "DryLoadSense": "#FF00AA",
    "Coast": "#00AAFF",
    "Brake": "#FFFF00",
    "OpenLoopAngle": "#FF8800",
    "ChildSafety": "#8800FF"
}


def parse_command_id(cmd_id_str):
    """Convert command ID string to numeric value"""
    if pd.isna(cmd_id_str) or cmd_id_str is None:
        return None
    
    cmd_str = str(cmd_id_str).strip()
    
    # Map enum names to IDs
    name_to_id = {
        "InverterCommandId_Stop": 2,
        "InverterCommandId_Agitate": 3,
        "InverterCommandId_ClosedLoopSpin": 4,
        "InverterCommandId_OpenLoop": 5,
        "InverterCommandId_DryLoadSense": 6,
        "InverterCommandId_Coast": 7,
        "InverterCommandId_Brake": 8,
        "InverterCommandId_OpenLoopAngle": 9,
        "InverterCommandId_ChildSafety": 10,
        "InverterCommandId_DoNothing": 1,
    }
    
    if cmd_str in name_to_id:
        return name_to_id[cmd_str]
    
    try:
        return int(cmd_str)
    except ValueError:
        return None


def extract_target_speed(hex_data, command_id=None, command_name=None, scale_factor=1.0):
    """Extract target speed from hex data for all command types
    
    InverterCommand uses BIG-ENDIAN byte order
    
    Structure varies by command type:
    - ClosedLoopSpin: bytes 0-1=ramp, bytes 2-3=targetSpeed
    - Agitate: header 4 bytes, then entries @ byte 4: ramp(4-5), speed(6-7)
    - DryLoadSense: bytes 0-1=ramp, bytes 2-3=targetSpeed  
    - Brake: bytes 0-1=targetSpeed
    - Coast: bytes 0-1=upperMeas, bytes 2-3=lowerMeas, bytes 4-5=targetSpeed
    - OpenLoop: header 4 bytes, then entries @ byte 4: amplitude(4-5), speed(6-7)
    - OpenLoopAngle: header 4 bytes, then entries @ byte 4: amplitude(4-5), arcLength(6-7)
    """
    if pd.isna(hex_data) or hex_data is None:
        return None
    
    hex_str = str(hex_data).strip()
    if len(hex_str) < 4:
        return None
    
    try:
        if command_name == 'Agitate':
            # First entry's targetSpeed at bytes 6-7
            speed_hex = hex_str[12:16]
        elif command_name == 'OpenLoop':
            # First entry's targetSpeed at bytes 6-7
            speed_hex = hex_str[12:16]
        elif command_name == 'DryLoadSense':
            # targetSpeed at bytes 2-3
            speed_hex = hex_str[4:8]
        elif command_name == 'Brake':
            # targetSpeed at bytes 0-1
            speed_hex = hex_str[0:4]
        elif command_name == 'Coast':
            # targetSpeed at bytes 4-5
            speed_hex = hex_str[8:12]
        else:  # ClosedLoopSpin and others
            # targetSpeed at bytes 2-3
            speed_hex = hex_str[4:8]
        
        speed_bytes = bytes.fromhex(speed_hex)
        speed = struct.unpack('>h', speed_bytes)[0]  # BIG-ENDIAN signed
        
        if scale_factor != 1.0:
            speed = speed / scale_factor
        
        return speed
    except (ValueError, struct.error):
        return None


def extract_ramp_rate(hex_data, command_id=None, command_name=None, scale_factor=1.0):
    """Extract ramp rate from hex data for command types that support it
    
    InverterCommand uses BIG-ENDIAN byte order
    
    Not all commands have ramp rates:
    - ClosedLoopSpin: bytes 0-1
    - Agitate: bytes 4-5 (first entry)
    - DryLoadSense: bytes 0-1
    - OpenLoop: bytes 4-5 (first entry's amplitude)
    - Brake, Coast, OpenLoopAngle: N/A
    """
    if pd.isna(hex_data) or hex_data is None:
        return None
    
    hex_str = str(hex_data).strip()
    if len(hex_str) < 4:
        return None
    
    try:
        if command_name == 'Agitate':
            # First entry's rampRate at bytes 4-5
            ramp_hex = hex_str[8:12]
        elif command_name == 'OpenLoop':
            # First entry's amplitude at bytes 4-5
            ramp_hex = hex_str[8:12]
        elif command_name in ['DryLoadSense', 'ClosedLoopSpin']:
            # rampRate at bytes 0-1
            ramp_hex = hex_str[0:4]
        else:
            return None  # Not applicable for this command
        
        ramp_bytes = bytes.fromhex(ramp_hex)
        ramp = struct.unpack('>H', ramp_bytes)[0]  # BIG-ENDIAN unsigned
        
        if scale_factor != 1.0:
            ramp = ramp / scale_factor
        
        return ramp
    except (ValueError, struct.error):
        return None


def extract_amplitude_percentage(hex_data, command_name=None):
    """Extract amplitude percentage for OpenLoop and OpenLoopAngle commands
    
    OpenLoop structure:
      - Header: 4 bytes
      - Entry 0: amplitude(4-5), targetSpeed(6-7), onTime(8-9), offTime(10-11)
      
    OpenLoopAngle structure:
      - Header: 4 bytes  
      - Entry 0: amplitude(4-5), arcLength(6-7), maxStrokeTime(8-9), postPauseTime(10-11)
    """
    if pd.isna(hex_data) or hex_data is None:
        return None
    
    hex_str = str(hex_data).strip()
    if len(hex_str) < 10:
        return None
    
    try:
        if command_name in ['OpenLoop', 'OpenLoopAngle']:
            # Amplitude at bytes 4-5
            amp_hex = hex_str[8:12]
            amp_bytes = bytes.fromhex(amp_hex)
            amplitude = struct.unpack('>h', amp_bytes)[0]  # BIG-ENDIAN signed
            return amplitude
    except (ValueError, struct.error):
        pass
    
    return None


def extract_measurement_speeds(hex_data, command_name=None):
    """Extract coast measurement speeds
    
    Coast structure:
      - Bytes 0-1: upperCoastMeasurementSpeed
      - Bytes 2-3: lowerCoastMeasurementSpeed
      - Bytes 4-5: targetSpeed
    
    Returns tuple: (upper_speed, lower_speed)
    """
    if command_name != 'Coast' or pd.isna(hex_data):
        return None, None
    
    hex_str = str(hex_data).strip()
    if len(hex_str) < 12:
        return None, None
    
    try:
        upper_hex = hex_str[0:4]
        lower_hex = hex_str[4:8]
        
        upper_bytes = bytes.fromhex(upper_hex)
        lower_bytes = bytes.fromhex(lower_hex)
        
        upper_speed = struct.unpack('>H', upper_bytes)[0]  # BIG-ENDIAN unsigned (Rpm_t)
        lower_speed = struct.unpack('>H', lower_bytes)[0]  # BIG-ENDIAN unsigned (Rpm_t)
        
        return upper_speed, lower_speed
    except (ValueError, struct.error):
        pass
    
    return None, None


def extract_command_details(hex_data, command_name=None):
    """Extract command-specific details as a formatted string"""
    if pd.isna(hex_data) or hex_data is None:
        return None
    
    hex_str = str(hex_data).strip()
    details = []
    
    try:
        if command_name == 'Agitate':
            num_entries = int(hex_str[0:2], 16)
            repeat = int(hex_str[2:4], 16)
            details.append(f"{num_entries} entries")
            if repeat == 255:
                details.append("repeat indefinitely")
            
        elif command_name == 'OpenLoop':
            num_entries = int(hex_str[0:2], 16)
            repeat = int(hex_str[2:4], 16)
            details.append(f"{num_entries} entries")
            if repeat == 255:
                details.append("repeat indefinitely")
                
        elif command_name == 'OpenLoopAngle':
            num_entries = int(hex_str[0:2], 16)
            repeat = int(hex_str[2:4], 16)
            details.append(f"{num_entries} entries")
            if repeat == 255:
                details.append("repeat indefinitely")
                
        elif command_name == 'Coast':
            upper, lower = extract_measurement_speeds(hex_str, command_name)
            if upper and lower:
                details.append(f"upper={upper} RPM")
                details.append(f"lower={lower} RPM")
        
        return "; ".join(details) if details else None
    except (ValueError, struct.error):
        pass
    
    return None


def extract_target_speed_OLD(hex_data, command_id=None, command_name=None, scale_factor=1.0):
    """DEPRECATED: Use extract_target_speed instead"""
    return extract_target_speed(hex_data, command_id, command_name, scale_factor)


def extract_ramp_rate_OLD(hex_data, command_id=None, command_name=None, scale_factor=1.0):
    """DEPRECATED: Use extract_ramp_rate instead"""
    return extract_ramp_rate(hex_data, command_id, command_name, scale_factor)


@st.cache_data
def load_and_parse_csv(uploaded_file):
    """Load CSV and parse command data"""
    df = pd.read_csv(uploaded_file)
    
    # Detect and standardize column names
    # Support original names with prefix, simplified names, and various formats
    cmd_id_col = None
    seq_num_col = None
    hex_data_col = None
    
    # Look for command ID column (case-insensitive, supports prefixes)
    for col in df.columns:
        col_lower = col.lower()
        if 'commandid' in col_lower and 'header' in col_lower:
            cmd_id_col = col
            break
    
    # Look for sequence number column (case-insensitive, supports prefixes)
    for col in df.columns:
        col_lower = col.lower()
        if 'commandsequencenumber' in col_lower and 'header' in col_lower:
            seq_num_col = col
            break
    
    # Look for hex data column (case-insensitive, supports prefixes)
    for col in df.columns:
        col_lower = col.lower()
        if 'erd_invertercommand.data' in col_lower or ('invertercommand' in col_lower and 'data' in col_lower and 'header' not in col_lower):
            hex_data_col = col
            break
    
    # If we found the columns, rename them
    if cmd_id_col:
        df.rename(columns={cmd_id_col: 'CommandId'}, inplace=True)
    else:
        st.error(f"❌ Could not find command ID column. Available columns:\n{', '.join(df.columns[:20])}")
        st.stop()
    
    if seq_num_col:
        df.rename(columns={seq_num_col: 'SequenceNumber'}, inplace=True)
    
    if hex_data_col:
        df.rename(columns={hex_data_col: 'HexData'}, inplace=True)
    
    # Parse command IDs
    df['CommandIdNumeric'] = df['CommandId'].apply(parse_command_id)
    df['CommandName'] = df['CommandIdNumeric'].map(COMMAND_NAMES)
    
    # Parse all command types (if hex data exists)
    if 'HexData' in df.columns:
        # Parse target speeds for all commands that have them
        df['TargetSpeed'] = df.apply(
            lambda row: extract_target_speed(row.get('HexData'), row.get('CommandIdNumeric'), row.get('CommandName')) 
            if row.get('CommandName') in ['ClosedLoopSpin', 'Agitate', 'DryLoadSense', 'Brake', 'Coast', 'OpenLoop'] else None,
            axis=1
        )
        
        # Parse ramp rates for commands that have them
        df['RampRate'] = df.apply(
            lambda row: extract_ramp_rate(row.get('HexData'), row.get('CommandIdNumeric'), row.get('CommandName')) 
            if row.get('CommandName') in ['ClosedLoopSpin', 'Agitate', 'DryLoadSense', 'OpenLoop'] else None,
            axis=1
        )
        
        # Parse amplitude for OpenLoop and OpenLoopAngle
        df['Amplitude'] = df.apply(
            lambda row: extract_amplitude_percentage(row.get('HexData'), row.get('CommandName')) 
            if row.get('CommandName') in ['OpenLoop', 'OpenLoopAngle'] else None,
            axis=1
        )
        
        # Parse command-specific details
        df['Details'] = df.apply(
            lambda row: extract_command_details(row.get('HexData'), row.get('CommandName')),
            axis=1
        )
    else:
        df['TargetSpeed'] = None
        df['RampRate'] = None
        df['Amplitude'] = None
        df['Details'] = None
    
    # Parse timestamp
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    return df


# Sidebar: File upload
st.sidebar.header("📁 Load Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV file",
    type="csv",
    help="Select the inverter command CSV file to analyze"
)

if uploaded_file is None:
    st.info("👈 Upload a CSV file to get started")
    st.stop()

# Load data
with st.spinner("Loading and parsing CSV..."):
    df = load_and_parse_csv(uploaded_file)

# Data info
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Data Summary")
st.sidebar.metric("Total Rows", f"{len(df):,}")
st.sidebar.metric("Commands", f"{len(df[df['CommandName'].notna()]):,}")

if 'Timestamp' in df.columns:
    time_range = pd.to_datetime(df['Timestamp']).max() - pd.to_datetime(df['Timestamp']).min()
    st.sidebar.metric("Duration", f"{time_range.days}d {time_range.seconds//3600}h")

# Filters in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")

# Command type filter
available_commands = sorted(df['CommandName'].dropna().unique())
selected_commands = st.sidebar.multiselect(
    "Command Types",
    options=available_commands,
    default=available_commands,
    help="Filter by command type"
)

# Time range filter
if 'Timestamp' in df.columns:
    time_col = pd.to_datetime(df['Timestamp'])
    min_time = time_col.min().to_pydatetime()  # Convert pandas Timestamp to Python datetime
    max_time = time_col.max().to_pydatetime()  # Convert pandas Timestamp to Python datetime
    
    time_range = st.sidebar.slider(
        "Time Range",
        min_value=min_time,
        max_value=max_time,
        value=(min_time, max_time),
        step=timedelta(minutes=1)
    )
else:
    time_range = None

# Sequence number range
if 'SequenceNumber' in df.columns:
    min_seq = int(df['SequenceNumber'].min()) if df['SequenceNumber'].dtype in ['int64', 'int32'] else 0
    max_seq = int(df['SequenceNumber'].max()) if df['SequenceNumber'].dtype in ['int64', 'int32'] else 255
    
    seq_range = st.sidebar.slider(
        "Sequence Number Range",
        min_value=min_seq,
        max_value=max_seq,
        value=(min_seq, max_seq),
        step=1
    )
else:
    seq_range = None

# Apply filters
filtered_df = df[df['CommandName'].isin(selected_commands)].copy()

if time_range and 'Timestamp' in df.columns:
    time_col = pd.to_datetime(filtered_df['Timestamp'])
    # Convert time_range values to be comparable with pandas datetime
    time_range_min = pd.Timestamp(time_range[0])
    time_range_max = pd.Timestamp(time_range[1])
    filtered_df = filtered_df[(time_col >= time_range_min) & (time_col <= time_range_max)]

if seq_range and 'SequenceNumber' in df.columns:
    filtered_df = filtered_df[
        (filtered_df['SequenceNumber'] >= seq_range[0]) & 
        (filtered_df['SequenceNumber'] <= seq_range[1])
    ]

# Show filter results
st.sidebar.metric("Filtered Commands", f"{len(filtered_df):,}")

# Main content area
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Command Flow",
    "📊 Statistics",
    "🎯 Target Speeds",
    "📋 Data Table"
])

# TAB 1: Command Flow
with tab1:
    st.subheader("Command Flow Over Time")
    
    if 'Timestamp' in filtered_df.columns:
        # Prepare data for plotting
        plot_df = filtered_df[['Timestamp', 'CommandName', 'TargetSpeed']].copy()
        plot_df['Timestamp'] = pd.to_datetime(plot_df['Timestamp'])
        plot_df = plot_df.sort_values('Timestamp')
        
        # Sampling for performance
        sample_size = min(5000, len(plot_df))
        if len(plot_df) > sample_size:
            step = len(plot_df) // sample_size
            plot_df = plot_df.iloc[::step]
        
        # Create figure with Plotly
        fig = go.Figure()
        
        for cmd_name in selected_commands:
            cmd_data = plot_df[plot_df['CommandName'] == cmd_name]
            if len(cmd_data) > 0:
                fig.add_trace(go.Scatter(
                    x=cmd_data['Timestamp'],
                    y=[COMMAND_NAMES.get(COMMAND_NAMES.get(cmd_name, cmd_name), cmd_name)] * len(cmd_data),
                    mode='markers',
                    name=f"{cmd_name} ({len(cmd_data)})",
                    marker=dict(
                        size=6,
                        color=COMMAND_COLORS.get(cmd_name, '#000000'),
                        opacity=0.6
                    ),
                    hovertemplate=f"<b>{cmd_name}</b><br>Time: %{{x}}<br><extra></extra>"
                ))
        
        fig.update_layout(
            title="Command Distribution Over Time",
            xaxis_title="Time",
            yaxis_title="Command Type",
            height=500,
            hovermode='closest',
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No Timestamp column found in CSV")

# TAB 2: Statistics
with tab2:
    st.subheader("Command Statistics")
    
    # Command distribution
    cmd_stats = filtered_df['CommandName'].value_counts().reset_index()
    cmd_stats.columns = ['Command', 'Count']
    cmd_stats['Percentage'] = (cmd_stats['Count'] / cmd_stats['Count'].sum() * 100).round(2)
    cmd_stats = cmd_stats.sort_values('Count', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Table
        st.dataframe(cmd_stats, use_container_width=True, hide_index=True)
    
    with col2:
        # Pie chart
        fig = px.pie(
            cmd_stats,
            values='Count',
            names='Command',
            title="Command Distribution",
            color_discrete_map=COMMAND_COLORS,
            hole=0.3
        )
        fig.update_layout(height=400, template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Target speed statistics (all commands that have target speeds)
    speed_cmds = filtered_df[filtered_df['TargetSpeed'].notna()]
    
    if len(speed_cmds) > 0:
        st.subheader("⚡ Target Speed Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Combined Statistics**")
            speeds = speed_cmds['TargetSpeed'].dropna()
            col1a, col1b, col1c, col1d, col1e = st.columns(5)
            col1a.metric("Count", len(speeds))
            col1b.metric("Min", f"{speeds.min():.0f} RPM")
            col1c.metric("Max", f"{speeds.max():.0f} RPM")
            col1d.metric("Mean", f"{speeds.mean():.1f} RPM")
            col1e.metric("Std Dev", f"{speeds.std():.1f} RPM")
        
        with col2:
            st.markdown("**By Command Type**")
            for cmd_type in speed_cmds['CommandName'].unique():
                if pd.notna(cmd_type):
                    cmd_speeds = speed_cmds[speed_cmds['CommandName'] == cmd_type]['TargetSpeed'].dropna()
                    if len(cmd_speeds) > 0:
                        st.write(f"**{cmd_type}**: {len(cmd_speeds)} commands, "
                               f"Range: {cmd_speeds.min():.0f}..{cmd_speeds.max():.0f} RPM, "
                               f"Mean: {cmd_speeds.mean():.1f} RPM")
        
        # Speed distribution histogram
        fig = px.histogram(
            speed_cmds,
            x='TargetSpeed',
            nbins=50,
            color='CommandName',
            title="Target Speed Distribution (All Commands)",
            labels={'TargetSpeed': 'RPM', 'count': 'Count'},
            barmode='overlay'
        )
        fig.update_layout(height=400, template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)

# TAB 3: Target Speeds Over Time
with tab3:
    st.subheader("Target Speed Timeline")
    
    # Get commands with target speeds
    speed_df = filtered_df[filtered_df['TargetSpeed'].notna()].copy()
    
    if len(speed_df) > 0:
        if 'Timestamp' in speed_df.columns:
            speed_df['Timestamp'] = pd.to_datetime(speed_df['Timestamp'])
            speed_df = speed_df.sort_values('Timestamp')
            
            # Create tabs for different views
            view_tab1, view_tab2, view_tab3 = st.tabs(["Timeline", "Statistics", "Details"])
            
            with view_tab1:
                # Sample for performance
                sample_size = min(2000, len(speed_df))
                if len(speed_df) > sample_size:
                    step = len(speed_df) // sample_size
                    plot_data = speed_df.iloc[::step]
                else:
                    plot_data = speed_df
                
                fig = go.Figure()
                
                # Add traces for each command type with target speed
                for cmd_type in speed_df['CommandName'].unique():
                    if pd.notna(cmd_type):
                        cmd_data = plot_data[plot_data['CommandName'] == cmd_type]
                        if len(cmd_data) > 0:
                            fig.add_trace(go.Scatter(
                                x=cmd_data['Timestamp'],
                                y=cmd_data['TargetSpeed'],
                                mode='lines+markers',
                                name=f'{cmd_type}',
                                marker=dict(size=4),
                                hovertemplate=f'<b>{cmd_type}</b><br>Time: %{{x}}<br>Speed: %{{y}} RPM<extra></extra>'
                            ))
                
                fig.update_layout(
                    title="Target Speed Over Time (All Commands)",
                    xaxis_title="Time",
                    yaxis_title="Target Speed (RPM)",
                    height=500,
                    template='plotly_dark',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with view_tab2:
                # Statistics
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**ClosedLoopSpin Statistics**")
                    spin_speeds = speed_df[speed_df['CommandName'] == 'ClosedLoopSpin']['TargetSpeed'].dropna()
                    if len(spin_speeds) > 0:
                        st.metric("Count", len(spin_speeds))
                        st.metric("Min", f"{spin_speeds.min():.0f} RPM")
                        st.metric("Max", f"{spin_speeds.max():.0f} RPM")
                        st.metric("Mean", f"{spin_speeds.mean():.1f} RPM")
                    else:
                        st.info("No ClosedLoopSpin data")
                
                with col2:
                    st.markdown("**Agitate Statistics**")
                    agitate_speeds = speed_df[speed_df['CommandName'] == 'Agitate']['TargetSpeed'].dropna()
                    if len(agitate_speeds) > 0:
                        st.metric("Count", len(agitate_speeds))
                        st.metric("Min", f"{agitate_speeds.min():.0f} RPM")
                        st.metric("Max", f"{agitate_speeds.max():.0f} RPM")
                        st.metric("Mean", f"{agitate_speeds.mean():.1f} RPM")
                    else:
                        st.info("No Agitate data")
                
                st.markdown("---")
                
                # Speed distribution histogram
                fig = px.histogram(
                    speed_df,
                    x='TargetSpeed',
                    nbins=50,
                    color='CommandName',
                    title="Target Speed Distribution",
                    labels={'TargetSpeed': 'RPM', 'count': 'Count'},
                    barmode='group'
                )
                fig.update_layout(height=400, template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)
            
            with view_tab3:
                # Sequence number vs Speed
                st.markdown("**Speed vs Sequence Number**")
                fig = px.scatter(
                    speed_df,
                    x='SequenceNumber',
                    y='TargetSpeed',
                    color='CommandName',
                    title="Sequence Number vs Target Speed",
                    labels={'SequenceNumber': 'Sequence Number', 'TargetSpeed': 'Target Speed (RPM)'},
                    hover_data=['Timestamp'] if 'Timestamp' in speed_df.columns else []
                )
                fig.update_layout(height=500, template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No Timestamp column found")
    else:
        st.info("No ClosedLoopSpin or Agitate commands with target speeds in filtered data")

# TAB 4: Data Table
with tab4:
    st.subheader("Detailed Command Data")
    
    # Select columns to display
    display_cols = []
    if 'Timestamp' in filtered_df.columns:
        display_cols.append('Timestamp')
    display_cols.extend(['CommandName', 'CommandIdNumeric', 'SequenceNumber'])
    if 'RampRate' in filtered_df.columns:
        display_cols.append('RampRate')
    if 'TargetSpeed' in filtered_df.columns:
        display_cols.append('TargetSpeed')
    if 'Amplitude' in filtered_df.columns:
        display_cols.append('Amplitude')
    if 'Details' in filtered_df.columns:
        display_cols.append('Details')
    
    display_df = filtered_df[display_cols].copy()
    
    # Sorting
    sort_by = st.selectbox(
        "Sort by",
        options=display_cols,
        index=0 if display_cols else None
    )
    
    if sort_by:
        display_df = display_df.sort_values(sort_by, ascending=False)
    
    # Display with pagination
    page_size = st.selectbox("Rows per page", [10, 25, 50, 100, 500])
    
    total_pages = (len(display_df) + page_size - 1) // page_size
    page = st.slider("Page", 1, max(1, total_pages), 1)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    st.dataframe(
        display_df.iloc[start_idx:end_idx],
        use_container_width=True,
        height=600,
        hide_index=True
    )
    
    st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(display_df))} of {len(display_df)} rows")
    
    # Download CSV
    st.markdown("---")
    csv_data = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name=f"command_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("Motor Controller Command Flow Dashboard | Version 1.0")
