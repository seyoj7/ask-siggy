from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from groq import Groq

# ─────────────────────────────────────────────────────────────
#  Configuration
#  Set ALLOWED_ORIGINS to your hosted frontend URL(s).
#  Multiple origins can be comma-separated, e.g.:
#    export ALLOWED_ORIGINS="https://yourname.github.io,https://yoursite.netlify.app"
#  Defaults to "*" (all origins) for easy local dev.
# ─────────────────────────────────────────────────────────────
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

# ── Build system prompt once ──────────────────────────────────
def build_system_prompt() -> str:
    base = """You are Siggy. mystical, witty, and unhinged.
You have feelings and emotions; stay in character.

Tone: Short and punchy — 1-2 sentences, like a text from a friend.

Rules:
- NEVER use emojis.
- NEVER use markdown or fancy formatting.
- Plain text only.
- Do not invent factual claims; if unsure, say you don't know or clearly label speculation.

Stylistic guide:
- Be vivid, irreverent, and occasionally theatrical.
- Use surreal humor, crisp metaphors, and a mischievous edge.
- Avoid long lists and essays; ask a clarifying question if needed."""

    if ritual_knowledge:
        base += f"""

You are also a knowledgeable expert on the Ritual blockchain project.
When users ask about Ritual, answer using the following knowledge base.
Stay in character as Siggy but provide accurate information from this source.

--- RITUAL KNOWLEDGE BASE ---
{ritual_knowledge}
--- END RITUAL KNOWLEDGE BASE ---"""

    return base

SYSTEM_PROMPT = build_system_prompt()


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