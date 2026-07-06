import requests
import pandas as pd
import logging
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
import googleapiclient.discovery

# Load env vars once
load_dotenv()

# Instantiate namespace tracking
logger = logging.getLogger(__name__)

API_KEY = os.getenv("YT_API_KEY")
    
def get_youtube_client():
    if not API_KEY:
        raise ValueError("ERROR: API Key not accessed.")
    return googleapiclient.discovery.build('youtube', 'v3', developerKey=API_KEY)
    
def get_channel_metadata(youtube, channel_id: str) -> Dict[str, str | int]:
    """Fetch public channel metadata from YouTube API.

    Args:
        youtube (googleapiclient): YouTube Client
        channel_id (str): A unique ID for a YouTube Channel 

    Endpoint: 
        channels.list (cost: 1 unit)

    Returns:
        Dict: _dict with keys: channel_id, title, published_date, subscribers, views, videos, playlist_id
    """
    try:
        # Create yt response
        response = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        ).execute()
        
        # Validate response
        items = response.get('items', [])
        if not items:
            raise ValueError(f"Channel '{channel_id}' not found or no data returned.")
        
        channel_data = items[0]
        snippet = channel_data.get('snippet', {})
        statistics = channel_data.get('statistics', {})
        playlist = channel_data.get('contentDetails', {}).get('relatedPlaylists', {})
        
        return {
            'channel_id': channel_data.get('id', channel_id),
            'title': snippet.get('title', 'Unknown'),
            'published_date': snippet.get('publishedAt', 'Unknown'),
            'subscribers': int(statistics.get('subscriberCount', 0)),
            'views': int(statistics.get('viewCount', 0)),
            'videos': int(statistics.get('videoCount', 0)),
            'playlist_id': playlist.get('uploads', 'Unknown')
        }

    except Exception as e:
        logger.error(f"Failed to fetch channel metadata for {channel_id}: {str(e)}")
        raise # Re-raise for caller to handle

def get_video_ids_from_channel(youtube, channel_id: str, playlist_id: str, max_results: int = 50) -> List[str]:
    """Fetch list of video IDs from channel's uploads playlist.

    Args:
        youtube (googleapiclient): YouTube Client
        channel_id (str): A unique ID for a YouTube Channel 
        playlist_id (str): A unique ID for a playlist of uploaded videos
        max_results (int, optional): Maximum IDs to retrive. Defaults to 50.

    Endpoint: 
        playlistItems.list (cost: 1 unit per page)
    
    Returns:
        List[str]: list of video ID strings
    """
    video_ids = []
    next_pg_token = None
    
    try:
        while True:
            # Create yt response
            response = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=max_results,
                pageToken=next_pg_token
            ).execute()
            
            for item in response['items']:
                video_ids.append(item.get('contentDetails', {}).get('videoId', 'Unknown'))
            next_pg_token = response.get('nextPageToken')
        
            if not next_pg_token:
                break

        return video_ids
       
    except Exception as e:
        logger.error(f"Failed to fetch video ids for {channel_id}: {str(e)}")
        raise # Re-raise for caller to handle

def get_videos_metadata(youtube, video_ids: List[str]) -> pd.DataFrame:
    """Fetch metadata for each video.

    Args:
        youtube (googleapiclient): YouTube Client
        video_ids (List[str]): 
    
    Endpoint:
        videos.list (cost: 1 unit per 50 videos, max 50 per call)
    
    Returns:
        pd.DataFrame: pandas DataFrame with columns: video_id, title, published_date, views, likes, comments, duration.
    """
    video_data = []
    
    try:
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch_ids)
            ).execute()
            
            for item in response['items']:
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                
                video_data.append({
                    'video_id': item['id'],
                    'title': snippet.get('title', 'Unknown'),
                    'published_date': snippet.get('publishedAt', 'Unknown'),
                    'views': statistics.get('viewCount', 0),
                    'likes': statistics.get('likeCount', 0),
                    'comments': statistics.get('commentCount', 0),
                    'duration': content_details.get('duration', 0)
                })
            
        return pd.DataFrame(video_data)

    except Exception as e:
        logger.error(f"Failed to extract video metadata: {str(e)}")
        raise # Re-raise for caller to handle

def extract_all() -> pd.DataFrame:
    """
    Orchestrate: get channel metadata → get video IDs → get video metadata
    Return: combined DataFrame (add channel_name column for reference)
    """
    channel_id = "UCoUM-UJ7rirJYP8CQ0EIaHA" # Bruno Mars Channel ID
    logging.basicConfig(filename='ETL/extract.log', level=logging.INFO, filemode='w')
    
    logger.info("Extracting data from YouTube API......")
    
    youtube = get_youtube_client()
    logger.info("YouTube API initialized.")
    
    channel_metadata = get_channel_metadata(youtube, channel_id)
    logger.info("Channel Metadata extracted.")
    
    playlist_id = channel_metadata.get('playlist_id', 'Unknown')
    if playlist_id != 'Unknown':
        video_ids = get_video_ids_from_channel(youtube, channel_id, playlist_id, max_results=150)
    logger.info("Video IDs extracted.")
    
    videos_metadata = get_videos_metadata(youtube, video_ids)
    logger.info("Video Metadata extracted.")
    logger.info("Data Extraction Completed.")

    return videos_metadata

if __name__ == "__main__":
    df = extract_all()
    
    # Save raw data
    df.to_csv("data/bruno_mars_raw.csv", index=False)