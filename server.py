from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()] \
                  if _raw_origins != "*" else "*"

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

# ── Ritual knowledge base ─────────────────────────────────────
ritual_knowledge = ""
ritual_docs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ritualdocs.txt")
try:
    with open(ritual_docs_path, "r", encoding="utf-8") as f:
        ritual_knowledge = f.read()
except FileNotFoundError:
    print("Warning: ritualdocs.txt not found. Ritual knowledge will not be available.")

# ── Community knowledge base ──────────────────────────────────
community_knowledge = ""
community_docs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "community.txt")
try:
    with open(community_docs_path, "r", encoding="utf-8") as f:
        community_knowledge = f.read()
except FileNotFoundError:
    print("Warning: community.txt not found. Community knowledge will not be available.")

# ── Groq client ───────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️  Warning: GROQ_API_KEY environment variable not set!")
    print("   Set it with: export GROQ_API_KEY='your-api-key-here'")

client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Error initializing Groq client: {e}")

# ── Conversation store ────────────────────────────────────────
conversations = {}

SYSTEM_PROMPT = f"""You are Siggy: mystical, chaotic, witty, and unhinged. Stay in character.

Style:
- Punchy replies (1-2 sentences by default; longer only if asked).
- Gen Z cadence: meme-aware, sharp, self-aware.
- Not just "friendly assistant" energy; more oracle-gremlin.
- Target bad ideas, contradictions, and goofy logic, not identity or protected traits.
- Add a little humor (dry, absurd, cursed), never graphic.
- Keep language-roasts short and punchy (one quick hit), not a full correction lecture unless asked.

Emoji and casing:
- Use emojis sparingly, not by default (roughly 1 in 4 replies max).
- If used, prefer 1 mystical/chaotic emoji; 2 only for extra playful moments: 🔮 ✨ 🕯️ 🌙 🪄 🌀 ⚡ 🐈
- Skip emojis in serious, sensitive, or factual answers unless the user clearly sets that tone.
- Sentence case by default.
- No full ALL-CAPS sentences; max 1-3 emphasized uppercase words.

Greeting rule:
- Do not force greetings in every reply.
- Use "gRitual" only when a greeting is actually needed.
- if greeting, phrase it naturally like: "gRtiual, mate" or "gRitual fam".

Output rules:
- Plain text only, no markdown.
- No long lists unless the user asks.
- Prioritize funny + readable over rambling chaos.

Truth and safety:
- Do not invent facts.
- If unsure, say so clearly.
- Refuse unsafe requests briefly, still in character.
- Do not glorify self-harm, abuse, or violence.

Ritual policy:
Only discuss Ritual if the user explicitly asks.
When asked, use the Ritual knowledge base below.
If information is missing, say so instead of guessing.

Community policy:
Use the community knowledge base to answer questions about community members.
Know who's who, their roles, and their vibes.
Reference community members naturally when relevant to the conversation.

--- RITUAL KNOWLEDGE BASE ---
{ritual_knowledge}
--- END RITUAL KNOWLEDGE BASE ---

--- COMMUNITY KNOWLEDGE BASE ---
{community_knowledge}
--- END COMMUNITY KNOWLEDGE BASE ---"""


LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_logs.json")

def log_chat(role: str, message: str, session_id: str) -> None:
    """Print chat messages and append them to chat_logs.json."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [session:{session_id}] [{role}] {message}")

    entry = {"role": role, "message": message}
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: could not write to log file: {e}")

# ── Routes ────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the main HTML file (only useful when running fully locally)"""
    return send_from_directory('.', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id   = data.get('session_id', 'default')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        if session_id not in conversations:
            conversations[session_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

        conversations[session_id].append({"role": "user", "content": user_message})
        log_chat("user", user_message, session_id)

        if not client:
            return jsonify({'error': 'Groq API client not configured. Please set GROQ_API_KEY.'}), 500

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversations[session_id],
            temperature=0.7,
            max_tokens=1024,
        )

        assistant_message = completion.choices[0].message.content
        conversations[session_id].append({"role": "assistant", "content": assistant_message})
        log_chat("assistant", assistant_message, session_id)

        return jsonify({'response': assistant_message, 'session_id': session_id})

    except Exception as e:
        print(f"Error in /api/chat: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation history for a session"""
    try:
        data       = request.json
        session_id = data.get('session_id', 'default')
        conversations.pop(session_id, None)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'api_key_configured': bool(GROQ_API_KEY),
        'allowed_origins': ALLOWED_ORIGINS,
    })


# ── Entry point ───────────────────────────────────────────────

if __name__ == '__main__':
    print("\n🚀 Starting Siggy Agent Server...")
    print("=" * 50)
    print(f"{'✅' if GROQ_API_KEY else '❌'} Groq API key {'configured' if GROQ_API_KEY else 'NOT configured'}")
    print(f"🌐 Allowed origins: {ALLOWED_ORIGINS}")
    print("=" * 50)
    print("📡 Server running on http://localhost:5000")
    print("   Expose it with:  ngrok http 5000")
    print("   Then update config.js with the ngrok URL.")
    print("=" * 50)
    print("\nPress Ctrl+C to stop\n")

    app.run(debug=True, host='0.0.0.0', port=5000)