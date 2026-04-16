import requests
from bs4 import BeautifulSoup

session = requests.Session()
r = session.get('http://localhost:5000/driver/login')
soup = BeautifulSoup(r.text, 'html.parser')

meta_tag = soup.find('meta', {'name': 'csrf-token'})
csrf_token = meta_tag.get('content') if meta_tag else None

if csrf_token:
    data = {
        'email': 'driver679078@example.com',
        'password': 'password123',
        'csrf_token': csrf_token
    }
    session.post('http://localhost:5000/driver/login', data=data)

# Get dashboard with full error
r = session.get('http://localhost:5000/driver/dashboard')
print(f'Dashboard status: {r.status_code}')
if r.status_code != 200:
    # Find the error message
    soup = BeautifulSoup(r.text, 'html.parser')
    # Look for error text
    if 'Traceback' in r.text:
        # Extract Python traceback
        start = r.text.find('Traceback')
        end = r.text.find('</pre>', start)
        if end == -1:
            end = len(r.text)
        error_text = r.text[start:end]
        # Print last 1000 chars
        print(error_text[-2000:])
