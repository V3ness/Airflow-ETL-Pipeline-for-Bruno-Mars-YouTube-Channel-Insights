import pandas as pd
import logging
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env vars once
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(filename='ETL/load.log', level=logging.INFO, filemode='w')

def get_connection_string():
    """
    Build PostgreSQL connection string from environment variables.
    
    Returns:
        str: SQLAlchemy connection string
    """
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def create_table_if_not_exists(engine):
    """
    Create the table with proper schema if it doesn't exist.
    This ensures data types and constraints are correct.
    
    Args:
        engine: SQLAlchemy engine object
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS bruno_yt_data (
        video_id VARCHAR(50) PRIMARY KEY,
        title TEXT,
        published_date TIMESTAMP,
        views INTEGER,
        likes INTEGER,
        comments INTEGER,
        duration_seconds INTEGER,
        vid_category VARCHAR(50),
        channel_title VARCHAR(100),
        channel_subscribers INTEGER,
        channel_views BIGINT,
        extract_date TIMESTAMP
    );
    
    -- Create indexes for faster queries
    CREATE INDEX IF NOT EXISTS idx_published_date ON bruno_yt_data(published_date);
    CREATE INDEX IF NOT EXISTS idx_vid_category ON bruno_yt_data(vid_category);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        logger.info("Table 'bruno_yt_data' created successfully.")
    except Exception as e:
        logger.error(f"Failed to create table: {str(e)}")
        raise

def load_to_postgres(df: pd.DataFrame, table_name: str = 'bruno_yt_data', if_exists: str = 'replace') -> int:
    """
    Load transformed DataFrame to PostgreSQL.
    
    Args:
        df: Transformed DataFrame ready for loading
        table_name: Target table name
        if_exists: 'replace' (drop and recreate) or 'append' (add to existing)
    
    Returns:
        int: Number of rows loaded
    """
    try:
        # Create database engine
        connection_string = get_connection_string()
        engine = create_engine(connection_string)
        logger.info(f"Database engine created. Target: {table_name}")
        
        # Ensure table exists with correct schema
        create_table_if_not_exists(engine)
        
        # Load data to PostgreSQL
        rows_loaded = df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,  # 'replace' drops table and recreates it
            index=False,          # Don't write DataFrame index as a column
            method='multi',       # Insert multiple rows at once (faster)
            chunksize=1000        # Insert 1000 rows per batch
        )
        
        logger.info(f"Successfully loaded {rows_loaded} rows to '{table_name}'.")
        
        # Verify the load with a count query
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            logger.info(f"Verification: {count} rows in '{table_name}'.")
        
        return rows_loaded
        
    except Exception as e:
        logger.error(f"Failed to load data to PostgreSQL: {str(e)}")
        raise
