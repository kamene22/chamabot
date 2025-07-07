import os
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
from twilio_helpers import send_whatsapp_message
from send_weekly_reminders import send_weekly_reminders

# === Load .env ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# === Setup ===
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"  # ✅ Make sure this matches OpenRouter
)

app = Flask(__name__)
CORS(app)

EXPECTED_CONTRIBUTIONS = {
    "welfare": 500,
    "emergency": 1000,
    "savings": 1500
}

# === Helpers ===

def classify_user(phone):
    res = supabase.table("admins").select("*").eq("phone", phone).execute()
    return "admin" if res.data else "member"

def fetch_user_summary(phone):
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        return None, None
    member = res.data[0]

    contribs = supabase.table("contributions") \
        .select("*") \
        .eq("member_id", member["id"]) \
        .execute().data

    summary = {
        "name": member["name"],
        "total_paid": sum(c["amount"] for c in contribs),
        "months_paid": list(set(c["period"] for c in contribs)),
        "records": contribs
    }
    return member, summary

def ask_ai(message, phone):
    member, summary = fetch_user_summary(phone)
    role = classify_user(phone)

    if not summary:
        return "⚠️ You haven't made any contributions yet."

    context = f"""
You are a helpful chatbot for a community savings group (Chama).
This user is a {role}.
Name: {summary['name']}
Total Paid: KES {summary['total_paid']}
Months Paid: {', '.join(summary['months_paid'])}
"""

    record_lines = [
        f"- {r['period']} | {r['category'].title()}: KES {int(r['amount'])}"
        for r in summary["records"]
    ]

    try:
        response = client.chat.completions.create(
            model="mistralai/mixtral-8x7b",  # ✅ Replace with any valid model
            messages=[
                {"role": "system", "content": context + "\n\n" + "\n".join(record_lines)},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI Error: {e}"

def extract_contribution_data(msg):
    match = re.search(r"(\d{2,6})(?:\s*for\s*(\w+))?", msg.lower())
    if match:
        return float(match.group(1)), match.group(2) if match.group(2) else "general"
    return None, None

# === Handlers ===

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

    contribs = supabase.table("contributions") \
        .select("amount, category") \
        .eq("member_id", member["id"]) \
        .eq("period", period).execute()

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

def handle_message(phone, message, name=None):
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        if name or " " in message:
            member_name = name or message.strip().title()
            supabase.table("members").insert({"name": member_name, "phone": phone}).execute()
            return f"🎉 {member_name}, you’ve been registered!"
        else:
            return "👋 Please reply with your full name to join the chama."

    if classify_user(phone) == "admin":
        return ask_ai(message, phone)

    return "✅ You're already registered, type 'Check Balance' or 'I paid 500 for welfare'."

# === Routes ===

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    phone = data.get("phone") or data.get("from")
    message = data.get("message", "").strip()
    name = data.get("name", "").strip().title() if data.get("name") else None

    if not phone:
        return jsonify({"reply": "⚠️ Missing phone number."}), 400

    if name and not message:
        return jsonify({"reply": handle_message(phone, "", name)})

    lower_msg = message.lower()

    if re.search(r"\bpaid\b|\bsent\b|\btuma\b", lower_msg):
        reply = handle_contribution(phone, message)
    elif re.search(r"\bbalance\b|\bowe\b|\bhave i paid\b|nimeshalipa", lower_msg):
        reply = handle_balance(phone)
    elif classify_user(phone) == "admin":
        reply = ask_ai(message, phone)
    else:
        reply = handle_message(phone, message)

    return jsonify({"reply": reply})

@app.route("/send-reminders", methods=["POST"])
def trigger_reminders():
    send_weekly_reminders()
    return jsonify({"status": "success", "message": "Reminders sent."})

# === Run ===
if __name__ == "__main__":
    print("✅ Chama Bot is running...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
