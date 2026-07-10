"""
Bruno Mars YouTube Channel Dashboard
Streamlit dashboard with 4 charts in 2x2 layout.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import database utilities
from db_utils import load_data_from_postgres, get_latest_extract_date, get_channel_summary

# ============================================
# CONFIGURATION
# ============================================

# Color theme
COLORS = {
    'main': '#133a9f',      # Dark blue
    'secondary': '#00a0ca', # Cyan
    'contrast': '#45eb2f',  # Bright green
    'background': '#f5f7fa' # Light gray for background
}

# Page configuration
st.set_page_config(
    page_title="Bruno Mars YT Channel Analysis",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# PART 1: LOAD DATA (Cached for performance)
# ============================================

@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_data():
    """
    Load data with caching to avoid hitting database on every refresh.
    Streamlit's @st.cache_data keeps data in memory between reruns.
    """
    df = load_data_from_postgres()
    return df

# Load the data
df = load_data()

# ============================================
# PART 2: HEADER SECTION
# ============================================

st.markdown(f"""
    <div style="background-color: {COLORS['main']}; padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center; font-size: 2.5rem;">
            Bruno Mars YT Channel Analysis
        </h1>
        <div style="display: flex; justify-content: space-around; margin-top: 1rem;">
            <div style="text-align: center;">
                <p style="color: white; margin: 0; font-size: 0.9rem;">Total Views</p>
                <p style="color: {COLORS['contrast']}; margin: 0; font-size: 1.8rem; font-weight: bold;">
                    {get_channel_summary(df)['total_views']:,.0f}
                </p>
            </div>
            <div style="text-align: center;">
                <p style="color: white; margin: 0; font-size: 0.9rem;">Subscribers</p>
                <p style="color: {COLORS['contrast']}; margin: 0; font-size: 1.8rem; font-weight: bold;">
                    {get_channel_summary(df)['total_subscribers']:,.0f}
                </p>
            </div>
            <div style="text-align: center;">
                <p style="color: white; margin: 0; font-size: 0.9rem;">Total Videos</p>
                <p style="color: {COLORS['contrast']}; margin: 0; font-size: 1.8rem; font-weight: bold;">
                    {get_channel_summary(df)['video_count']}
                </p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Top right corner: Extracted date
extract_date = get_latest_extract_date(df)
st.markdown(f"""
    <div style="text-align: right; color: #666; font-size: 0.85rem; margin-top: -1.5rem; margin-bottom: 1.5rem;">
        📊 Data extracted: {extract_date}
    </div>
""", unsafe_allow_html=True)

# ============================================
# PART 3: SIDEBAR / FILTERS
# ============================================

with st.sidebar:
    st.markdown(f"### Filter by Category")
    
    # Get unique categories for filter
    categories = ['All'] + sorted(df['vid_category'].unique().tolist())
    
    selected_category = st.selectbox(
        "Select Video Category:",
        options=categories,
        index=0
    )
    
    st.markdown("---")
    st.caption(f"Total Videos: {len(df)}")
    st.caption(f"Categories: {len(df['vid_category'].unique())}")

# Apply filter to data
if selected_category != 'All':
    filtered_df = df[df['vid_category'] == selected_category]
else:
    filtered_df = df

# ============================================
# PART 4: CHARTS (2x2 Layout)
# ============================================

# Create 2x2 grid using columns
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

# --------------------------------------------
# Panel 1: Bar Chart - Views by Video Title
# --------------------------------------------

with row1_col1:
    st.markdown(f"### Views by Video")
    st.caption(f"Grouped by: {selected_category if selected_category != 'All' else 'All Categories'}")
    
    # Prepare data - top 15 videos for readability
    bar_df = filtered_df.nlargest(15, 'views').sort_values('views', ascending=True)
    
    # Create bar chart
    fig_bar = px.bar(
        bar_df,
        x='views',
        y='title',
        orientation='h',
        color='vid_category',
        color_discrete_sequence=[COLORS['main'], COLORS['secondary'], COLORS['contrast']],
        title=None,
        labels={'views': 'Views', 'title': 'Video Title'},
        hover_data={'views': ':,.0f'}
    )
    
    fig_bar.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5)
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)

# --------------------------------------------
# Panel 2: Pie Chart - Distribution by Category
# --------------------------------------------

