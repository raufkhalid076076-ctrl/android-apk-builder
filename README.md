## School Fee Manager

A simple Flask + SQLite app to manage student fees, print slips, and send WhatsApp notifications.

### Features
- Add/edit/delete students: class, name, parent WhatsApp, monthly fee
- Record payments per month (Jan-Dec)
- Print fee slip per student
- Send WhatsApp notification (placeholder – integrate Twilio or Meta Cloud API)

### Setup
1. Create and activate a virtual environment
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Run the app
```bash
python app.py
```
App runs at `http://127.0.0.1:5000/`.

### WhatsApp Integration
This repo has a placeholder endpoint `POST /api/notify/<student_id>`.
Replace the placeholder with one of:

- Twilio WhatsApp:
```python
from twilio.rest import Client
client = Client(account_sid, auth_token)
client.messages.create(
    from_='whatsapp:+14155238886', to=f'whatsapp:{s.parent_phone}', body=message
)
```

- Meta WhatsApp Cloud API:
```python
import requests
requests.post(
    'https://graph.facebook.com/v19.0/YOUR_PHONE_NUMBER_ID/messages',
    headers={'Authorization': f'Bearer {ACCESS_TOKEN}'},
    json={
      'messaging_product':'whatsapp',
      'to': s.parent_phone,
      'type':'text',
      'text':{'body': message}
    }
)
```

Set environment variables or config securely; do not hardcode secrets.






