import csv
import os
from datetime import datetime

LOG_FILE = "call_logs.csv"
FIELDNAMES = ["timestamp", "caller", "call_sid", "direction", "intent", "query"]

def log_call(caller, call_sid, direction, intent, query):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "caller": caller,
            "call_sid": call_sid,
            "direction": direction,
            "intent": intent,
            "query": query
        })