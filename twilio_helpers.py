# === twilio_helpers.py ===
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

def send_whatsapp_message(phone, message):
    try:
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
            to=f"whatsapp:{phone}"
        )
        print(f"✅ Sent to {phone}: {message}")
    except Exception as e:
        print(f"⚠️ Error sending to {phone}: {e}")


# === send_weekly_reminders.py ===
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
from twilio_helpers import send_whatsapp_message

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

EXPECTED_CONTRIBUTIONS = {
    "welfare": 500,
    "emergency": 1000,
    "savings": 1500
}

def send_weekly_reminders():
    period = datetime.now().strftime("%B %Y")
    print(f"\n📣 Sending reminders for {period}...")

    members = supabase.table("members").select("*").execute().data
    for member in members:
        member_id = member["id"]
        phone = member["phone"]
        name = member["name"]

        contribs = supabase.table("contributions")\
            .select("*")\
            .eq("member_id", member_id)\
            .eq("period", period)\
            .execute().data

        totals = {}
        for c in contribs:
            cat = c.get("category", "general")
            totals[cat] = totals.get(cat, 0) + float(c.get("amount", 0))

        unpaid = []
        for cat, expected in EXPECTED_CONTRIBUTIONS.items():
            paid = totals.get(cat, 0)
            if paid < expected:
                unpaid.append(f"{cat.title()} (KES {int(expected - paid)})")

        if unpaid:
            msg = f"📤 Hello {name}, you still owe for {period}: {', '.join(unpaid)}. Please contribute today!"
            send_whatsapp_message(phone, msg)

if __name__ == "__main__":
    send_weekly_reminders()


