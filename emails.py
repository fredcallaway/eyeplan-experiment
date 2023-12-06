from datetime import datetime
import re
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText

from fire import Fire

# If modifying these SCOPES, delete the file token.json.
SCOPES = [f'https://www.googleapis.com/auth/gmail.{f}' for f in ('send', 'modify')]
BODY = """
Hi {name},

This is just a quick reminder about the study today ({date}) at {time}. Please
arrive on time, or a bit early if you can. If you are more than 10 minutes late, you may be
assigned as a no-show.

IMPORTANT: please review the guidelines below regarding eye makeup and eyewear.

Eye Makeup: Please avoid heavy eye makeup on the day of the experiment. This
includes thick eyeliner, heavy mascara, glittery or shimmery eyeshadows, and
false eyelashes. Understanding that you may be coming directly from other
commitments, we will provide makeup removal facilities and products in the
lab. This will allow you to participate if you are wearing makeup upon
arrival.

Vision Correction: If you require vision correction, we recommend clear and
non-tinted contact lenses. Glasses, especially those with
thick, reflective, or tinted lenses, can interfere with the eye-tracking
equipment. If you must wear glasses, please choose a pair with thin, plastic
frames and clear, non-reflective lenses.

Location: The study is being run in Meyer 566. If you take one of the main
elevators, you take a right out of the elevator, then your first right, you'll
walk down a hallway and up some stairs, and then when you hit the end of the
hallway, 566 will be directly to your left. If you instead take the side
elevator, you'll come out into a waiting area with seats. Then, the experiment
will be down the hall to your left.

Thanks for participating!

Fred
""".strip()

CRED_HELP = """
To use this script you must create a credentials file.

- go to https://console.cloud.google.com/
- create a project
- from your new project page, find "Enabled APIs and services"
- enable the gmail API
- check the boxes for gmail.send and gmail.modify permissions
- download the file, which will start with client_secret
- rename to credentials.json
- ✨
"""

if not os.path.isfile('credentials.json'):
    print(CRED_HELP)
    exit(1)

try:
    with open('reminded.txt') as f:
        reminded = set(email.strip() for email in f.readlines())
except FileNotFoundError:
    reminded = set()

def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

GMAIL = get_gmail_service()

def get_message_body(msg):
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' or part['mimeType'] == 'text/html':
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    else:
        return base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')

def create_message(to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_email(to, subject, message_text):
    message = create_message(to, subject, message_text)
    GMAIL.users().messages().send(userId='me', body=message).execute()

def send_reminder(email, full_name, dt):
    if email in reminded:
        print(f'{email} has already been reminded. Skipping.')
        return
    assert datetime.now().date() == dt.date()
    date = dt.strftime('%A, %B %d')
    time = dt.strftime('%l:%M%p').strip()
    subject = f"Reminder: study today at {time} in Meyer 566"
    name = full_name.split()[0]
    my_body = BODY.format(name=name, date=date, time=time)
    my_body = my_body.replace('\n\n', 'BREAK').replace('\n', ' ').replace('BREAK', '\n\n')

    send_email(email, subject, my_body)
    print(f'Sent a reminder to {email}')
    with open('reminded.txt', 'a') as f:
        f.write(email + '\n')

def get_todays_participants(kind = "Sign-Up"):
    today = datetime.now()
    dstring = today.strftime('%A, %B %-d')
    query = f'from: nyu-psych-admin@sona-systems.net subject: "Study {kind} Notification" "{dstring}"'
    result = GMAIL.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])


    participants = []
    for message in messages:
        msg = GMAIL.users().messages().get(userId='me', id=message['id'], format='full').execute()
        body = get_message_body(msg)

        # Extract the appointment details and email address
        full_name, email = re.search(r'The participant (.*) <(\S+@\S+)>', body).groups()

        date = re.search(r'The study (is|was) scheduled to take place on (.*) in the location', body).group(2)
        start, end = date.split(' - ')
        dt = datetime.strptime(start, '%A, %B %d, %Y %I:%M %p')
        if today.date() == dt.date():
            participants.append((dt, full_name, email))

    return participants

def main(remind=False):
    today = datetime.now()
    signed_up = get_todays_participants()
    cancelled = get_todays_participants("Cancellation")
    for c in cancelled:
        assert c in signed_up

    participants = sorted(set(signed_up).difference(set(cancelled)))

    for (dt, full_name, email) in participants:
        print(dt.strftime('%I:%M %p'), full_name, email, sep='   ')

    if remind and input('send reminders? [N/y]') == 'y':
            assert len(participants) < 20  # failsafe: make sure we don't email too many people
            for (dt, full_name, email) in participants:
                send_reminder(email, full_name, dt)

if __name__ == '__main__':
    Fire(main)