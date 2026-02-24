import requests
import csv
from io import StringIO
import os

def get_products():
    csv_url = os.getenv("GOOGLE_SHEET_CSV")
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        products = {}
        for row in reader:
            name = row.get("Product Name", "").lower().strip()
            if name:
                products[name] = {
                    "price": row.get("Price Range", ""),
                    "sizes": row.get("Sizes Available", ""),
                    "colors": row.get("Colors Available", ""),
                    "availability": row.get("Availability", ""),
                    "material": row.get("Material", ""),
                    "moq": row.get("MOQ (Min Order)", ""),
                    "delivery": row.get("Delivery Days", "")
                }
        return products
    except Exception as e:
        print(f"Error loading products: {e}")
        return {}