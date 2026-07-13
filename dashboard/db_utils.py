"""
Database utility functions for Streamlit dashboard.
Separate from visualization logic for clean separation.
"""

import pandas as pd
import logging
import os
import re
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

# Load env vars once
load_dotenv()

logger = logging.getLogger(__name__)

# Check if running on Streamlit Cloud
IS_STREAMLIT_CLOUD = os.getenv('STREAMLIT_SERVER', '').lower() == 'true'

if IS_STREAMLIT_CLOUD:
    # Use console logging (no files)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
else:
    # Use file logging locally
    PROJECT_ROOT = Path(__file__).parent.parent
    LOG_DIR = PROJECT_ROOT / 'logs'
    LOG_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        filename=LOG_DIR / 'db_utils.log',
        level=logging.INFO,
    )

def get_connection_string() -> str:
    """
    Build PostgreSQL connection string from environment variables.
    
    Returns:
        str: SQLAlchemy connection string
    """
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_LOCAL_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def load_data_from_postgres() -> pd.DataFrame:
    """
    Load YouTube data from PostgreSQL into pandas DataFrame.
    
    Returns:
        pd.DataFrame: Full dataset from bruno_yt_data table
    """
    try:
        connection_string = get_connection_string()
        engine = create_engine(connection_string)
        logger.info(f"Database engine created.")
        
        # SQL Query - select all
        query = "SELECT * FROM bruno_yt_data ORDER BY published_date DESC;"
        
        df = pd.read_sql(query, engine)
        
        # Clean titles
        df = clean_title(df)
        
        logger.info(f"Loaded {len(df)} rows from database")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise
    
def get_latest_extract_date(df: pd.DataFrame) -> str:
    """
    Get the most recent extract_date from the data.
    
    Args:
        df: DataFrame with extract_date column
    
    Returns:
        str: Formatted date string
    """
    if df.empty or 'extract_date' not in df.columns:
        return "No data available"
    
    latest = df['extract_date'].max()
    
    return latest.strftime('%B %d, %Y at %H:%M:%S')

def get_channel_summary(df: pd.DataFrame) -> dict:
    """
    Calculate channel-level metrics from the data.
    
    Returns:
        dict: Total views, subscribers, video count
    """
    if df.empty:
        return {
            'channel_title': 'Unknown',
            'total_views': 0,
            'total_subscribers': 0,
            'video_count': 0
        }
    
    return {
        'channel_title': df['channel_title'].iloc[0],
        'total_views': df['channel_views'].iloc[0],
        'total_subscribers': df['channel_subscribers'].iloc[0],
        'video_count': len(df)
    }

def clean_title(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove the video category string from the title.

    Args:
        df: DataFrame with 'title' and 'vid_category' columns

    Returns:
        DataFrame: With cleaned titles
    """
    df_copy = df.copy()
    
    category_patterns = {
        'Music Video': ['(Official Music Video)', '[Official Music Video]', 'Official Music Video'],
        'Lyric Video': ['(Official Lyric Video)', '[Official Lyric Video]', 'Official Lyric Video'],
        'Audio': ['(Official Audio)', '[Official Audio]', 'Official Audio'],
        'Video': ['(Official Video)', '[Official Video]', 'Official Video'],
        'Live Performance': ['(Official Live Performance)', '[Official Live Performance]', 'Official Live Performance'],
        'Alternative Video': ['(Official Alternative Video)', '[Official Alternative Video]', 'Official Alternative Video'],
        'Documentary Video': ['(Official Documentary Video)', '[Official Documentary Video]', 'Official Documentary Video'],
    }
    
    def remove_pattern(title: str, category: str) -> str:
        if category == 'Other' or pd.isna(title):
            return title
        
        patterns = category_patterns.get(category, [])
        
        cleaned = title
        for pattern in patterns:
            cleaned = cleaned.replace(pattern, '')
            
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' -–—|()[]')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip() if cleaned.strip() else title
    
    df['title_cleaned'] = df.apply(lambda row: remove_pattern(row['title'], row['vid_category']), axis=1)
    
    return df