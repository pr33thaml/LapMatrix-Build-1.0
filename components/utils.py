import os
import secrets
import string
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import streamlit as st

# Define absolute paths to token.json and credentials.json
TOKEN_PATH = r'C:\Users\Maverick\Downloads\For Asus\Lap_Rec\data\token.json'
CREDENTIALS_PATH = r'C:\Users\Maverick\Downloads\For Asus\Lap_Rec\data\credentials.json'

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Function to authenticate Gmail API
def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the credentials to the absolute path
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    
    return creds


# Function to generate a random password
def generate_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for i in range(length))


# Function to send email using Gmail API
def send_email(to_email, subject, body):
    try:
        # Authenticate the Gmail API
        creds = authenticate()
        service = build('gmail', 'v1', credentials=creds)
        
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        st.success(f"Email sent to {to_email}!")
    except Exception as e:
        st.error(f"Failed to send email: {e}")
