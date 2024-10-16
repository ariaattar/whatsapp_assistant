from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI
import json
from datetime import datetime, timedelta
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from pytz import timezone
from youtube_transcript_api import YouTubeTranscriptApi
import re
import PyPDF2
from io import BytesIO
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = Flask(__name__)

username = os.environ.get('SMARTPROXY_USERNAME', '')
password = os.environ.get('SMARTPROXY_PASSWORD', '')
proxy = f"http://{username}:{password}@gate.smartproxy.com:10001"

url = 'https://ip.smartproxy.com/json'
result = requests.get(url, proxies={
    'http': proxy,
    'https': proxy
})

account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
twilio_client = Client(account_sid, auth_token)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

openai_client = OpenAI(api_key=OPENAI_API_KEY)


scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
scheduler.start()
conversation_history = []

def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies={
            'http': proxy,
            'https': proxy
        })
        return transcript
    except Exception as e:
        print(f"Error retrieving transcript for video ID {video_id}: {e}")
        return None

def extract_video_id(youtube_url):
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def extract_arxiv_id(arxiv_url):
    arxiv_id_match = re.search(r'arxiv\.org\/(?:abs|pdf)\/([0-9]+\.[0-9]+)', arxiv_url)
    if arxiv_id_match:
        return arxiv_id_match.group(1)
    return None

def download_arxiv_pdf(arxiv_url):
    try:
        response = requests.get(arxiv_url)
        response.raise_for_status()  
        return response.content
    except Exception as e:
        print(f"Error downloading PDF from {arxiv_url}: {e}")
        return None

def extract_text_from_pdf(pdf_content):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def generate_gpt4o_response(user_message):
    global conversation_history

    if user_message.strip().upper() == "RESET":
        conversation_history = []
        return "Conversation history has been reset."
    if "youtube.com" in user_message or "youtu.be" in user_message:
        video_id = extract_video_id(user_message)
        if video_id:
            transcript = get_youtube_transcript(video_id)
            if isinstance(transcript, list):
                transcript_text = " ".join([entry['text'] for entry in transcript])
                user_message = f"Transcript of the video: {transcript_text}"
            else:
                return f"Error retrieving transcript: {transcript}"

    if "arxiv.org" in user_message:
        arxiv_id = extract_arxiv_id(user_message)
        if arxiv_id:
            pdf_content = download_arxiv_pdf(user_message)
            if pdf_content:
                full_text = extract_text_from_pdf(pdf_content)
                if full_text:
                    user_message = f"Full text of the ArXiv paper: {full_text}"
                else:
                    return "Error extracting text from the ArXiv PDF."
            else:
                return "Error downloading the ArXiv PDF."


    try:
        conversation_history.append({"role": "user", "content": user_message})

        california_time = datetime.now(timezone('America/Los_Angeles')).isoformat()
        chicago_time = datetime.now(timezone('America/Chicago')).isoformat()

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
                        Current date and time: California - {california_time}, Chicago - {chicago_time}. Only use the take note function when the user specifically asks you to write something down or remember something. 
                        Use the set_reminder function when the user wants to set a reminder. Otherwise, use a normal response. 
                        your conversations with the user are through text message so respond a way thats appropriate for back and forth texting, 
                        try not to give super long responses unless user user explicitly asks you to explain something in more detail.
                         Also never respond in markdown and use ** or * to bold text.
                        """
                    }
                ]
            }
        ] + conversation_history

        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            temperature=1,
            max_tokens=8000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "take_note",
                        "description": "Create a standardized response for a given event",
                        "parameters": {
                            "type": "object",
                            "required": ["title", "note", "time"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Title of the note"
                                },
                                "note": {
                                    "type": "string",
                                    "description": "Content of the note"
                                },
                                "time": {
                                    "type": "string",
                                    "description": "Timestamp of when the note was made, in ISO 8601 format"
                                }
                            },
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "set_reminder",
                        "description": "Set a reminder for a specific date and time",
                        "parameters": {
                            "type": "object",
                            "required": ["reminder_text", "reminder_time"],
                            "properties": {
                                "reminder_text": {
                                    "type": "string",
                                    "description": "The text of the reminder"
                                },
                                "reminder_time": {
                                    "type": "string",
                                    "description": "The time for the reminder in ISO 8601 format"
                                }
                            },
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            ],
            parallel_tool_calls=True,
            response_format={"type": "text"}
        )

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "take_note":
                
                arguments = json.loads(tool_call.function.arguments)
                note_content = arguments.get('note', '')
                with open('note.txt', 'w') as note_file:
                    note_file.write(note_content)
                assistant_response = "Note saved successfully." + "\n\n" + note_content
            elif tool_call.function.name == "set_reminder":
                arguments = json.loads(tool_call.function.arguments)
                reminder_text = arguments.get('reminder_text', '')
                reminder_time = arguments.get('reminder_time', '')
                set_reminder(reminder_text, reminder_time)
                
                reminder_datetime = datetime.fromisoformat(reminder_time).astimezone(timezone('America/Chicago'))
                formatted_time = reminder_datetime.strftime('%m/%d %I:%M %p CST')
                
                assistant_response = f"Reminder set for {formatted_time}: {reminder_text}"
        else:
            assistant_response = response.choices[0].message.content or "I'm sorry, I couldn't process that request."

        conversation_history.append({"role": "assistant", "content": assistant_response})

        return assistant_response
    except Exception as e:
        print(f"Error generating GPT-4o response: {e}")
        return "I'm sorry, I'm having trouble processing your request right now. Please try again later."

def set_reminder(reminder_text, reminder_time):
    reminder_datetime = datetime.fromisoformat(reminder_time)
    scheduler.add_job(send_reminder, 'date', run_date=reminder_datetime, args=[reminder_text])

def send_text(message):
    max_length = 1400 
    messages = []

    while message:
        if len(message) <= max_length:
            messages.append(message)
            break
        
        split_index = message.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        
        messages.append(message[:split_index])
        message = message[split_index:].lstrip()

    responses = []
    for chunk in messages:
        try:
            response = twilio_client.messages.create(
                from_="whatsapp:+14155238886",
                body=chunk,
                to="whatsapp:+16506464321"
            )
            responses.append({"success": True, "sid": response.sid})
        except Exception as e:
            responses.append({"success": False, "error": str(e)})

    return responses

def send_reminder(reminder_text, phone_number="16506464321"):
    send_text(f"Reminder: {reminder_text}")

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    
    results = send_text(message)
    return jsonify({"results": results}), 200

@app.route('/')
def home():
    return "Welcome to the SMS API!"

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')

    response = generate_gpt4o_response(incoming_msg)

    resp = MessagingResponse()
    resp.message(response)

    return str(resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
