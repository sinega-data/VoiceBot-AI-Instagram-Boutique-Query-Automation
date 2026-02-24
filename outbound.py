import requests
import csv
import os
from io import StringIO
import time
import base64

def get_customers():
    csv_url = os.getenv("CUSTOMER_LIST_CSV")
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        customers = []
        for row in reader:
            name = row.get("Customer Name", "").strip()
            phone = row.get("Phone Number", "").strip()
            if name and phone:
                customers.append({"name": name, "phone": phone})
        return customers
    except Exception as e:
        print(f"Error loading customers: {e}")
        return []

def trigger_outbound_calls(campaign_message, ngrok_url):
    customers = get_customers()
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_num = os.getenv("TWILIO_NUMBER")
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    
    print(f"Starting outbound calls to {len(customers)} customers...")
    
    for customer in customers:
        data = {
            "To": customer["phone"],
            "From": twilio_num,
            "Url": f"{ngrok_url}/voice/outbound_script?campaign={campaign_message}"
        }
        
        try:
            response = requests.post(url, data=data, headers={"Authorization": f"Basic {auth}"})
            if response.status_code == 201:
                print(f"✓ Called {customer['name']} at {customer['phone']}")
            else:
                print(f"✗ Failed to call {customer['name']}: {response.text}")
        except Exception as e:
            print(f"✗ Error calling {customer['name']}: {e}")
        
        time.sleep(2)  # 2 second gap between calls
    
    print("All calls completed!")

if __name__ == "__main__":
    campaign = "We have a special 20 percent discount on all kurtis this weekend"
    ngrok_url = "https://zuri-unnecessitated-wren.ngrok-free.dev"
    trigger_outbound_calls(campaign, ngrok_url)