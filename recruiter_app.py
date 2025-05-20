import os
import json
import base64
import csv
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes
import openai  # or anthropic, or other API of your choice

# Load environment variables
load_dotenv()

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
RECRUITER_LABEL = 'money/jobs/job agents'  # Label containing LinkedIn job emails
TEST_EMAIL_LIMIT =150
MAX_EMAIL_AGE_YEARS = 4  # Maximum age of emails to process

def is_email_recent(date_str):
    try:
        # Parse the email date string to datetime
        email_date = parsedate_to_datetime(date_str)
        # Calculate the cutoff date (4 years ago from now)
        cutoff_date = datetime.now(email_date.tzinfo) - timedelta(days=MAX_EMAIL_AGE_YEARS * 365)
        # Return True if email is newer than cutoff date
        return email_date > cutoff_date
    except Exception as e:
        print(f"Warning: Could not parse date '{date_str}': {str(e)}")
        return False  # Skip emails with invalid dates

def authenticate_gmail():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        # Create credentials.json from environment variables
        credentials_dict = json.loads(os.getenv('GMAIL_CLIENT_SECRET_JSON'))
        with open('credentials.json', 'w') as f:
            json.dump(credentials_dict, f)
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def get_recruiter_emails(service, label_name=RECRUITER_LABEL, max_results=TEST_EMAIL_LIMIT):
    try:
        # Get label ID for the recruiter folder
        print(f"Searching for label: {label_name}")
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        label_id = None
        for label in labels:
            if label['name'] == label_name:
                label_id = label['id']
                break
        
        if not label_id:
            print(f"Error: Label '{label_name}' not found")
            return []
        
        print(f"Found label ID: {label_id}")
        print(f"Fetching up to {max_results} emails...")
        
        # Get messages with that label
        results = service.users().messages().list(
            userId='me', labelIds=[label_id], maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No messages found in the label")
            return []
            
        print(f"Found {len(messages)} messages")
        
        emails = []
        for i, message in enumerate(messages, 1):
            print(f"Processing email {i}/{len(messages)}")
            try:
                msg = service.users().messages().get(
                    userId='me', id=message['id'], format='raw').execute()
                
                # Convert from Base64
                msg_bytes = base64.urlsafe_b64decode(msg['raw'])
                mime_msg = message_from_bytes(msg_bytes)
                
                # Extract date, from, subject and body
                date = None
                sender = None
                subject = None
                body = ""
                
                # Basic extraction of headers
                if mime_msg['Date']:
                    date = mime_msg['Date']
                    # Skip if email is too old
                    if not is_email_recent(date):
                        print(f"Skipping email {i} - older than {MAX_EMAIL_AGE_YEARS} years")
                        continue
                if mime_msg['From']:
                    sender = mime_msg['From']
                if mime_msg['Subject']:
                    subject = mime_msg['Subject']
                    
                # Extract body (simplified)
                if mime_msg.is_multipart():
                    for part in mime_msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                            except Exception as e:
                                print(f"Warning: Could not decode body for email {i}: {str(e)}")
                                body = ""
                            break
                else:
                    try:
                        body = mime_msg.get_payload(decode=True).decode()
                    except Exception as e:
                        print(f"Warning: Could not decode body for email {i}: {str(e)}")
                        body = ""
                
                emails.append({
                    'message_id': message['id'],
                    'date': date,
                    'sender': sender,
                    'subject': subject,
                    'body': body
                })
            except Exception as e:
                print(f"Error processing email {i}: {str(e)}")
                continue
        
        print(f"Found {len(emails)} recent emails (less than {MAX_EMAIL_AGE_YEARS} years old)")
        return emails
    except Exception as e:
        print(f"Error in get_recruiter_emails: {str(e)}")
        return []

def extract_recruiter_info(email_data):
    try:
        # Use OpenAI API key from environment variables
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key not found in environment variables")
        
        prompt = f"""
        Extract the following information from this recruiter email:
        - Full name of recruiter
        - Email address
        - Company
        - Date of contact (use the email date if not mentioned in body)
        - Job type/role mentioned

        Format the output as a valid JSON object with these exact fields:
        {{
          "name": "",
          "email": "",
          "company": "",
          "last_contact": "YYYY-MM-DD",
          "job_type": ""
        }}

        Email:
        From: {email_data['sender']}
        Date: {email_data['date']}
        Subject: {email_data['subject']}
        
        {email_data['body']}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract structured data from recruiter emails accurately."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and parse the JSON response
        try:
            extracted_json = json.loads(response.choices[0].message.content.strip())
            return extracted_json
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for email: {email_data['subject']}")
            print(f"Error: {str(e)}")
            return {
                "name": "",
                "email": email_data['sender'],
                "company": "",
                "last_contact": email_data['date'],
                "job_type": ""
            }
    except Exception as e:
        print(f"Error in extract_recruiter_info: {str(e)}")
        return {
            "name": "",
            "email": email_data['sender'],
            "company": "",
            "last_contact": email_data['date'],
            "job_type": ""
        }

def load_existing_contacts(filename='recruiter_contacts.csv'):
    """Load existing contacts from CSV file."""
    existing_contacts = {
        'regular': set(),  # Set of regular email addresses
        'linkedin': {}     # Dict of LinkedIn contacts {name: email}
    }
    
    if not os.path.exists(filename):
        print("No existing contacts file found")
        return existing_contacts
        
    try:
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                email = row['email'].lower().strip()
                name = row['name'].lower().strip()
                
                if not email:  # Skip rows with no email
                    continue
                    
                if email == 'inmail-hit-reply@linkedin.com':
                    existing_contacts['linkedin'][name] = email
                else:
                    existing_contacts['regular'].add(email)
                    
        print(f"Loaded {len(existing_contacts['regular'])} regular contacts and {len(existing_contacts['linkedin'])} LinkedIn contacts from CSV")
        print("Regular contacts:", existing_contacts['regular'])
        return existing_contacts
    except Exception as e:
        print(f"Error loading existing contacts: {str(e)}")
        return existing_contacts

def is_duplicate_contact(contact_data, existing_contacts):
    """Check if a contact is a duplicate based on our rules."""
    email = contact_data['email'].lower()
    name = contact_data['name'].lower()
    
    # Special handling for LinkedIn InMail
    if email == 'inmail-hit-reply@linkedin.com':
        # Only consider it a duplicate if both name and email match
        return name in existing_contacts['linkedin']
    else:
        # For all other emails, check if email exists
        return email in existing_contacts['regular']

def is_duplicate_email(email, existing_contacts):
    """Check if an email is a duplicate based on our rules."""
    email = email.lower().strip()
    
    # Special handling for LinkedIn InMail
    if email == 'inmail-hit-reply@linkedin.com':
        # For LinkedIn InMail, we need the name too, so return False here
        return False
    else:
        # For all other emails, check if email exists
        is_duplicate = email in existing_contacts['regular']
        if is_duplicate:
            print(f"Found duplicate email: {email}")
        return is_duplicate

def save_to_csv(recruiter_data, filename='recruiter_contacts.csv'):
    # Append new contacts to existing file
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'email', 'company', 'last_contact', 'job_type']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for contact in recruiter_data:
            writer.writerow(contact)
    
    return len(recruiter_data)

def main():
    try:
        print("Starting recruiter email processing...")
        
        # Get API service
        print("Authenticating with Gmail...")
        service = authenticate_gmail()
        
        # Load existing contacts from CSV
        existing_contacts = load_existing_contacts()
        
        # Get emails from the money-jobs-job-agents label
        emails = get_recruiter_emails(service)
        
        if not emails:
            print("No emails found to process")
            return
            
        print(f"\nProcessing {len(emails)} emails...")
        
        # Process each email
        recruiter_data = []
        for i, email in enumerate(emails, 1):
            print(f"\nProcessing email {i}/{len(emails)}")
            print(f"Subject: {email['subject']}")
            print(f"From: {email['sender']}")
            
            # Check for duplicate email before calling ChatGPT
            if is_duplicate_email(email['sender'], existing_contacts):
                print(f"Skipping duplicate email: {email['sender']}")
                continue
                
            info = extract_recruiter_info(email)
            
            # For LinkedIn InMail, we need to check name+email after getting the info
            if info['email'].lower() == 'inmail-hit-reply@linkedin.com':
                if is_duplicate_contact(info, existing_contacts):
                    print(f"Skipping duplicate LinkedIn contact: {info['name']}")
                    continue
            
            recruiter_data.append(info)
            # Update our tracking of processed contacts
            email = info['email'].lower().strip()
            name = info['name'].lower().strip()
            if email == 'inmail-hit-reply@linkedin.com':
                existing_contacts['linkedin'][name] = email
            else:
                existing_contacts['regular'].add(email)
            
            print(f"Extracted data: {json.dumps(info, indent=2)}")
        
        # Save results
        print("\nSaving results to CSV...")
        new_contacts_count = save_to_csv(recruiter_data)
        print(f"Successfully added {new_contacts_count} new contacts to recruiter_contacts.csv")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == '__main__':
    main()