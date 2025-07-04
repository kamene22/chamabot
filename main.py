import os
import re
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import openai
from twilio_helpers import send_whatsapp_message

# ----------------------- Config -----------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Supabase and OpenAI clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

app = Flask(__name__)

EXPECTED_CONTRIBUTIONS = {
    "welfare": 500,
    "emergency": 1000,
    "savings": 1500
}

# ----------------------- Helpers -----------------------

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
    }

def ask_deepseek(message, phone):
    member, summary = fetch_user_summary(phone)
    role = classify_user(phone)
    context = f"""
You are a helpful Chama bot. This user is a {role}.
Name: {summary['name'] if summary else 'Unknown'}
Total Paid: KES {summary['total_paid'] if summary else 0}
Months Paid: {', '.join(summary['months_paid']) if summary else 'None'}
"""

    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": context},
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

# ----------------------- Message Handlers -----------------------

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

def handle_message(phone, message):
    res = supabase.table("members").select("*").eq("phone", phone).execute()
    if not res.data:
        if " " in message:
            name = message.strip().title()
            supabase.table("members").insert({"name": name, "phone": phone}).execute()
            return f"🎉 {name}, you’ve been registered!"
        else:
            return "👋 Please reply with your full name to join the chama."
    return f"✅ You're already registered, {res.data[0]['name']}!"

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

# ----------------------- Flask Webhook -----------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", "").strip()
    phone = data.get("phone") or data.get("from")

    if not message or not phone:
        return jsonify({"reply": "⚠️ Invalid message format"}), 400

    if re.search(r"\bpaid\b|\bsent\b|\btuma\b", message.lower()):
        reply = handle_contribution(phone, message)
    elif re.search(r"\bbalance\b|\bowe\b|\bhave i paid\b", message.lower()):
        reply = handle_balance(phone)
    elif classify_user(phone) == "admin":
        reply = ask_deepseek(message, phone)
    else:
        reply = handle_message(phone, message)

    return jsonify({"reply": reply})

# ----------------------- Reminder Logic -----------------------

def send_weekly_reminders():
    print("📣 Sending WhatsApp reminders...")
    period = datetime.now().strftime("%B %Y")
    members = supabase.table("members").select("*").execute().data

    for member in members:
        contribs = supabase.table("contributions").select("*") \
            .eq("member_id", member["id"]) \
            .eq("period", period).execute().data

        totals = {}
        for c in contribs:
            cat = c["category"] if c["category"] else "general"
            totals[cat] = totals.get(cat, 0) + float(c["amount"])

        unpaid = []
        for category, expected in EXPECTED_CONTRIBUTIONS.items():
            paid = totals.get(category, 0)
            if paid < expected:
                unpaid.append(f"{category.title()} (KES {int(expected - paid)})")

        if unpaid:
            msg = f"📤 Hello {member['name']}, you still owe for {period}: {', '.join(unpaid)}. Please contribute today!"
            send_whatsapp_message(member["phone"], msg)

# ----------------------- Main -----------------------

if __name__ == "__main__":
    print("✅ Chama Bot is running...")
    # send_weekly_reminders()  # Uncomment to run it manually
    app.run(port=5000)
