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

# === Load .env ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# === Supabase and OpenAI Setup ===
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

# === Flask App ===
app = Flask(__name__)
CORS(app)

# === Constants ===
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
    contribs = supabase.table("contributions").select("*").eq("member_id", member["id"]).execute().data

    total_paid = sum(c["amount"] for c in contribs)
    months_paid = list(set(c["period"] for c in contribs))

    # Breakdown by month and category
    breakdown = {}
    for c in contribs:
        period = c["period"]
        category = c.get("category", "general")
        breakdown.setdefault(period, {}).setdefault(category, 0)
        breakdown[period][category] += float(c["amount"])

    return member, {
        "name": member["name"],
        "total_paid": total_paid,
        "months_paid": months_paid,
        "breakdown": breakdown
    }

def extract_category_and_month(message):
    categories = ["welfare", "emergency", "savings"]
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    category = next((cat for cat in categories if cat in message.lower()), None)
    month = next((m for m in months if m.lower() in message.lower()), None)

    if month and str(datetime.now().year) not in message:
        month += f" {datetime.now().year}"

    return category, month

def ask_deepseek(message, phone):
    member, summary = fetch_user_summary(phone)
    if not summary:
        return "⚠️ Couldn’t fetch your records."

    category, month = extract_category_and_month(message)
    breakdown = summary["breakdown"]

    if category and month:
        amount = breakdown.get(month, {}).get(category, 0)
        return f"💰 You paid KES {int(amount)} for *{category.title()}* in *{month}*."

    elif category:
        total = sum(breakdown[p].get(category, 0) for p in breakdown)
        return f"📊 You’ve paid a total of KES {int(total)} for *{category.title()}* so far."

    elif month:
        entries = breakdown.get(month, {})
        if not entries:
            return f"❌ No contributions recorded for *{month}*."
        lines = [f"{k.title()}: KES {int(v)}" for k, v in entries.items()]
        return f"📅 Contributions for *{month}*:\n" + "\n".join(lines)

    return (
        f"👤 Name: {summary['name']}\n"
        f"💰 Total Paid: KES {int(summary['total_paid'])}\n"
        f"🗓️ Months Paid: {', '.join(summary['months_paid'])}"
    )

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
    name = data.get("name", "").strip().title()
    phone = data.get("phone") or data.get("from")
    message = data.get("message", "").strip()

    if not phone:
        return jsonify({"reply": "⚠️ Missing phone number."}), 400

    if name:
        res = supabase.table("members").select("*").eq("phone", phone).execute()
        if not res.data:
            supabase.table("members").insert({"name": name, "phone": phone}).execute()
            return jsonify({"reply": f"🎉 {name}, you’ve been registered!"})
        else:
            return jsonify({"reply": f"✅ You're already registered, {res.data[0]['name']}!"})

    if not message:
        return jsonify({"reply": "⚠️ Please provide a message or name."}), 400

    lower_msg = message.lower()

    if re.search(r"\bpaid\b|\bsent\b|\btuma\b|\bi have paid\b", lower_msg):
        reply = handle_contribution(phone, message)
    elif re.search(r"\bbalance\b|\bowe\b|\bhave i paid\b|nimeshalipa", lower_msg):
        reply = handle_balance(phone)
    elif classify_user(phone) == "admin":
        reply = ask_deepseek(message, phone)
    else:
        reply = handle_message(phone, message)

    return jsonify({"reply": reply})

@app.route("/send-reminders", methods=["POST"])
def trigger_reminders():
    send_weekly_reminders()
    return jsonify({"status": "success", "message": "Reminders sent."})

# === Start ===
if __name__ == "__main__":
    print("✅ Chama Bot is running...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
