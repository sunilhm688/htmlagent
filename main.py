from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("Supabase credentials missing! Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment.")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app = FastAPI()

# Define the CrewAI Agent (Frontend webpage generator)
webpage_coder = Agent(
    role="Frontend Webpage Generator",
    goal="Based on the provided prompt, return only the complete and functional HTML and inline CSS to make a static web page. Do not include code explanations or anything else.",
    backstory="You are a helpful coding assistant skilled at generating modern, responsive static websites using HTML and CSS.",
    verbose=True,
    allow_delegation=False
)

def generate_webpage(prompt: str) -> str:
    task = Task(
        description=f"Create a static webpage based on this prompt: '{prompt}'. Output only HTML with embedded CSS or a separate style block. No additional explanations.",
        expected_output="A complete HTML file with embedded CSS for the specified webpage.",
        agent=webpage_coder
    )
    crew = Crew(agents=[webpage_coder], tasks=[task])
    result = crew.kickoff()

    # Extract raw HTML string output from CrewAI response
    return result.raw

class GenerateRequest(BaseModel):
    user_id: str
    prompt: str

@app.post("/generate")
async def generate_site(req: GenerateRequest):
    try:
        # 1. Generate HTML code from prompt
        html_code = generate_webpage(req.prompt)

        # 2. Insert data into Supabase sites table
        insert_data = {
            "user_id": req.user_id,
            "prompt": req.prompt,
            "html": html_code
        }

        response = supabase.table("sites").insert(insert_data).execute()
        # Check insert success (status_code 201 = success creation)
        if response.get("status_code", 201) > 210:
            raise HTTPException(status_code=500, detail="Failed to insert record into database.")

        # 3. Return generated HTML in JSON response
        return {"success": True, "html": html_code}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
