import os
import requests
import json
import traceback
from features_ext import parse_resume_text

GEMINI_API_KEY = "AIzaSyD7gSGcURKEtd6g8EMCMN2a3XOxhq5V7J8"

def test():
    filepath = r"c:\Users\llegi\OneDrive\Desktop\smarthire_ready_to_deploy\smarthire_deploy\static\uploads\resume_4_Shashank_Pullabhatla_HighRadius.pdf"
    print("Parsing resume...")
    resume_text = parse_resume_text(filepath)
    print(f"Extracted resume text length: {len(resume_text)}")
    print(f"Resume text preview: {resume_text[:200]}")
    
    jd = "Looking for a Python Backend Developer who knows Python, Flask, SQL, and Git."
    print("Building prompt...")
    prompt = (
        f"You are an expert AI recruiter matching a candidate's resume against a job description.\n\n"
        f"--- JOB DESCRIPTION ---\n{jd}\n\n"
        f"--- CANDIDATE RESUME ---\n{resume_text}\n\n"
        f"Compare the resume and job description. You must evaluate the overall match percentage (0 to 100) "
        f"and extract a list of key skills requested in the job description.\n"
        f"For each key skill, determine if it is present in the candidate's resume (matched: true or false) "
        f"and assign a match score (0 to 100) reflecting their proficiency/experience with that skill based on the resume.\n\n"
        f"Return a JSON object with this exact structure:\n"
        f"{{\n"
        f"  \"score\": 85, // overall match score as an integer\n"
        f"  \"verdict\": \"Excellent Match\", // 'Excellent Match' if score >= 75, 'Good Match' if score >= 50, 'Needs Improvement' otherwise\n"
        f"  \"summary\": \"A brief 1-2 sentence description explaining the fit.\",\n"
        f"  \"skills\": [\n"
        f"    {{\n"
        f"      \"name\": \"Python\",\n"
        f"      \"matched\": true,\n"
        f"      \"score\": 90 // score for this skill based on resume relevance\n"
        f"    }},\n"
        f"    ...\n"
        f"  ]\n"
        f"}}\n"
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        print("Calling Gemini API...")
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        print(f"Status Code: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        print("Response received successfully:")
        print(text)
    except Exception as e:
        print("API Call Failed!")
        traceback.print_exc()

if __name__ == "__main__":
    test()
