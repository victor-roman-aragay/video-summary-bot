"""
YouTube API handler for getting latest videos and transcripts
"""

import logging
from typing import Optional, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from datetime import datetime
import re


def _parse_iso_duration(duration: str) -> int:
    """
    Parse ISO 8601 duration (e.g. 'PT1M30S') to total seconds.

    Args:
        duration: ISO 8601 duration string from YouTube API

    Returns:
        Duration in seconds
    """
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YouTubeHandler:
    """Handles YouTube API operations"""

    def __init__(self, api_key: str):
        """Initialize YouTube handler with API key"""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.logger = logging.getLogger(__name__)

    def is_shorts(self, video_id: str, max_duration_seconds: int = 60) -> bool:
        """
        Check if a video is a YouTube Short by checking its duration.
        Videos with duration <= max_duration_seconds are considered Shorts.

        Args:
            video_id: YouTube video ID
            max_duration_seconds: Threshold for shorts detection (default: 60)

        Returns:
            True if video is a Short, False otherwise
        """
        try:
            self.logger.info(f"Checking if video {video_id} is a Short")
            request = self.youtube.videos().list(
                part='contentDetails',
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                self.logger.warning(f"No video found with ID: {video_id}")
                return False

            content_details = response['items'][0].get('contentDetails', {})
            duration_str = content_details.get('duration', '')
            duration_seconds = _parse_iso_duration(duration_str)

            is_short = duration_seconds <= max_duration_seconds
            self.logger.info(
                f"Video {video_id} duration: {duration_str} ({duration_seconds}s). "
                f"Is Short: {is_short}"
            )
            return is_short

        except Exception as e:
            self.logger.error(f"Error checking if video is a Short: {e}")
            return False
    
    def get_todays_video(self, channel_id: str) -> Optional[Dict]:
        """
        Get the today's video from a specific channel
        
        Args:
            channel_id: YouTube channel ID (e.g., 'UCxxxxxx') or handle (e.g., '@channelname')
        
        Returns:
            Dict with video info or None if not found
        """
        try:
            self.logger.info(f"Getting latest video from channel: {channel_id}")
            
            # If channel_id starts with @, we need to get the actual channel ID first
            if channel_id.startswith('@'):
                actual_channel_id = self._get_channel_id_from_handle(channel_id)
                if not actual_channel_id:
                    self.logger.error(f"Could not find channel ID for handle: {channel_id}")
                    return None
                channel_id = actual_channel_id
            
            # Search for latest video from the channel
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=1,
                order='date',
                type='video'
            )
            
            response = request.execute()
            
            if not response.get('items'):
                self.logger.warning(f"No videos found for channel: {channel_id}")
                return None
            
            video = response['items'][0]
            today = datetime.now().strftime('%Y-%m-%d')

            if video['snippet']['publishedAt'][:10] == today:  # Replace with today's date in 'YYYY-MM-DD' format
                video_info = {
                    'id': video['id']['videoId'],
                    'title': video['snippet']['title'],
                    'description': video['snippet']['description'],
                    'published_at': video['snippet']['publishedAt'],
                    'channel_title': video['snippet']['channelTitle'],
                    'thumbnail_url': video['snippet']['thumbnails']['medium']['url']
                }
            
                self.logger.info(f"Found video: {video_info['title']}")
                return video_info
            else:
                self.logger.info(f"No video published today for channel: {channel_id}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest video: {e}")
            return None
    
    def _get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """
        Convert @handle to channel ID
        
        Args:
            handle: Channel handle like '@channelname'
        
        Returns:
            Channel ID or None if not found
        """
        try:
            # Remove @ symbol
            username = handle.replace('@', '')
            
            # Try to get channel by username
            request = self.youtube.channels().list(
                part='id',
                forUsername=username
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['id']
            
            # If not found by username, try searching
            search_request = self.youtube.search().list(
                part='snippet',
                q=handle,
                type='channel',
                maxResults=1
            )
            search_response = search_request.execute()
            
            if search_response.get('items'):
                return search_response['items'][0]['snippet']['channelId']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting handle to channel ID: {e}")
            return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """
        Get video information by video ID

        Args:
            video_id: YouTube video ID

        Returns:
            Dict with video info or None if not found
        """
        try:
            self.logger.info(f"Getting video info for: {video_id}")

            request = self.youtube.videos().list(
                part='snippet',
                id=video_id
            )

            response = request.execute()

            if not response.get('items'):
                self.logger.warning(f"No video found with ID: {video_id}")
                return None

            video = response['items'][0]['snippet']
            video_info = {
                'id': video_id,
                'title': video['title'],
                'description': video['description'],
                'published_at': video['publishedAt'],
                'channel_title': video['channelTitle'],
                'thumbnail_url': video['thumbnails']['medium']['url']
            }

            self.logger.info(f"Found video: {video_info['title']}")
            return video_info

        except Exception as e:
            self.logger.error(f"Error getting video info: {e}")
            return None

    def get_transcript(self, video_id: str) -> Optional[str]:
            """
            Get transcript for a specific video in Spanish
            
            Args:
                video_id: YouTube video ID
            
            Returns:
                Full transcript text in Spanish or None if not available
            """
            try:
                self.logger.info(f"Getting Spanish transcript for video: {video_id}")
                
                # Initialize transcript API
                transcript_api = YouTubeTranscriptApi()
                                
            # Try to find Spanish transcript
            # Try direct fetch first (your working method)
                try:
                    transcript = transcript_api.fetch(video_id, languages=['es'])
                    full_text = ' '.join([snippet.text for snippet in transcript])
                    self.logger.info(f"Spanish transcript retrieved: {len(full_text)} characters")
                    return full_text
                except Exception as e:
                    self.logger.warning(f"Direct fetch failed: {e}")
                    
                    # Fallback: try list/find method
                    try:
                        transcript = transcript_api.fetch(video_id, languages=['en'])
                        full_text = ' '.join([snippet.text for snippet in transcript])
                        self.logger.info(f"English transcript retrieved: {len(full_text)} characters")
                        return full_text
                    except Exception as e:
                        self.logger.warning(f"Direct fetch failed: {e}")
                    
                    self.logger.info(f"Spanish transcript retrieved, length: {len(full_text)} characters")
                    return full_text
            
            except Exception as e:
                self.logger.error(f"Error getting transcript: {e}")
                return None
    
    def get_video_info_with_transcript(self, channel_id: str) -> Optional[Dict]:
        """
        Get latest video from channel with its transcript
        
        Args:
            channel_id: YouTube channel ID or handle
        
        Returns:
            Dict with video info and transcript or None if failed
        """
        try:
            # Get latest video
            video_info = self.get_todays_video(channel_id)
            if not video_info:
                return None
            
            # Get transcript
            transcript = self.get_transcript(video_info['id'])
            if not transcript:
                self.logger.warning(f"No transcript available for video: {video_info['title']}")
                return video_info  # Return video info even without transcript
            
            # Add transcript to video info
            video_info['transcript'] = transcript
            return video_info
            
        except Exception as e:
            self.logger.error(f"Error getting video with transcript: {e}")
            return None


if __name__ == "__main__":
    # Test the YouTube handler
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Test with your API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        logger.error("❌ Please set YOUTUBE_API_KEY in .env file")
        exit(1)
    
    # Initialize handler
    yt = YouTubeHandler(api_key)
    
    # Test with a channel (replace with actual channel ID)
    # Supports both channel ID and @handle
    test_channel = "@nacho_ic" 
    
    logger.info(f"Testing with channel: {test_channel}")

    # Test getting today's video
    video = yt.get_todays_video(test_channel)
    if video:
        logger.info(f"✅ Today's video: {video['title']}")
        logger.info(f"📅 Published: {video['published_at']}")
        
        # Test getting transcript
        transcript = yt.get_transcript(video['id'])
        if transcript:
            logger.info(f"✅ Transcript length: {len(transcript)} characters")
            logger.info(f"📝 First 200 chars: {transcript[:200]}...")
        else:
            logger.warning("❌ No transcript available")
    else:
        logger.error("❌ Could not get latest video")