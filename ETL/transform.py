import pandas as pd
import numpy as np
from datetime import datetime, UTC
import isodate
import regex
import time
from utils.kafka_utils import (
    create_producer,
    log_transform_started,
    log_transform_completed,
    log_error
)

def clean_published_date(date_str: str) -> str:
    """
    Convert Zulu suffix datetime to Singapore time.

    Args:
        date_str (str): Raw datetime format from YT API

    Returns:
        str: Formatted datetime
    """
    try:
        # Replace Z with +00:00 for proper parsing
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
            
        # Convert to standart UTC datetime
        utc_dt = datetime.fromisoformat(date_str)
        
        return utc_dt.strftime('%Y-%m-%d %H:%M:%S')
        
    except ValueError:
        print(f"Incorrect value for {date_str}.")
        raise
    except TypeError:
        print(f"Incorrect type for {date_str}.")
        raise

def parse_duration(duration_str: str) -> int:
    """
    Convert ISO 8601 duration string to seconds.

    Args:
        duration_str (str): Raw duration format from YT API

    Returns:
        int: Transformed duration in seconds
    """
    try:
        converted_duration = isodate.parse_duration(duration_str)
        total_seconds = int(converted_duration.total_seconds())
        
        return total_seconds

    except ValueError:
        print(f"Incorrect value for {duration_str}.")
        raise
    except TypeError:
        print(f"Incorrect type for {duration_str}.")
        raise

def remove_emojis(text):
    pattern = regex.compile(r'[\p{Emoji}&&\n\p{Emoji_Component}]', regex.V1)
    
    return pattern.sub('', text)

def clean_title(title: str) -> str:
    """
    Clean the title column.

    Args:
        title (str): Raw title string format from YT API

    Returns:
        str: Cleaned and transformed title
    """
    try:
        # Remove whitespace
        cleaned_title = title.strip()
        
        # Remove emojis
        cleaned_title = remove_emojis(cleaned_title)
        
        # Clean using regex
        cleaned_title = cleaned_title.replace("’", "'").replace("–", "-")
        
        return cleaned_title
        
    except ValueError:
        print(f"Incorrect value for {title}.")
        raise
    except TypeError:
        print(f"Incorrect type for {title}.")
        raise

def transform_video_metadata(raw_df: pd.DataFrame, channel_metadata: dict) -> pd.DataFrame:
    """
    Transform the video metadata by cleaning published_date and title, parsing duration,
    handling missing values, adding extract_date, vid_category and channel columns.

    Args:
        raw_df (pd.DataFrame): Before transformed DataFrame
        channel_metadata (dict): The metadata of YT Channel

    Returns:
        pd.DataFrame: Transformed DataFrame
    """
    start_time = time.time()
    producer = create_producer()
    
    try:
        # Start log
        log_transform_started(producer, len(raw_df))
        
        df = raw_df.copy()
        
        # Data transformation
        df['published_date'] = df['published_date'].apply(clean_published_date)
        
        df['duration_seconds'] = df['duration'].apply(parse_duration)
        
        df['title'] = df['title'].apply(clean_title)
        
        # Fill missing values on numeric cols
        df.fillna({'views': 0, 'likes': 0, 'comments': 0}, inplace=True)
        
        # Add extract_date col
        df['extract_date'] = datetime.now(UTC).isoformat()

        
        # Add vid_category col to categorize vid title
        conditions = [
            df['title'].str.contains('Official Lyric Video', case=False, na=False),
            df['title'].str.contains('Official Audio', case=False, na=False),
            df['title'].str.contains('Official Music Video', case=False, na=False),
            df['title'].str.contains('Official Live Performance', case=False, na=False),
            df['title'].str.contains('Official Video', case=False, na=False),
            df['title'].str.contains('Official Alternative Video', case=False, na=False),
            df['title'].str.contains('Official Documentary Video', case=False, na=False),
        ]
        
        categories = ['Lyric Video', 'Audio', 'Music Video', 'Live Performance', 'Video', 'Alternative Video', 'Documentary Video']
        
        df['vid_category'] = np.select(conditions, categories, default='Other')
        
        # Add channel columns from channel_metadata
        df['channel_title'] = channel_metadata['title']
        df['channel_subscribers'] = channel_metadata['subscribers']
        df['channel_views'] = channel_metadata['views']
        
        # Drop rows if duration = 0
        df = df[df['duration'] != 0]
        
        # Log success with category distribution
        duration = time.time() - start_time
        category_counts = df['vid_category'].value_counts().to_dict()
        log_transform_completed(producer, len(df), category_counts, duration)
        
        if producer:
            producer.close()
            
        return df
    
    except Exception as e:
        log_error(producer, str(e), {
            'record_count': len(raw_df) if 'raw_df' in locals() else 0,
            'phase': 'transform'
        })
        if producer:
            producer.close()
        raise
    