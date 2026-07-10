"""
Database utility functions for Streamlit dashboard.
Separate from visualization logic for clean separation.
"""

import pandas as pd
import logging
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env vars once
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(filename='dashboard/logs/db_utils.log')

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
