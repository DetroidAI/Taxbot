from flask import Flask, request, jsonify
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import os
import re
from typing import Dict, List, Optional

app = Flask(__name__)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
CALENDAR_ID = os.getenv('CALENDAR_ID')  # Your Google Calendar ID
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')  # Your Google Sheets ID

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Google API Setup
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_google_credentials():
    """Initialize Google API credentials"""
    return Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)

def get_calendar_service():
    """Get Google Calendar service"""
    credentials = get_google_credentials()
    return build('calendar', 'v3', credentials=credentials)

def get_sheets_service():
    """Get Google Sheets service"""
    credentials = get_google_credentials()
    return build('sheets', 'v4', credentials=credentials)

class AppointmentAssistant:
    def __init__(self):
        self.conversation_state = {}
        self.pending_confirmations = {}
        
    def extract_appointment_info(self, message: str, conversation_history: List[str]) -> Dict:
        """Extract appointment information using Gemini"""
        
        prompt = f"""
        You are an AI appointment assistant. Analyze the following conversation and extract appointment information.
        
        Conversation History: {' '.join(conversation_history[-5:])}
        Current Message: {message}
        
        Extract the following information if available:
        - Customer Name
        - Phone Number
        - Email
        - Preferred Date (format: YYYY-MM-DD)
        - Preferred Time (format: HH:MM)
        - Service Type
        - Duration (in minutes, default 60)
        - Additional Notes
        
        Return ONLY a JSON object with these fields. Use null for missing information.
        Example: {{"name": "John Doe", "phone": "+1234567890", "email": "john@email.com", "date": "2024-12-15", "time": "14:30", "service": "Consultation", "duration": 60, "notes": "First time customer"}}
        """
        
        try:
            response = model.generate_content(prompt)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Error extracting appointment info: {e}")
        
        return {}
    
    def check_calendar_availability(self, date: str, time: str, duration: int = 60) -> Dict:
        """Check if the requested time slot is available"""
        try:
            calendar_service = get_calendar_service()
            
            # Convert to datetime
            appointment_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = appointment_datetime + timedelta(minutes=duration)
            
            # Query calendar for conflicts
            events_result = calendar_service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=appointment_datetime.isoformat() + 'Z',
                timeMax=end_datetime.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                return {
                    'available': False,
                    'conflicts': [event.get('summary', 'Busy') for event in events]
                }
            else:
                return {'available': True, 'conflicts': []}
                
        except Exception as e:
            print(f"Calendar check error: {e}")
            return {'available': False, 'error': str(e)}
    
    def get_available_slots(self, date: str, duration: int = 60) -> List[str]:
        """Get available time slots for a given date"""
        try:
            calendar_service = get_calendar_service()
            
            # Define business hours (9 AM to 5 PM)
            start_time = datetime.strptime(f"{date} 09:00", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date} 17:00", "%Y-%m-%d %H:%M")
            
            # Get all events for the day
            events_result = calendar_service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Generate all possible slots
            available_slots = []
            current_time = start_time
            
            while current_time < end_time:
                slot_end = current_time + timedelta(minutes=duration)
                if slot_end <= end_time:
                    # Check if this slot conflicts with any event
                    conflict = False
                    for event in events:
                        event_start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                        event_end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                        
                        if (current_time < event_end and slot_end > event_start):
                            conflict = True
                            break
                    
                    if not conflict:
                        available_slots.append(current_time.strftime("%H:%M"))
                
                current_time += timedelta(minutes=30)  # Check every 30 minutes
            
            return available_slots
            
        except Exception as e:
            print(f"Error getting available slots: {e}")
            return []
    
    def create_calendar_event(self, appointment_info: Dict) -> bool:
        """Create a calendar event"""
        try:
            calendar_service = get_calendar_service()
            
            start_datetime = datetime.strptime(
                f"{appointment_info['date']} {appointment_info['time']}", 
                "%Y-%m-%d %H:%M"
            )
            end_datetime = start_datetime + timedelta(minutes=appointment_info.get('duration', 60))
            
            event = {
                'summary': f"{appointment_info['service']} - {appointment_info['name']}",
                'description': f"Customer: {appointment_info['name']}\nPhone: {appointment_info['phone']}\nEmail: {appointment_info['email']}\nNotes: {appointment_info.get('notes', '')}",
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/New_York',  # Adjust timezone as needed
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'attendees': [
                    {'email': appointment_info['email']},
                ],
            }
            
            created_event = calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
            return True
            
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return False
    
    def save_to_sheets(self, appointment_info: Dict) -> bool:
        """Save appointment data to Google Sheets"""
        try:
            sheets_service = get_sheets_service()
            
            # Prepare data row
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [
                timestamp,
                appointment_info.get('name', ''),
                appointment_info.get('phone', ''),
                appointment_info.get('email', ''),
                appointment_info.get('date', ''),
                appointment_info.get('time', ''),
                appointment_info.get('service', ''),
                appointment_info.get('duration', 60),
                appointment_info.get('notes', ''),
                'Confirmed'
            ]
            
            # Append to sheet
            body = {'values': [row_data]}
            sheets_service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range='A:J',  # Adjust range as needed
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Error saving to sheets: {e}")
            return False
    
    def generate_response(self, message: str, conversation_history: List[str], user_id: str) -> Dict:
        """Generate AI response based on conversation context"""
        
        # Extract appointment information
        appointment_info = self.extract_appointment_info(message, conversation_history)
        
        # Check if we have enough information to proceed
        required_fields = ['name', 'phone', 'date', 'time', 'service']
        missing_fields = [field for field in required_fields if not appointment_info.get(field)]
        
        if missing_fields:
            # Ask for missing information
            prompt = f"""
            You are a friendly appointment booking assistant. The customer has provided some information but is missing: {', '.join(missing_fields)}.
            
            Current conversation: {message}
            Available info: {appointment_info}
            
            Ask for the missing information in a natural, friendly way. Be specific about the format needed (e.g., date as YYYY-MM-DD, time as HH:MM).
            """
            
            try:
                response = model.generate_content(prompt)
                return {
                    'message': response.text,
                    'status': 'collecting_info',
                    'appointment_info': appointment_info
                }
            except Exception as e:
                return {
                    'message': "I'd be happy to help you book an appointment. Could you please provide your name, phone number, preferred date, time, and the service you need?",
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check availability
        availability = self.check_calendar_availability(
            appointment_info['date'], 
            appointment_info['time'], 
            appointment_info.get('duration', 60)
        )
        
        if availability.get('available'):
            # Slot is available, request human confirmation
            confirmation_id = f"{user_id}_{datetime.now().timestamp()}"
            self.pending_confirmations[confirmation_id] = appointment_info
            
            return {
                'message': f"Great! I found that {appointment_info['date']} at {appointment_info['time']} is available for {appointment_info['service']}. I'm now checking with our team to confirm this appointment. You'll receive a confirmation message shortly.",
                'status': 'pending_confirmation',
                'confirmation_id': confirmation_id,
                'appointment_info': appointment_info
            }
        else:
            # Slot not available, suggest alternatives
            available_slots = self.get_available_slots(appointment_info['date'])
            
            if available_slots:
                slots_text = ', '.join(available_slots[:5])  # Show first 5 slots
                return {
                    'message': f"I'm sorry, but {appointment_info['time']} on {appointment_info['date']} is not available. Here are some available times on the same date: {slots_text}. Would any of these work for you?",
                    'status': 'suggesting_alternatives',
                    'available_slots': available_slots,
                    'appointment_info': appointment_info
                }
            else:
                return {
                    'message': f"Unfortunately, there are no available slots on {appointment_info['date']}. Could you suggest an alternative date?",
                    'status': 'no_availability',
                    'appointment_info': appointment_info
                }

# Initialize assistant
assistant = AppointmentAssistant()

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.json
        message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        conversation_history = data.get('history', [])
        
        # Generate response
        result = assistant.generate_response(message, conversation_history, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'message': "I'm sorry, I encountered an error. Please try again.",
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    """Endpoint for human assistant to confirm appointments"""
    try:
        data = request.json
        confirmation_id = data.get('confirmation_id')
        approved = data.get('approved', False)
        human_notes = data.get('notes', '')
        
        if confirmation_id not in assistant.pending_confirmations:
            return jsonify({'error': 'Confirmation ID not found'}), 404
        
        appointment_info = assistant.pending_confirmations[confirmation_id]
        
        if approved:
            # Create calendar event and save to sheets
            calendar_success = assistant.create_calendar_event(appointment_info)
            sheets_success = assistant.save_to_sheets(appointment_info)
            
            if calendar_success and sheets_success:
                # Remove from pending
                del assistant.pending_confirmations[confirmation_id]
                
                return jsonify({
                    'message': f"Appointment confirmed for {appointment_info['name']} on {appointment_info['date']} at {appointment_info['time']}",
                    'status': 'confirmed',
                    'appointment_info': appointment_info
                })
            else:
                return jsonify({
                    'message': 'Error creating appointment',
                    'status': 'error'
                }), 500
        else:
            # Appointment rejected
            del assistant.pending_confirmations[confirmation_id]
            return jsonify({
                'message': f"Appointment request denied. Reason: {human_notes}",
                'status': 'denied'
            })
            
    except Exception as e:
        return jsonify({
            'message': 'Error processing confirmation',
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/available_slots/<date>', methods=['GET'])
def get_available_slots(date):
    """Get available slots for a specific date"""
    try:
        duration = int(request.args.get('duration', 60))
        slots = assistant.get_available_slots(date, duration)
        
        return jsonify({
            'date': date,
            'available_slots': slots
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/pending_confirmations', methods=['GET'])
def get_pending_confirmations():
    """Get all pending appointment confirmations for human assistant"""
    return jsonify({
        'pending_confirmations': assistant.pending_confirmations
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)