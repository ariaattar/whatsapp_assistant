# AI-Powered WhatsApp Assistant

This project is an AI-powered WhatsApp assistant that uses OpenAI's GPT-4 model to provide intelligent responses, set reminders, take notes, and process various types of content including YouTube videos and ArXiv papers.

## Features

- **Reminder Setting**: Set reminders for specific dates and times.
- **Note Taking**: Save notes with titles and timestamps.
- **YouTube Video Processing**: Extract and summarize YouTube video transcripts.
- **ArXiv Paper Processing**: Download and extract text from ArXiv papers for analysis.
- **WhatsApp Integration**: Interact with the AI assistant through WhatsApp.
- **Proxy Support**: Use SmartProxy for accessing YouTube transcripts from VMs.

## Prerequisites

Before you begin, ensure you have met the following requirements:
- Python 3.7+
- Flask
- OpenAI API access
- Twilio account for WhatsApp integration
- SmartProxy account (optional, for proxy support for YouTube transcripts)

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/ariaattar/whatsapp_assistant.git
   cd whatsapp_assistant
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the project root and add the following:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   SMARTPROXY_USERNAME=your_smartproxy_username
   SMARTPROXY_PASSWORD=your_smartproxy_password
   ```

4. Configure Twilio WhatsApp Sandbox:
   - Set up a Twilio account and configure the WhatsApp Sandbox.
   - Set the webhook URL in your Twilio console to point to your server's `/whatsapp` endpoint.

5. Run the application:
   ```
   python main.py
   ```

## Usage

Once set up, users can interact with the AI assistant through WhatsApp by sending messages to the Twilio WhatsApp number. The assistant can:

- Engage in conversations
- Set reminders (e.g., "Remind me to call John tomorrow at 3 PM")
- Take notes (e.g., "Take a note: Remember to buy groceries")
- Process YouTube videos (send a YouTube URL)
- Analyze ArXiv papers (send an ArXiv paper URL)

## Disclaimer

This project is for educational purposes only. Ensure you comply with OpenAI's use-case policy and Twilio's terms of service when using this application.
