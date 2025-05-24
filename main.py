import os
from dotenv import load_dotenv
load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    import logging
    logging.warning("PERPLEXITY_API_KEY not found. Using mock responses.")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from fastapi import Request

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define Pydantic models for request and response
class NewsQueryRequest(BaseModel):
    search_query: str

class Citation(BaseModel):
    source_name: str | None = None
    source_url: str | None = None
    snippet: str | None = None

class NewsExplanationResponse(BaseModel):
    summary: str | None = None
    citations: list[Citation] = []
    full_explanation: str | None = None
    related_topics: list[str] = []

app = FastAPI()

# Set up templates directory and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

SONAR_API_URL = "https://api.perplexity.ai/chat/completions"  # Update this if needed

@app.post("/api/v1/explain-news-by-query", response_model=NewsExplanationResponse)
async def explain_news_by_query(request: NewsQueryRequest):
    search_query = request.search_query
    if not search_query:
        raise HTTPException(status_code=400, detail="Invalid search query provided.")

    logger.info(f"Received query: {search_query}")

    # Check if API key is configured
    if not PERPLEXITY_API_KEY:
        logger.warning("API Key not configured. Returning mock response.")
        return _get_mock_response(search_query)

    try:
        # Use openai client with Perplexity settings
        from openai import OpenAI
        client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that explains news and provides cited sources based on the user query."
                )
            },
            {
                "role": "user",
                "content": f"Provide an in-depth analysis of: {search_query}"
            },
        ]
        logger.info(f"Calling Sonar API using OpenAI client for query: {search_query}")
        
        # Synchronous API call (adjust if you require streaming)
        response = client.chat.completions.create(model="sonar-pro", messages=messages)
        logger.info("Successfully received response from Sonar API")
        
        return _parse_sonar_response(response)
    
    except Exception as e:
        import traceback
        logger.error(f"Error processing Sonar API response: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

def _parse_sonar_response(sonar_data):
    """Parse the Sonar API response into our NewsExplanationResponse model"""
    try:
        import re  # Import regex module for cleaning markdown characters
        
        # Convert the response to a dictionary
        sonar_dict = sonar_data.dict() if hasattr(sonar_data, "dict") else sonar_data

        # Extract the main content
        content = ""
        if sonar_dict.get("choices") and len(sonar_dict["choices"]) > 0:
            first_choice = sonar_dict["choices"][0]
            if "message" in first_choice and first_choice["message"]:
                content = first_choice["message"].get("content", "")
                # Clean up the content if needed (e.g., remove <think> tags if present)
                if content.startswith("<think>"):
                    explanation_parts = content.split("</think>", 1)
                    if len(explanation_parts) > 1:
                        content = explanation_parts[1].strip()
                    else:
                        content = content.replace("<think>", "").strip()
        
        # Remove markdown headings at the beginning of lines
        content = re.sub(r"^#{1,6}\s*", "", content, flags=re.MULTILINE)
        # Remove markdown list separators at the beginning of lines
        content = re.sub(r"^-+\s*", "", content, flags=re.MULTILINE)
        # Convert markdown bold formatting to HTML bold tags
        content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
        
        # Extract citations
        citations_list = []
        if sonar_dict.get("citations"):
            for i, url in enumerate(sonar_dict["citations"]):
                try:
                    source_name = url.split("//", 1)[-1].split("/", 1)[0]
                except Exception:
                    source_name = f"Source {i+1}"
                citations_list.append(Citation(
                    source_name=source_name,
                    source_url=url,
                    snippet=f"Reference {i+1}"
                ))
        
        # Create summary (first portion of content) and full explanation
        summary = content[:500] + "..." if len(content) > 500 else content
        
        return NewsExplanationResponse(
            summary=summary,
            citations=citations_list,
            full_explanation=content,
            related_topics=[]
        )
    except Exception as e:
        logger.error(f"Error parsing Sonar API response: {e}")
        raise HTTPException(status_code=500, detail="Error parsing response from news service")

def _get_mock_response(search_query):
    """Return a mock response when API key is not available"""
    logger.info("Generating mock response")
    if "election" in search_query.lower():
        return NewsExplanationResponse(
            summary=f"This is a mock summary about the election query: '{search_query}'.",
            citations=[
                Citation(source_name="Example News Site", source_url="http://example.com/news-election", snippet="An article discussing election results."),
                Citation(source_name="Another Source", source_url="http://anotherexample.org/election-analysis", snippet="Analysis of voter turnout.")
            ],
            full_explanation="A more detailed explanation regarding the election would be provided here by the Sonar API, including various facets and implications.",
            related_topics=["Voter Turnout", "Campaign Finance", "Political Parties"]
        )
    else:
        return NewsExplanationResponse(
            summary=f"This is a mock summary for the query: '{search_query}'.",
            citations=[
                Citation(source_name="General News Source", source_url="http://example.com/general-news", snippet="General news coverage.")
            ],
            full_explanation=f"A detailed explanation for your query '{search_query}' would appear here, generated by the Sonar API."
        )

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    favicon_path = "static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    # Optionally return a blank response or a default image
    return FileResponse("static/style.css", media_type="text/css")

