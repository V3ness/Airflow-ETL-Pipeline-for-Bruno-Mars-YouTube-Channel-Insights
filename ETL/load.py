import pandas as pd
import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, BigInteger, String, DateTime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_connection_string() -> str:
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'youtube_database')
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def load_to_postgres(df: pd.DataFrame, table_name: str = 'bruno_yt_data', if_exists: str = 'replace') -> int:
    try:
        connection_string = get_connection_string()
        engine = create_engine(connection_string)
        logger.info(f"Database engine created. Target: {table_name}")
        
        # Define exact column types
        dtype_mapping = {
            'video_id': String(50),
            'title': String,
            'published_date': DateTime,
            'views': BigInteger,
            'likes': Integer,
            'comments': Integer,
            'duration_seconds': Integer,
            'vid_category': String(50),
            'channel_title': String(100),
            'channel_subscribers': BigInteger,
            'channel_views': BigInteger,
            'extract_date': DateTime,
        }
        
        # Load with correct types
        rows_loaded = df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,  # 'replace' drops and recreates
            index=False,
            dtype=dtype_mapping,  # Forces correct types
            method='multi',
            chunksize=1000
        )
        
        logger.info(f"Successfully loaded {rows_loaded} rows to '{table_name}'.")
        return rows_loaded
        
    except Exception as e:
        logger.error(f"Failed to load data to PostgreSQL: {str(e)}")
        raise