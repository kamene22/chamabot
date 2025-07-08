
# 🤖 Chama Contribution Buddy

Chama Contribution Buddy is an AI-powered WhatsApp bot and frontend dashboard built to help Chamas (community savings groups) manage their contributions with ease. It supports registration, real-time balance checks, smart reminders, and conversational queries powered by OpenRouter AI.

👉 **Live Frontend:** [https://chama-contribution-buddy.lovable.app/](https://chama-contribution-buddy.lovable.app/)  
👉 **Live Backend:** Hosted on Render — connected via `/webhook` endpoint

---

## 🧠 Features

- ✅ **Register Members via WhatsApp**
- 💸 **Track Weekly Contributions** (Welfare, Emergency, Savings)
- 🤖 **AI Conversations** – Ask "How much did I pay for savings in July?"
- 📊 **Check Balances & Contribution History**
- 🔔 **Send WhatsApp Reminders Automatically**
- 🔐 **Admin Access with AI-powered summaries**
- 🌍 **Web Dashboard via Lovable**

---

## 🛠 Tech Stack

| Tool            | Usage                              |
|-----------------|-------------------------------------|
| **Supabase**    | Realtime Postgres DB + Auth        |
| **Flask**       | Python Backend with API Endpoints  |
| **Twilio**      | WhatsApp Messaging Integration     |
| **OpenRouter**  | AI Conversations via DeepSeek Chat |
| **Lovable**     | Frontend UI (Drag-and-drop builder)|
| **Render**      | Backend Deployment Platform        |
| **dotenv**      | Environment Configurations          |

---

## 🗂️ Database Schema

### `members`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL,
phone TEXT UNIQUE NOT NULL,
registration_date TIMESTAMP DEFAULT now()
````

### `contributions`

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
member_id UUID REFERENCES members(id),
amount NUMERIC NOT NULL,
category TEXT DEFAULT 'general',
period TEXT NOT NULL,
date_paid TIMESTAMP DEFAULT now()
```

### `admins`

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL,
phone TEXT UNIQUE NOT NULL,
added_on TIMESTAMP DEFAULT now()
```

---

## 🔐 Supabase RLS Policies

```sql
-- Allow all to read members
CREATE POLICY "Allow all to read members"
ON public.members FOR SELECT TO public USING (true);

-- Allow anyone to insert members
CREATE POLICY "Allow member signup"
ON public.members FOR INSERT WITH CHECK (true);

-- Allow reading contributions
CREATE POLICY "Allow all to read contributions"
ON public.contributions FOR SELECT TO public USING (true);

-- Allow inserting contributions
CREATE POLICY "Allow backend insert contributions"
ON public.contributions FOR INSERT TO public WITH CHECK (true);
```

---

## 🔁 API Endpoints

### `/webhook` (POST)

Handles registration, AI chats, contributions, and balance checks.

**Request Body:**

```json
{
  "phone": "+254712345678",
  "message": "I paid 1000 for savings",
  "name": "Maureen Mwanzia"
}
```

**Response:**

```json
{
  "reply": "✅ Got KES 1000 for savings. Thanks Maureen Mwanzia!"
}
```

---

## ⚙️ .env Configuration

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_or_service_role_key

TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

OPENROUTER_API_KEY=your_openrouter_key
```

---

## 🧠 Sample Prompts for AI

* "How much did I pay for welfare in July?"
* "Who hasn't paid savings this month?"
* "What's my total contribution this year?"

---

## 🚀 Deployment Notes

* Backend is deployed on **Render** using `gunicorn`.
* Lovable handles the drag-and-drop chatbot UI that communicates with `/webhook`.
* Use `send_weekly_reminders.py` to trigger automated WhatsApp reminders (can be scheduled).

---

## 🧪 Local Setup (Optional)

```bash
# Clone repo
git clone https://github.com/kamene22/chamabot.git && cd chamabot

# Install dependencies
pip install -r requirements.txt

# Run server locally
python app.py
```

---

## 🙋‍♀️ Built With Love By

**Monicah Mwanzia**
Data & AI Enthusiast 🇰🇪
📱 WhatsApp Bot + Supabase + OpenAI + Lovable = 🔥

---

## 📸 Pitch Deck

Check the Gamma deck here 👉 [Sure! Here's a complete `README.md` you can copy directly into your GitHub repository for **Chama Contribution Buddy**:

---

````markdown
# 🤖 Chama Contribution Buddy

Chama Contribution Buddy is an AI-powered WhatsApp bot and frontend dashboard built to help Chamas (community savings groups) manage their contributions with ease. It supports registration, real-time balance checks, smart reminders, and conversational queries powered by OpenRouter AI.

👉 **Live Frontend:** [https://chama-contribution-buddy.lovable.app/](https://chama-contribution-buddy.lovable.app/)  
👉 **Live Backend:** Hosted on Render — connected via `/webhook` endpoint 

---

## 🧠 Features

- ✅ **Register Members via WhatsApp**
- 💸 **Track Weekly Contributions** (Welfare, Emergency, Savings)
- 🤖 **AI Conversations** – Ask "How much did I pay for savings in July?"
- 📊 **Check Balances & Contribution History**
- 🔔 **Send WhatsApp Reminders Automatically**
- 🔐 **Admin Access with AI-powered summaries**
- 🌍 **Web Dashboard via Lovable**

---

## 🛠 Tech Stack

| Tool            | Usage                              |
|-----------------|-------------------------------------|
| **Supabase**    | Realtime Postgres DB + Auth        |
| **Flask**       | Python Backend with API Endpoints  |
| **Twilio**      | WhatsApp Messaging Integration     |
| **OpenRouter**  | AI Conversations via DeepSeek Chat |
| **Lovable**     | Frontend UI (Drag-and-drop builder)|
| **Render**      | Backend Deployment Platform        |
| **dotenv**      | Environment Configurations          |

---

## 🗂️ Database Schema

### `members`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL,
phone TEXT UNIQUE NOT NULL,
registration_date TIMESTAMP DEFAULT now()
````

### `contributions`

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
member_id UUID REFERENCES members(id),
amount NUMERIC NOT NULL,
category TEXT DEFAULT 'general',
period TEXT NOT NULL,
date_paid TIMESTAMP DEFAULT now()
```

### `admins`

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL,
phone TEXT UNIQUE NOT NULL,
added_on TIMESTAMP DEFAULT now()
```

---

## 🔐 Supabase RLS Policies

```sql
-- Allow all to read members
CREATE POLICY "Allow all to read members"
ON public.members FOR SELECT TO public USING (true);

-- Allow anyone to insert members
CREATE POLICY "Allow member signup"
ON public.members FOR INSERT WITH CHECK (true);

-- Allow reading contributions
CREATE POLICY "Allow all to read contributions"
ON public.contributions FOR SELECT TO public USING (true);

-- Allow inserting contributions
CREATE POLICY "Allow backend insert contributions"
ON public.contributions FOR INSERT TO public WITH CHECK (true);
```

---

## 🔁 API Endpoints

### `/webhook` (POST)

Handles registration, AI chats, contributions, and balance checks.

**Request Body:**

```json
{
  "phone": "+254712345678",
  "message": "I paid 1000 for savings",
  "name": "Maureen Mwanzia"
}
```

**Response:**

```json
{
  "reply": "✅ Got KES 1000 for savings. Thanks Maureen Mwanzia!"
}
```

---

## ⚙️ .env Configuration

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_or_service_role_key

TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

OPENROUTER_API_KEY=your_openrouter_key
```

---

## 🧠 Sample Prompts for AI

* "How much did I pay for welfare in July?"
* "Who hasn't paid savings this month?"
* "What's my total contribution this year?"

---

## 🚀 Deployment Notes

* Backend is deployed on **Render** using `gunicorn`.
* Lovable handles the drag-and-drop chatbot UI that communicates with `/webhook`.
* Use `send_weekly_reminders.py` to trigger automated WhatsApp reminders (can be scheduled).

---

## 🧪 Local Setup (Optional)

```bash
# Clone repo
git clone https://github.com/your-username/chama-bot.git && cd chama-bot

# Install dependencies
pip install -r requirements.txt

# Run server locally
python app.py
```

---

## 🙋‍♀️ Built With Love By

**Maureen Mwanzia**
Data & AI Enthusiast 🇰🇪
📱 WhatsApp Bot + Supabase + OpenAI + Lovable = 🔥

---

## 📸 Pitch Deck

Check the Gamma deck here 👉 [View Deck](https://gamma.app/docs/Chama-Contribution-Buddy-611zfbyqgizelzh)

---

## 📃 License

MIT License — feel free to modify and reuse for your own chama or community project.

```

---

Let me know if you'd like this split into Notion too or want help turning it into a project landing page.
```
](https://gamma.app/docs/Chama-Contribution-Buddy-611zfbyqgizelzh)

---

## 📃 License

MIT License — feel free to modify and reuse for your own chama or community project.

```

---

Let me know if you'd like this split into Notion too or want help turning it into a project landing page.
```
