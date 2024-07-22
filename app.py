import streamlit as st
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import json
from datetime import datetime, timedelta
import re
import requests
from PIL import Image
from io import BytesIO
from streamlit_card import card

# Set up Gemini API
os.environ['GOOGLE_API_KEY'] = 'AIzaSyD5SNn_C2wv1mwdjXxOz09IiJg6yiIeQig'
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# # Set up Google Calendar API
# SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRET_FILE = 'path_to_your_client_secret_file.json'

@st.cache_resource
def load_gemini_model():
    return genai.GenerativeModel('gemini-pro')

model = load_gemini_model()

# def get_calendar_service():
#     creds = None
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
#             auth_url, _ = flow.authorization_url(prompt='consent')
#             st.write(f"Please visit this URL to authorize the application: {auth_url}")
#             auth_code = st.text_input("Enter the authorization code:")
#             flow.fetch_token(code=auth_code)
#             creds = flow.credentials
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
    
#     return build('calendar', 'v3', credentials=creds)

def parse_duration(duration_str):
    match = re.search(r'\d+', duration_str)
    if match:
        return int(match.group())
    return 60

def get_gemini_recommendations(subject, level, days_left):
    prompt = f"""
    Suggest 3 study resources for a student with the following criteria:
    - Subject: {subject}
    - Preparation level: {level}
    - Days left until exam: {days_left}

    Consider the time constraint and preparation level. 
    If time is short, prioritize quick review materials. For longer time frames, suggest more comprehensive resources.

    Use the following JSON format:
    [
        {{
            "title": "Resource Title",
            "type": "Resource Type (e.g., video, course, article)",
            "duration": "Estimated study time in minutes (just the number)",
            "url": "URL of the resource",
            "image_url": "URL of an image representing the resource"
        }},
        {{
            // Second recommendation
        }},
        {{
            // Third recommendation
        }}
    ]
    """

    response = model.generate_content(prompt)
    
    try:
        recommendations = json.loads(response.text)
        for rec in recommendations:
            rec['duration'] = parse_duration(str(rec['duration']))
        return recommendations
    except json.JSONDecodeError:
        st.error("Failed to parse AI response. Please try again.")
        return []

def generate_study_schedule(subjects, levels, exam_dates):
    schedule = []
    start_date = datetime.now().date()

    for subject, level, exam_date in zip(subjects, levels, exam_dates):
        days_until_exam = (exam_date - start_date).days
        recommendations = get_gemini_recommendations(subject, level, days_until_exam)
        for rec in recommendations:
            schedule.append({
                'subject': subject,
                'title': rec['title'],
                'duration': rec['duration'],
                'url': rec['url'],
                'image_url': rec['image_url'],
                'type': rec['type']
            })

    return schedule

def get_image_from_url(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def main():
    st.title("AI-Powered Study Planner")

    # User input
    num_subjects = st.number_input("Number of subjects", min_value=1, max_value=10, value=3)
    subjects = []
    levels = []
    exam_dates = []
    for i in range(num_subjects):
        col1, col2, col3 = st.columns(3)
        with col1:
            subject = st.text_input(f"Subject {i+1}")
            subjects.append(subject)
        with col2:
            level = st.selectbox(f"Preparation level for {subject}", ["bad", "good", "great"], key=f"level_{i}")
            levels.append(level)
        with col3:
            exam_date = st.date_input(f"Exam date for {subject}", key=f"exam_date_{i}")
            exam_dates.append(exam_date)

    if st.button("Generate Study Schedule"):
        if all(subjects) and all(exam_date > datetime.now().date() for exam_date in exam_dates):
            with st.spinner("Generating study schedule..."):
                schedule = generate_study_schedule(subjects, levels, exam_dates)
                
                # Display schedule
                st.subheader("Your Study Schedule")
                
                # Create a 3-column layout
                cols = st.columns(3)
                
                for index, item in enumerate(schedule):
                    with cols[index % 3]:
                        # Determine icon based on resource type
                        icon = "📺" if item['type'].lower() == 'video' else "📄" if item['type'].lower() == 'article' else "🎓"
                        
                        # Create a card for each resource
                        card(
                            title=f"{icon} {item['title']}",
                            text=f"{item['duration']} minutes | {item['type']}",
                            image=item['image_url'],
                            url=item['url'],
                            styles={
                                "card": {
                                    "width": "100%",
                                    "height": "100%",
                                    "border-radius": "10px",
                                    "box-shadow": "0 0 10px rgba(0,0,0,0.1)",
                                },
                                "filter": {
                                    "background-color": "rgba(0,0,0,0.2)",
                                }
                            },
                            key=f"card_{index}"
                        )
                        
                        # Add an expander for more details
                        with st.expander("More Info"):
                            st.write(f"Subject: {item['subject']}")
                            st.write(f"Duration: {item['duration']} minutes")
                            st.write(f"Type: {item['type']}")
                            st.write(f"URL: {item['url']}")
        else:
            st.error("Please fill in all subjects and select future exam dates.")

if __name__ == "__main__":
    main()