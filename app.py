from flask import Flask, request, Response, jsonify, send_file
from dotenv import load_dotenv
import os
import requests
import base64
from intent import get_faq_answer, classify_intent
from logger import log_call
import csv
from io import StringIO

load_dotenv()

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
OWNER_WHATSAPP = os.getenv("OWNER_WHATSAPP")

def create_twiml_response(message):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="en-IN">{message}</Say>
</Response>'''

def create_gather_twiml(message):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/voice/process" method="POST" speechTimeout="5" language="en-IN" hints="price size availability color delivery bulk order track status">
        <Say voice="Polly.Aditi" language="en-IN">{message}</Say>
    </Gather>
    <Say voice="Polly.Aditi" language="en-IN">Sorry, I did not catch that. Please call again.</Say>
</Response>'''

def get_order_status(query):
    """Check order status from Google Sheet"""
    csv_url = os.getenv("ORDER_STATUS_CSV")
    try:
        response = requests.get(csv_url, timeout=10)
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        query_lower = query.lower()
        
        for row in reader:
            order_id = row.get("Order ID", "").strip()
            name = row.get("Customer Name", "").strip()
            
            # Match by Order ID or Name
            if order_id.lower() in query_lower or name.lower() in query_lower:
                status = row.get("Dispatch Status", "").strip()
                delivery = row.get("Expected Delivery", "").strip()
                product = row.get("Product", "").strip()
                
                return f"Your order {order_id} for {product} is {status}. Expected delivery: {delivery}."
        
        return "Sorry, I could not find your order. Please contact our customer service for assistance."
    except:
        return "Sorry, I am unable to check order status right now. Please try again later."

@app.route("/voice/inbound", methods=["GET", "POST"])
def inbound():
    caller = request.form.get("From", "Unknown")
    call_sid = request.form.get("CallSid", "")
    
    greeting = "Welcome to Vastram boutique! I am your AI assistant. You can ask me about product details, pricing, sizes, or check your order status. Please speak your question after the tone."
    
    log_call(caller, call_sid, "inbound", "greeted", "")
    return Response(create_gather_twiml(greeting), mimetype="text/xml")

