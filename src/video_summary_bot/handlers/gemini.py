"""
Gemini AI handler for generating summaries
"""

import logging
from typing import Optional
import google.generativeai as genai


class GeminiHandler:
    """Handles Gemini AI operations for content summarization"""
    
    def __init__(self, api_key: str):
        """Initialize Gemini handler with API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.logger = logging.getLogger(__name__)
    
    def summarize_video(self, transcript: str, video_title: str, channel_name: str) -> Optional[str]:
        """
        Generate a summary of a video transcript
        
        Args:
            transcript: Full video transcript text
            video_title: Title of the video
            channel_name: Name of the YouTube channel
        
        Returns:
            Summary text or None if failed
        """
        try:
            self.logger.info(f"Generating summary for: {video_title}")
            
            prompt = f"""
            Eres un especialista en crear resúmenes de videos financieros y económicos.
            Resume esta transcripcion de video, destaca los puntos clave y no te dejes nada de información importante.
            Evita introducciones a lo que vas a hacer ni cierres innecesarios. No uses asteriscos.
            {transcript}
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                self.logger.info(f"Summary generated: {len(response.text)} characters")
                return response.text
            else:
                self.logger.error("Empty response from Gemini")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return None

    def get_todays_news(self) -> Optional[str]:
        """
        Generate a summary of a video transcript
        
        Args:
            transcript: Full video transcript text
            video_title: Title of the video
            channel_name: Name of the YouTube channel
        
        Returns:
            Summary text or None if failed
        """
        try:
            self.logger.info(f"Generating news summary")
            
            prompt = f"""
            Hazme un resumen de las noticias económicas y financieras más importantes de hoy a nivel españa e internacional.
            Especificamente de los mercados financieros, bolsa, criptomonedas, tipos de interés, inflación y economía en general.
            Ponme los enlaces de las fuentes de información que utilices para hacer el resumen.
            No te inventes nada, solo utiliza información verificada y de fuentes fiables.
            """
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                self.logger.info(f"Summary generated: {len(response.text)} characters")
                return response.text
            else:
                self.logger.error("Empty response from Gemini")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return None


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Set GEMINI_API_KEY in .env file")
        exit(1)
    
    gemini = GeminiHandler(api_key)
    
    # Test with sample text
    test_transcript = "Hoy hablamos sobre el mercado de valores y las predicciones económicas para 2025..."
    # summary = gemini.summarize_video(test_transcript, "Test Video", "Test Channel")
    news_summary = gemini.get_todays_news()

    if news_summary:
        print("News summary generated:")
        print(news_summary)
    else:
        print("Failed to generate summary")
