from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings): 
    # here we have extended the BaseSettings class from pydantic_settings 
    # to create a Settings class that will be used to access the TAVILY_API_KEY 
    # from the .env file.
    TAVILY_API_KEY: str = "your_tavily_api_key"
    GEMINI_API_KEY: str = "your_gemini_api_key"
   