with row1_col2:
    st.markdown(f"### Views Distribution by Category")
    
    # Aggregate views by category
    pie_df = filtered_df.groupby('vid_category')['views'].sum().reset_index()
    
    # Create pie chart
    fig_pie = px.pie(
        pie_df,
        values='views',
        names='vid_category',
        color_discrete_sequence=[COLORS['main'], COLORS['secondary'], COLORS['contrast'], '#ff6b6b', '#ffd93d'],
        title=None,
        hover_data={'views': ':,.0f'},
        hole=0.3  # Donut chart style
    )
    
    fig_pie.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

# --------------------------------------------
# Panel 3: Table - Video Data Table
# --------------------------------------------

with row2_col1:
    st.markdown(f"### Video Details Table")
    st.caption(f"Category: {selected_category if selected_category != 'All' else 'All Categories'}")
    
    # Select and format columns for display
    table_df = filtered_df[[
        'title', 
        'vid_category', 
        'views', 
        'likes', 
        'comments', 
        'duration_seconds'
    ]].copy()
    
    # Format duration from seconds to MM:SS
    table_df['duration'] = table_df['duration_seconds'].apply(
        lambda x: f"{int(x//60)}:{int(x%60):02d}" if x else "N/A"
    )
    
    # Format numbers with commas
    table_df['views'] = table_df['views'].apply(lambda x: f"{x:,.0f}")
    table_df['likes'] = table_df['likes'].apply(lambda x: f"{x:,.0f}")
    table_df['comments'] = table_df['comments'].apply(lambda x: f"{x:,.0f}")
    
    # Drop duration_seconds (replaced by formatted duration)
    table_df = table_df.drop('duration_seconds', axis=1)
    
    # Rename columns for display
    table_df.columns = ['Video Title', 'Category', 'Views', 'Likes', 'Comments', 'Duration']
    
    # Display table with scroll
    st.dataframe(
        table_df,
        height=300,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Video Title": st.column_config.TextColumn("Video Title", width="large"),
            "Views": st.column_config.TextColumn("Views", width="small"),
            "Likes": st.column_config.TextColumn("Likes", width="small"),
            "Comments": st.column_config.TextColumn("Comments", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
        }
    )

# --------------------------------------------
# Panel 4: Line Chart - Timeline of Publications
# --------------------------------------------

with row2_col2:
    st.markdown(f"### Publication Timeline")
    st.caption("Video uploads over time")
    
    # Prepare time series data
    # Count videos per day
    df_time = filtered_df.copy()
    df_time['published_date'] = pd.to_datetime(df_time['published_date'])
    df_time['date'] = df_time['published_date'].dt.date
    
    # Count videos per date
    timeline_df = df_time.groupby('date').size().reset_index(name='video_count')
    
    # Also add cumulative view count over time (alternative insight)
    views_timeline = df_time.groupby('date')['views'].sum().reset_index(name='daily_views')
    
    # Merge for line chart with dual axis or separate line
    fig_line = go.Figure()
    
    # Add video count line
    fig_line.add_trace(go.Scatter(
        x=timeline_df['date'],
        y=timeline_df['video_count'],
        name='Videos Uploaded',
        line=dict(color=COLORS['main'], width=2),
        mode='lines+markers',
        marker=dict(size=6)
    ))
    
    # Add cumulative views (secondary axis)
    fig_line.add_trace(go.Scatter(
        x=views_timeline['date'],
        y=views_timeline['daily_views'].cumsum(),
        name='Cumulative Views',
        line=dict(color=COLORS['secondary'], width=2, dash='dash'),
        mode='lines',
        yaxis='y2'
    ))
    
    fig_line.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5),
        xaxis=dict(title='Date', tickformat='%b %Y'),
        yaxis=dict(title='# Videos', side='left'),
        yaxis2=dict(
            title='Cumulative Views',
            side='right',
            overlaying='y',
            showgrid=False,
            tickformat=',.0f'
        )
    )
    
    st.plotly_chart(fig_line, use_container_width=True)

# ============================================
# PART 5: FOOTER
# ============================================

st.markdown("---")
st.caption(f"Data source: YouTube API | Dashboard built with Streamlit | {datetime.now().strftime('%B %d, %Y')}")