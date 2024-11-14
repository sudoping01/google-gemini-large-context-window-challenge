
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pickle, os, base64
from time import gmtime, strftime
from datetime import datetime
from collections import namedtuple
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from typing import Dict, Any

class Google: 
    def __init__(self, client_credentials_file_path) -> None:
          self.mail_service:Any       = None 
          self.calendar_service:Any   = None
          self.client_secret_file:str = client_credentials_file_path
          self.context:Dict[str:str]  = {"function" : "send mail, read mail and check upcoming events"}

    def _Create_Service(self, api_name, api_version, *scopes, prefix=''):
        CLIENT_SECRET_FILE = self.client_secret_file
        API_SERVICE_NAME = api_name
        API_VERSION = api_version
        SCOPES = [scope for scope in scopes[0]]
        
        cred = None
        working_dir = os.getcwd()
        token_dir = 'token files'
        pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.pickle'


        if not os.path.exists(os.path.join(working_dir, token_dir)):
            os.mkdir(os.path.join(working_dir, token_dir))

        if os.path.exists(os.path.join(working_dir, token_dir, pickle_file)):
            with open(os.path.join(working_dir, token_dir, pickle_file), 'rb') as token:
                cred = pickle.load(token)

        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                cred = flow.run_local_server()

            with open(os.path.join(working_dir, token_dir, pickle_file), 'wb') as token:
                pickle.dump(cred, token)

        try:
            service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
            return service
        
        except Exception as e:
            print(e)
            print(f'Failed to create service instance for {API_SERVICE_NAME}')
            os.remove(os.path.join(working_dir, token_dir, pickle_file))
            return None


    def send_email(self,to, subject, body):
        try : 
            if self.mail_service is None :
                self.mail_service = self._Create_Service('gmail',"v1",['https://mail.google.com/'])

            emailMsg = body
            mimeMessage = MIMEMultipart()
            mimeMessage['to'] = to
            mimeMessage['subject'] = subject
            mimeMessage.attach(MIMEText(emailMsg, 'plain'))
            raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()
            self.mail_service.users().messages().send(userId="me", body={'raw': raw_string}).execute()
            return True 
        except Exception as e: 
            return False 


    

    def get_emails(self,max_results=10000) -> dict:
        if self.mail_service is None :
            self.mail_service = self._Create_Service('gmail',"v1", ['https://mail.google.com/'])

        results = self.mail_service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        msgs = {}
        if not messages:
            return {}
            
        else:

            for message in messages:
                msg = self.mail_service.users().messages().get(userId='me', id=message['id']).execute()
                
                # Get headers
                headers = msg['payload']['headers']
                subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), '(No subject)')
                sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), '(No sender)')
                
                # Get body
                if 'parts' in msg['payload']:
                    parts = msg['payload']['parts']
                    body = ''
                    for part in parts:
                        if part['mimeType'] == 'text/plain':
                            body = part['body'].get('data', '')
                            break
                else:
                    body = msg['payload']['body'].get('data', '')
                
                if body:
                    body = base64.urlsafe_b64decode(body).decode('utf-8')
                else:
                    body = '(No body)'
                
                msgs[messages.index(message)] = {"From" : sender, "suject" : subject, "Body" : body}

        return msgs 

    
    def get_events(self, max_results=100):
        comingEvents = {}
        if self.calendar_service is None :
            self.calendar_service = self._Create_Service('calendar',"v3", ['https://www.googleapis.com/auth/calendar'])

        now = strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())
        events_result = self.calendar_service.events().list(calendarId='primary', timeMin=now,
                                                        maxResults=max_results, singleEvents=True,
                                                        orderBy='startTime').execute()
        events = events_result.get('items', [])
    
        if not events:
            return {"Events": "No up coming events"}
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                comingEvents[events.index(event)] = {"Event" : event['summary'], "Start" : start}

        return comingEvents
    
    
    def set_event(self, summary:str, location:str = None, description:str= None, start_time:datetime = None, end_time:datetime=None, attendees:list=None):
        if self.calendar_service is None:
            self.calendar_service = self._Create_Service('calendar', "v3", ['https://www.googleapis.com/auth/calendar'])

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': attendee} for attendee in attendees]

        event = self.calendar_service.events().insert(calendarId='primary', body=event).execute()
        return event.get('htmlLink')