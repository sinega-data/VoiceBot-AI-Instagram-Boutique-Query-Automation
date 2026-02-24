import re
from sheets import get_products

def detect_product(text):
    """Find product name in customer query"""
    products = get_products()
    text_lower = text.lower()
    
    for product_name in products.keys():
        if product_name in text_lower:
            return product_name
    return None

def detect_bulk_quantity(text):
    """Detect if customer is asking for bulk order"""
    pattern = r'(\d+)\s*(pieces|pcs|units|quantity)'
    match = re.search(pattern, text.lower())
    if match:
        qty = int(match.group(1))
        if qty >= 5:
            return qty
    return None

def classify_intent(text):
    """Classify the intent of customer query"""
    text_lower = text.lower()
    
    # Order status check
    if any(word in text_lower for word in ['order', 'track', 'status', 'dispatch', 'delivery status', 'where is my order', 'order id']):
        return "order_status"
    
    # Check for bulk order first (highest priority)
    if detect_bulk_quantity(text) or any(word in text_lower for word in ['bulk', 'wholesale', 'resell', 'dealer']):
        return "bulk_order"
    
    # Price query
    if any(word in text_lower for word in ['price', 'cost', 'how much', 'rate', 'rupees', 'rs']):
        return "price"
    
    # Size query
    if any(word in text_lower for word in ['size', 'fitting', 'small', 'medium', 'large', 'xl', 'xxl']):
        return "size"
    
    # Availability
    if any(word in text_lower for word in ['available', 'in stock', 'do you have', 'stock']):
        return "availability"
    
    # Color query
    if any(word in text_lower for word in ['color', 'colour', 'shade', 'red', 'blue', 'green', 'white', 'black']):
        return "color"
    
    # Delivery query
    if any(word in text_lower for word in ['delivery', 'shipping', 'how long', 'days', 'when will i get']):
        return "delivery"
    
    # Material query
    if any(word in text_lower for word in ['material', 'fabric', 'cotton', 'silk', 'rayon', 'georgette']):
        return "material"
    
    # If no specific intent found
    return "human_needed"

def get_faq_answer(query):
    """Get answer for FAQ based on intent and product"""
    intent = classify_intent(query)
    
    if intent == "order_status":
        return intent, "I can help you check your order status."
    
    products = get_products()
    product = detect_product(query)
    
    if intent == "bulk_order":
        qty = detect_bulk_quantity(query)
        if qty:
            answer = f"Great! You are interested in ordering {qty} pieces. Our team will contact you shortly with pricing and delivery details for bulk orders."
        else:
            answer = "Great! You are interested in bulk orders. Our team will contact you shortly with wholesale pricing and delivery details."
        return intent, answer
    
    if not product:
        return "human_needed", "Hello, please tell me which product you are interested in and I will give you the exact details."
    
    p = products.get(product, {})
    
    if intent == "price":
        if p.get('price'):
            answer = f"Our {product} is priced at rupees {p['price']}. Available sizes are {p.get('sizes', 'N/A')}."
        else:
            answer = f"Sorry, I don't have pricing information for {product} right now."
    
    elif intent == "size":
        if p.get('sizes'):
            answer = f"Our {product} is available in sizes {p['sizes']}. Price: rupees {p.get('price', 'N/A')}."
        else:
            answer = f"Sorry, I don't have size information for {product} right now."
    
    elif intent == "availability":
        if p.get('availability'):
            answer = f"Yes, {product} is {p['availability']}. Price: rupees {p.get('price', 'N/A')}, Sizes: {p.get('sizes', 'N/A')}."
        else:
            answer = f"Let me check the availability of {product} for you."
    
    elif intent == "color":
        if p.get('colors'):
            answer = f"Our {product} is available in {p['colors']}. Price: rupees {p.get('price', 'N/A')}."
        else:
            answer = f"Sorry, I don't have color information for {product} right now."
    
    elif intent == "delivery":
        if p.get('delivery'):
            answer = f"Our {product} will be delivered in {p['delivery']}. Price: rupees {p.get('price', 'N/A')}."
        else:
            answer = f"Typical delivery time is 3 to 5 days for {product}."
    
    elif intent == "material":
        if p.get('material'):
            answer = f"Our {product} is made of {p['material']}. Price: rupees {p.get('price', 'N/A')}."
        else:
            answer = f"Sorry, I don't have material information for {product} right now."
    
    else:
        answer = f"I can help you with information about {product}. What would you like to know - price, sizes, colors, or delivery time?"
    
    return intent, answer