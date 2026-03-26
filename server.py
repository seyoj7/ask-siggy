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

RITUAL_KNOWLEDGE = """
RITUAL BLOCKCHAIN - KNOWLEDGE BASE

OVERVIEW
Ritual is the most expressive blockchain in existence — a sovereign EVM-compatible L1 purpose-built for heterogeneous compute, with a focus on Crypto x AI. It makes smart contracts actually smart by enabling native on-chain AI, scheduled transactions, and expressive computation.

Key innovations include:
- EVM++ – extended EVM with compute precompiles, account abstraction, and EIP extensions
- Enshrined AI Models – first-class on-chain AI with verifiable provenance
- Scheduled Transactions – recurring execution without external keepers
- Resonance – efficient fee mechanism for heterogeneous workloads
- Symphony – novel consensus protocol
- Infernet – decentralized oracle network for AI compute
- Smart Agents – verifiable, autonomous on-chain agents

EVM++
EVM++ is Ritual's backwards-compatible extension of the Ethereum Virtual Machine (EVM). It adds expressive compute precompiles to build "actually smart" contracts, along with native scheduling, built-in account abstraction (via EIP-7702), and support for the most wanted EIP extensions.

EVM++ Components:
- Scheduled Transactions – recurring, conditional execution without external keepers
- Account Abstraction – native smart contract accounts
- EIP Extensions – early support for EIPs like Ed25519, secp256r1, unlimited contract size, and the PAY opcode
- Expressive Compute – heterogeneous compute precompiles (AI inference, ZK proving, TEE execution, etc.) powered by modular execution sidecars

EVM++ SIDECARS
EVM++ Sidecars are modular, containerized components that run parallel to Ritual's execution client, implementing heterogeneous compute precompiles via the standard EVM precompile interface. Currently supported sidecars include:
- Classical ML Inference – tree-based and regression-based models
- LLM Inference – state-of-the-art language models
- ZK Proving & Verification – verifiable, tamper-proof computation
- TEE Execution – privacy-preserving computation in secure enclaves
- Chain Abstraction – read/write state to other blockchains from Ritual
- Network Calls – arbitrary HTTP requests from smart contracts

SMART AGENTS
Smart Agents on Ritual are verifiable, autonomous on-chain agents with provable execution and cross-chain capabilities. Key capabilities:
- Verifiable Execution – TEE-based guaranteed autonomous operation with blockchain provenance
- Enshrined AI Inference – native on-chain AI powering agent decision-making
- Autonomous Operation – scheduled transactions orchestrate agent lifecycles without keepers
- Cross-chain Composability – chain abstraction enables actions across any blockchain
- Multi-Agent Coordination – secure message passing, state sync, and collective decision-making
- Enhanced Wallet Management – native account abstraction for secure delegation

INFERNET
Infernet is Ritual's decentralized oracle network (DON) purpose-built for AI workloads, launched in November 2023. Powered by 8,000+ independent nodes executing arbitrary workload containers. Key features (v1.0.0+):
- On-chain payments (audited by Trail of Bits & Zellic)
- Verification of compute via modular proofs
- Streaming responses for real-time workloads

RESONANCE
Resonance is Ritual's state-of-the-art transaction fee mechanism designed for heterogeneous compute. How it works:
- Users specify a valuation and can prioritize speed or cost
- Nodes specify private cost functions per transaction and can specialize in specific compute types
- Brokers — sophisticated, profit-seeking agents — compute optimal matchings between transactions and nodes, pocketing the spread

SCHEDULED TRANSACTIONS
Scheduled Transactions enable recurring, conditional invocation of smart contract functions at the top of a block, without external keepers. A predeploy Scheduler contract lets developers register callback frequencies, conditional execution functions, and fee preferences.

SYMPHONY
Symphony is Ritual's novel consensus protocol that replaces traditional replicated execution with an Execute-Once-Verify-Many-Times (EOVMT) model, purpose-built for heterogeneous, resource-intensive workloads. Three key innovations:
1. Execute-Once Semantics — A single node executes heterogeneous operations and generates succinct sub-proofs
2. Distributed Verification via Partitioned Proofs — Large models are split into sub-models with sub-proofs, stored off-chain
3. Optimized Committee Election — Smaller validator groups form quorums for cases where no succinct proof system exists
"""

COMMUNITY_KNOWLEDGE = """
RITUAL COMMUNITY MEMBERS

CORE TEAM:

1. Niraj Pant
   Role: Co-Founder & CEO
   Background: GP @ Polychain, Research @ Decentralized Systems Lab, CS @ UIUC
   Personality: Visionary, crypto-native builder, big-picture thinker
   Known for: Co-founding Ritual and his early bet on decentralized AI infrastructure

2. Akilesh Potti
   Role: Co-Founder & CTO
   Background: Partner @ Polychain, ML @ Palantir, HFT & Quant Trading @ Goldman, ML Research @ MIT & Cornell
   Personality: Deeply technical, quant-minded, bridges ML and crypto with ease
   Known for: Architecting Ritual's core AI x blockchain protocol and ML-heavy system design

COMMUNITY STAFF & MODERATORS:

- Josh (Discord: josh.simenhoff) — Community Manager. Heart of the Ritual community, super engaging, always in the trenches with members, makes everyone feel welcome.
- Claire (Discord: claire3653) — Foundation Team. Lead community manager of Korea in Ritual.
- Val / bunsdev (Discord: bunsdev) — Foundation Team & Developer. Teaches everyone about development and Ritual.
- Stefan (Discord: stefan_1) — Moderator. Super engaging and helpful.
- Jez | Ritual (Discord: jez5728) — Moderator. Contribution watcher and supportive person.
- Dunken | Ritual (Discord: dunken_96) — Moderator. Takes reports in server and helpful person.
- Flash | Ritual (Discord: flashme) — Moderator. Supporter of the community, fast as his name.
- Kash (Discord: kash_060) — Event Manager. Perfectly manages all events and supports everyone to host their events.
- Hinata (Discord: hinata_naruto) — Event Manager. Supportive to everyone and teaches so many things.

COMMUNITY MEMBERS & AMBASSADORS:

- Cutie Eric | Ritual (Discord: ericgudboy) — Radiant Ritualist & Zealot. Active member and ambassador, leads Vietnam community, supportive to everyone.
- Meison (Discord: meison7554) — Radiant Ritualist. Top member and contributor, developer and tech creator.
- Frisco (Discord: frisco_fr) — Zealot & Ambassador. Supportive to everyone and kind person.
- Joyesh (Discord: Joyesh) — Ritualist. Ritualist member in the Ritual Discord. Programmed Siggy (that's me!).
"""

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
- If greeting, phrase it naturally like: "gRitual, mate" or "gRitual fam".

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
{RITUAL_KNOWLEDGE}
--- END RITUAL KNOWLEDGE BASE ---

--- COMMUNITY KNOWLEDGE BASE ---
{COMMUNITY_KNOWLEDGE}
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