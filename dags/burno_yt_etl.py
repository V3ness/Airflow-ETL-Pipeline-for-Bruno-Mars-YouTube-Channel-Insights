"""
Bruno Mars YouTube ETL Pipeline
"""

from airflow.sdk import dag
from airflow.decorators import task
from pendulum import datetime
import pandas as pd
import logging
import sys
import os

sys.path.insert(0, '/opt/airflow')

from etl.extract import extract_all, get_channel_metadata, get_youtube_client
from etl.transform import transform_video_metadata
from etl.load import load_to_postgres

logger = logging.getLogger(__name__)


@dag(
    dag_id='bruno_mars_etl',
    start_date=datetime(year=2026, month=7, day=1, tz='Asia/Singapore'),
    description='Extract Bruno Mars YouTube data, transform, load to PostgreSQL',
    schedule='@daily',
    catchup=False,
    tags=['youtube', 'bruno_mars', 'etl'],
    max_active_runs=1,
)
def bruno_mars_etl():
    
    @task.python(task_id='extract_youtube_data')
    def extract_data():
        logger.info("Starting extraction...")
        channel_id = "UCoUM-UJ7rirJYP8CQ0EIaHA"
        youtube = get_youtube_client()
        channel_metadata = get_channel_metadata(youtube, channel_id)
        raw_df = extract_all()
        
        return {
            'data': raw_df.to_dict(orient='records'),
            'channel_metadata': channel_metadata
        }
    
    @task.python(task_id='transform_youtube_data')
    def transform_data(raw_data: dict):
        logger.info("Starting transformation...")
        raw_df = pd.DataFrame(raw_data['data'])
        channel_metadata = raw_data['channel_metadata']
        transformed_df = transform_video_metadata(raw_df, channel_metadata)
        return transformed_df.to_dict(orient='records')
    
    @task.python(task_id='load_to_postgres')
    def load_data(transformed_data: dict):
        logger.info("Starting load...")
        df = pd.DataFrame(transformed_data)
        rows_loaded = load_to_postgres(df, table_name='bruno_yt_data', if_exists='replace')
        return rows_loaded
    
    # Task dependencies
    raw_data = extract_data()
    transformed_data = transform_data(raw_data)
    load_data(transformed_data)

bruno_mars_etl()
