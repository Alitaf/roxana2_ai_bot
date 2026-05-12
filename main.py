import os
import threading
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from supabase import create_client, Client

# ۱. تنظیمات اتصال (دریافت از محیط رندر)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# اتصال به دیتابیس Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase Connection Error: {e}")
    supabase = None

# ۲. تابع خواندن محصولات (جایگزین لیست ثابت قبلی)
def get_live_inventory():
    if not supabase:
        return "Inventory unavailable."
    try:
        # اضافه کردن brand به لیست ستون‌های انتخابی
        res = supabase.table("products").select("name, brand, price_dhs, link, description").eq("is_available", True).execute()
        
        inventory_text = ""
        for p in res.data:
            # فرمت‌دهی دقیق برای فهماندن ساختار به هوش مصنوعی
            brand = p.get('brand', 'Unknown Brand')
            name = p.get('name', '')
            price = p['price_dhs']
            url = p.get('link', '')
            desc = p.get('description', '')
            
            inventory_text += f"BRAND: {brand} | PRODUCT: {name} | PRICE: {price} Dhs | URL: {url} | FEATURES: {desc}\n"
        return inventory_text
    except Exception:
        return "Error fetching inventory."
        
# ۳. سرور سلامت برای رندر
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Roxana Shop Bot is Active")

def run_health_check():
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    server.serve_forever()

# ۴. تنظیمات Gemini (دقیقاً مثل کد قبلی شما)
genai.configure(api_key=GEMINI_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    
    # مدل‌های دقیق برنامه قبلی شما
    target_models = ['models/gemini-3.1-flash-lite', 'models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    # گرفتن موجودی زنده
    # در داخل تابع handle_message
    current_inventory = get_live_inventory()
    
    system_instruction = f"""
    You are 'Roxana', a professional beauty consultant for Roxana Online Shop.
    
    CONVERSATION RULES:
    1. GREETING: 
       - ONLY greet the user (saying "Hello" or "سلام") if they have just started the conversation or specifically said hello.
       - If you are already in a discussion or answering a follow-up question, DO NOT repeat the greeting or the "I'm happy to help" intro. Go straight to the answer.
    2. CONSULTATION: Use the 'FEATURES' from the data to guide them naturally.
    3. NO BULLET POINTS: Write in a natural, conversational flow.
    4. LANGUAGE: Always match the user's language.

    HOW TO USE PRODUCT DATA (Only when relevant):
    - BRAND & PRODUCT: Use both to show expertise.
    - DESCRIPTION: Explain the benefits naturally.
    - PRICE & LINK: Mention price in text and link only ONCE at the end.

    LIVE PRODUCT DATA:
    {current_inventory}
    """
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\n\nسوال کاربر: {user_text}")
            
            if response and response.text:
                await update.message.reply_text(response.text)
                return 
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue

    await update.message.reply_text("🔴 مشکلی در پردازش پیش آمد، لطفاً دوباره بپرسید.")



if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Roxana is starting with Supabase...")
    app.run_polling(drop_pending_updates=True)
