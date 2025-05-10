from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Sonar API config
SONAR_API_KEY = os.getenv("PERPLEXITY_API_KEY")
SONAR_URL = "https://api.perplexity.ai/chat/completions"

async def get_news_summary(query: str):
    headers = {"Authorization": f"Bearer {SONAR_API_KEY}"}
    payload = {
        "model": "sonar",
        "query": f"Summarize {query} with credible sources, focus on 2025 events",
        "depth": "deep_research"
    }
    response = requests.post(SONAR_URL, json=payload, headers=headers)
    return response.json()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def explain_news(request: Request, query: str = Form(...)):
    result = await get_news_summary(query)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "summary": result.get("answer", "No summary available."),
            "citations": result.get("citations", [])
        }
    )