@app.route("/voice/process", methods=["POST"])
def process():
    caller = request.form.get("From", "Unknown")
    call_sid = request.form.get("CallSid", "")
    speech = request.form.get("SpeechResult", "").strip()
    confidence = float(request.form.get("Confidence", 0))
    
    if not speech or confidence < 0.4:
        log_call(caller, call_sid, "inbound", "low_confidence", speech)
        return Response(create_twiml_response("I am sorry, I could not understand you clearly. Our owner will call you back."), mimetype="text/xml")
    
    # Check if order tracking query
    intent = classify_intent(speech)
    
    if intent == "order_status":
        log_call(caller, call_sid, "inbound", "order_status", speech)
        message = "Sure, wait a minute, let me check. Please tell me your order ID or your name."
        
        # Use a special route to capture order details
        return Response(f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/voice/order_check" method="POST" speechTimeout="5" language="en-IN" hints="order ORD001 ORD002 ORD003 Agalya SUBI JAYA">
        <Say voice="Polly.Aditi" language="en-IN">{message}</Say>
    </Gather>
    <Say voice="Polly.Aditi" language="en-IN">Sorry, I did not catch that. Please call again.</Say>
</Response>''', mimetype="text/xml")
    # Regular FAQ
    intent, answer = get_faq_answer(speech)
    log_call(caller, call_sid, "inbound", intent, speech)
    
    # Add "wait a minute" before product queries
    if intent in ["price", "size", "availability", "color", "delivery", "material"]:
        answer = f"Sure, wait a minute, let me check. {answer}"
    
    if intent == "bulk_order":
        send_owner_alert(caller, speech, intent)
        message = f"{answer} Thank you for your interest!"
    elif intent == "human_needed":
        send_owner_alert(caller, speech, intent)
        message = f"{answer} Thank you for calling!"
    else:
        message = f"{answer} Do you have any other questions?"

    return Response(create_gather_twiml(message), mimetype="text/xml")

@app.route("/voice/order_check", methods=["POST"])
def order_check():
    """Handle order status check after customer provides order ID/name"""
    caller = request.form.get("From", "Unknown")
    call_sid = request.form.get("CallSid", "")
    speech = request.form.get("SpeechResult", "").strip()
    
    if not speech:
        return Response(create_twiml_response("Sorry, I did not catch that. Please call again."), mimetype="text/xml")
    
    # Get order status
    status_message = get_order_status(speech)
    log_call(caller, call_sid, "inbound", "order_checked", speech)
    
    message = f"{status_message} Do you have any other questions?"
    return Response(create_gather_twiml(message), mimetype="text/xml")

def send_owner_alert(caller, query, intent):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    auth = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    
    body = f"🔔 HIGH INTENT LEAD\nCaller: {caller}\nIntent: {intent}\nQuery: {query}"
    
    data = {
        "From": f"whatsapp:{TWILIO_NUMBER}",
        "To": f"whatsapp:{OWNER_WHATSAPP}",
        "Body": body
    }
    
    try:
        requests.post(url, data=data, headers={"Authorization": f"Basic {auth}"})
    except Exception as e:
        print(f"WhatsApp alert failed: {e}")

@app.route("/api/logs", methods=["GET"])
def get_logs():
    logs = []
    if os.path.exists("call_logs.csv"):
        with open("call_logs.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                logs.append(row)
    return jsonify(logs[::-1])

@app.route("/api/stats", methods=["GET"])
def get_stats():
    logs = []
    if os.path.exists("call_logs.csv"):
        with open("call_logs.csv", "r") as f:
            reader = csv.DictReader(f)
            logs = list(reader)
    
    total = len(logs)
    resolved = sum(1 for l in logs if l["intent"] not in ["human_needed", "low_confidence"])
    high_intent = sum(1 for l in logs if l["intent"] == "bulk_order")
    intents = {}
    for l in logs:
        intents[l["intent"]] = intents.get(l["intent"], 0) + 1
    
    return jsonify({
        "total_calls": total,
        "bot_resolved": resolved,
        "high_intent_leads": high_intent,
        "resolution_rate": round((resolved / total * 100) if total else 0, 1),
        "intent_breakdown": intents
    })

@app.route("/")
def dashboard():
    return send_file("dashboard.html")

@app.route("/voice/outbound", methods=["POST"])
def outbound():
    data = request.json
    to_number = data.get("to")
    campaign = data.get("campaign", "our latest collection")
    
    if not to_number:
        return jsonify({"error": "Missing 'to' number"}), 400
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
    auth = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    
    call_data = {
        "To": to_number,
        "From": TWILIO_NUMBER,
        "Url": request.host_url + f"voice/outbound_script?campaign={campaign}"
    }
    
    try:
        response = requests.post(url, data=call_data, headers={"Authorization": f"Basic {auth}"})
        call = response.json()
        log_call(to_number, call.get("sid", ""), "outbound", "initiated", campaign)
        return jsonify({"status": "call_initiated", "sid": call.get("sid")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/voice/outbound_script", methods=["GET", "POST"])
def outbound_script():
    campaign = request.args.get("campaign", "our latest collection")
    greeting = f"Hello! This is a message from Vastram boutique. {campaign}. You can ask me about pricing, sizes, availability, or any questions. Please speak after the tone."
    return Response(create_gather_twiml(greeting), mimetype="text/xml")

@app.route("/api/trigger_campaign", methods=["POST"])
def trigger_campaign():
    import requests as req
    from io import StringIO
    import time
    
    data = request.json
    message = data.get("message", "")
    
    csv_url = os.getenv("CUSTOMER_LIST_CSV")
    try:
        response = req.get(csv_url, timeout=10)
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        customers = []
        for row in reader:
            phone = row.get("PHONE NUMBER", "").strip()
            if phone:
                customers.append(phone)
    except:
        return jsonify({"error": "Failed to load customer list"}), 500
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
    auth = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    
    for phone in customers:
        call_data = {
            "To": phone,
            "From": TWILIO_NUMBER,
            "Url": os.getenv("NGROK_URL") + f"/voice/outbound_script?campaign={message}"
        }
        try:
            result = req.post(url, data=call_data, headers={"Authorization": f"Basic {auth}"})
            print(f"Twilio response: {result.status_code} - {result.text}")
            time.sleep(2)
        except Exception as e:
         print(f"Twilio call failed: {e}")
    
    return jsonify({"status": "success", "total": len(customers)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)