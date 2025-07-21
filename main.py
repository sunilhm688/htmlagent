from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Set up FastAPI app
app = FastAPI()

# Set up Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Set up CrewAI Agent
webpage_coder = Agent(
    role="Frontend Webpage Generator",
    goal="Based on the provided prompt, return only the complete and functional HTML and inline CSS to make a static web page. Do not include code explanations or anything else.",
    backstory="You are a helpful coding assistant skilled at generating modern, responsive static websites using HTML and CSS.",
    verbose=True,
    allow_delegation=False
)

def generate_webpage(prompt):
    task = Task(
        description=f"Create a static webpage based on this prompt: '{prompt}'. Output only HTML with embedded CSS or a separate style block. No additional explanations.",
        expected_output="A complete HTML file with embedded CSS for the specified webpage.",
        agent=webpage_coder
    )
    crew = Crew(agents=[webpage_coder], tasks=[task])
    result = crew.kickoff()
    return result

# Pydantic model for request body
class GenerateRequest(BaseModel):
    user_id: str
    prompt: str

@app.post("/generate")
async def generate_site(req: GenerateRequest):
    try:
        # 1. Generate HTML using CrewAI agent
        html_code = generate_webpage(req.prompt)

        # 2. Insert data into Supabase
        data = {
            "user_id": req.user_id,
            "prompt": req.prompt,
            "html": html_code
        }
        supabase_resp = supabase.table("sites").insert(data).execute()
        if supabase_resp.get("status_code", 201) > 210:
            return HTTPException(status_code=500, detail="Database insert failed!")

        # 3. Return generated HTML
        return {"success": True, "html": html_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
