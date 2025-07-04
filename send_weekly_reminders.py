import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
from twilio_helpers import send_whatsapp_message

# Load env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_weekly_reminders():
    period = datetime.now().strftime("%B %Y")
    print(f"📣 Sending reminders for {period}...")

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

        if not contribs:
            msg = f"📅 Hello {name}, it’s Friday! Please remember to contribute to the chama for {period}. Thanks!"
            send_whatsapp_message(phone, msg)

if __name__ == "__main__":
    send_weekly_reminders()
