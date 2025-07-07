import os
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
import openai
from twilio_helpers import send_whatsapp_message
from send_weekly_reminders import send_weekly_reminders

# === Load environment variables ===
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

# === Flask App Setup ===
app = Flask(__name__)
CORS(app)

# === Constants ===
EXPECTED_CONTRIBUTIONS = {
    "welfare": 500,
    "emergency": 1000,
    "savings": 1500
}

# === Helper Functions ===

def classify_user(phone):
    res = supabase.table("admins").select("*").eq("phone", phone).execute()
    return "admin" if res.data else "member"

def fetch_user_summary(phone):
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        return None, None
    member = res.data[0]
    contribs = supabase.table("contributions").select("*").eq("member_id", member["id"]).execute().data
    total_paid = sum(c["amount"] for c in contribs)
    months_paid = list(set(c["period"] for c in contribs))
    return member, {
        "name": member["name"],
        "total_paid": total_paid,
        "months_paid": months_paid,
        "records": contribs
    }

def ask_deepseek(message, phone):
    member, summary = fetch_user_summary(phone)
    role = classify_user(phone)

    history = [
        {"role": "system", "content": f"""
You are a helpful assistant for a savings group (Chama).
This user is a {role}.
Name: {summary['name'] if summary else 'Unknown'}
Total Paid: {summary['total_paid']} KES
Months Paid: {', '.join(summary['months_paid']) if summary else 'None'}
"""},
        {"role": "user", "content": message}
    ]

    if summary:
        # Include past contributions in the context for smarter answers
        records = summary["records"]
        history.insert(1, {
            "role": "system",
            "content": f"Here are the user’s past payments:\n" +
                       "\n".join([f"- {r['period']} ({r['category']}): KES {int(r['amount'])}" for r in records])
        })

    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=history
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI Error: {e}"

def extract_contribution_data(msg):
    match = re.search(r"(\d{2,6})(?:\s*for\s*(\w+))?", msg.lower())
    if match:
        return float(match.group(1)), match.group(2) if match.group(2) else "general"
    return None, None

def handle_contribution(phone, message):
    amount, category = extract_contribution_data(message)
    if not amount:
        return "⚠️ I couldn't understand that. Try: 'I paid 500 for welfare'."
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        return "⚠️ You're not registered. Please send your full name."
    member = res.data[0]
    period = datetime.now().strftime("%B %Y")
    supabase.table("contributions").insert({
        "member_id": member["id"],
        "amount": amount,
        "period": period,
        "category": category
    }).execute()
    return f"✅ Got KES {int(amount)} for {category}. Thanks {member['name']}!"

def handle_balance(phone):
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        return "⚠️ You're not registered."
    member = res.data[0]
    period = datetime.now().strftime("%B %Y")
    contribs = supabase.table("contributions").select("amount, category") \
        .eq("member_id", member["id"]).eq("period", period).execute()
    totals = {}
    for c in contribs.data:
        cat = c["category"] if c["category"] else "general"
        totals[cat] = totals.get(cat, 0) + float(c["amount"])
    lines = []
    for cat, expected in EXPECTED_CONTRIBUTIONS.items():
        paid = totals.get(cat, 0)
        balance = expected - paid
        if balance <= 0:
            lines.append(f"✅ {cat.title()}: Fully paid (KES {int(paid)})")
        else:
            lines.append(f"⚠️ {cat.title()}: You owe KES {int(balance)} (Paid: {int(paid)})")
    return f"📊 *Your balance for {period}:*\n" + "\n".join(lines)

# === Routes ===

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    phone = data.get("phone") or data.get("from")
    message = data.get("message", "").strip()
    name = data.get("name", "").strip().title()

    if not phone:
        return jsonify({"reply": "⚠️ Missing phone number."}), 400

    res = supabase.table("members").select("*").eq("phone", phone).execute()
    is_registered = bool(res.data)

    # 1. Register
    if not is_registered and name:
        supabase.table("members").insert({"name": name, "phone": phone}).execute()
        return jsonify({"reply": f"🎉 {name}, you’ve been registered!"})
    elif not is_registered:
        return jsonify({"reply": "👋 Please reply with your full name to join the chama."})

    # 2. Handle message
    if not message:
        return jsonify({"reply": "⚠️ Empty message."})

    lower_msg = message.lower()

    if re.search(r"\bpaid\b|\bsent\b|\btuma\b|\bi have paid\b", lower_msg):
        reply = handle_contribution(phone, message)
    elif re.search(r"\bbalance\b|\bowe\b|\bhave i paid\b|nimeshalipa", lower_msg):
        reply = handle_balance(phone)
    else:
        reply = ask_deepseek(message, phone)

    return jsonify({"reply": reply})

@app.route("/send-reminders", methods=["POST"])
def trigger_reminders():
    send_weekly_reminders()
    return jsonify({"status": "success", "message": "Reminders sent."})

if __name__ == "__main__":
    print("✅ Chama Bot is running...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
