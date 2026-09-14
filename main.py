import json
import os
import threading
import uuid
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

from character_loader import CharacterLoader
from memory_manager import MemoryManager
from llm_client import LLMClient
from voicevox_client import VoicevoxClient
from openai_tts_client import OpenAICompatibleTTSClient

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
config = {}
character_data = {}
memory_manager = None
llm_client = None
tts_client = None
current_session_id = None
conversation_history = []
turn_counter = 0

def load_config():
    global config
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Handle backward compatibility for voicevox_url
    if "tts" not in config.get("providers", {}):
        if "providers" not in config:
            config["providers"] = {}
        config["providers"]["tts"] = {
            "type": "voicevox",
            "voicevox_url": config.get("voicevox_url", "http://localhost:50021")
        }

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def get_tts_client(config):
    tts_config = config.get("providers", {}).get("tts", {})
    provider_type = tts_config.get("type", "voicevox")

    if provider_type == "voicevox":
        voicevox_url = tts_config.get("voicevox_url") or config.get("voicevox_url", "http://localhost:50021")
        return VoicevoxClient(voicevox_url)
    elif provider_type in ["dashscope", "openai_compatible"]:
        base_url = tts_config.get("base_url")
        api_key = tts_config.get("api_key")
        model_name = tts_config.get("model_name")
        voice = tts_config.get("voice")
        return OpenAICompatibleTTSClient(base_url, api_key, model_name, voice)
    else:
        # Fallback to voicevox
        return VoicevoxClient(config.get("voicevox_url", "http://localhost:50021"))

def initialize_system(session_id=None):
    global character_data, memory_manager, llm_client, tts_client, current_session_id, conversation_history, turn_counter

    load_config()

    char_loader = CharacterLoader()
    character_data = char_loader.load_character(config['active_character'])

    memory_manager = MemoryManager(character_data['path'], config['embedding_model'])

    llm_client = LLMClient(config['providers'])
    tts_client = get_tts_client(config)

    # Session handling
    turn_counter = 0
    if session_id:
        current_session_id = session_id
        session_file = os.path.join("conversations", f"{current_session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, "r", encoding="utf-8") as f:
                conversation_history = json.load(f)
                turn_counter = len([msg for msg in conversation_history if msg["role"] == "user"])
        else:
            conversation_history = []
    else:
        current_session_id = str(uuid.uuid4())
        conversation_history = []

def save_session():
    if not conversation_history:
        return
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        os.makedirs(conversations_dir)
    session_file = os.path.join(conversations_dir, f"{current_session_id}.json")
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(conversation_history, f, indent=4, ensure_ascii=False)

def build_system_prompt(user_input):
    # 1. Base Persona & Lore
    prompt = f"{character_data['persona']}"
    prompt += f"Latar Belakang / Lore:\n{character_data['lore']}\n\n"

    # 2. Mood / State
    temp_state = memory_manager.get_temporary_state()
    if temp_state.get('mood'):
        prompt += f"Mood Anda saat ini: {temp_state['mood']}\n\n"

    # 3. Relevant Memories
    memories = memory_manager.get_relevant_memories(user_input, top_k=5)
    retrieved_memories_debug = []
    if memories:
        prompt += "Memori/Fakta yang relevan:\n"
        for m in memories:
            text = m['content'].get('text', str(m['content']))
            prompt += f"- [{m['category']}] {text}\n"
            retrieved_memories_debug.append(f"[{m['category']}] {text}")
        prompt += "\n"

    prompt += "Instruksi Khusus:\n"
    prompt += "- Jawab selalu dalam Bahasa Indonesia.\n"
    prompt += "- Pisahkan narasi/aksi menggunakan tanda bintang (*) atau kurung ().\n"
    prompt += "- Pastikan dialog yang diucapkan langsung diapit tanda kutip ganda (\").\n"
    prompt += "- Sisipkan [MOOD: <mood_anda>] di bagian paling akhir respons untuk mengindikasikan mood Anda saat ini (contoh: [MOOD: senang], [MOOD: marah]).\n"
    prompt += "- Jangan keluar dari karakter.\n"

    return prompt, retrieved_memories_debug

def extract_mood_from_response(response_text):
    import re
    match = re.search(r'\[MOOD:\s*(.*?)\]', response_text, re.IGNORECASE)
    if match:
        mood = match.group(1).strip()
        # Hapus tag mood dari teks respons agar tidak ditampilkan di UI
        clean_text = re.sub(r'\[MOOD:\s*.*?\]', '', response_text, flags=re.IGNORECASE).strip()
        return mood, clean_text
    return None, response_text

def perform_memory_extraction(log_segment):
    print("Starting memory extraction...")
    log_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in log_segment])
    extracted = llm_client.extract_memory(log_text)

    changes_made = False
    if extracted:
        for category in ['user', 'relationship', 'events', 'world']:
            if category in extracted and extracted[category]:
                for item in extracted[category]:
                    if memory_manager.add_memory(category, item):
                        print(f"Added new memory to {category}: {item}")
                        changes_made = True

    if changes_made:
        print("Memory extraction completed and saved.")
    else:
        print("Memory extraction completed, no new memories added.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('audio_cache', filename)

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        global config
        new_config = request.json
        config.update(new_config)
        save_config()
        # Re-initialize to apply changes
        initialize_system(current_session_id)
        return jsonify({"status": "success"})
    return jsonify(config)

@app.route('/api/test_tts', methods=['POST'])
def test_tts():
    data = request.json
    tts_config = data.get('tts_config')
    active_character = data.get('active_character')

    if not tts_config or not active_character:
        return jsonify({"status": "error", "message": "Missing config or character data"}), 400

    try:
        # Load character to get speaker_id and voice_openai
        char_loader = CharacterLoader()
        char_data = char_loader.load_character(active_character)

        # Instantiate temporary client
        temp_config = {"providers": {"tts": tts_config}}
        temp_tts_client = get_tts_client(temp_config)

        # Synthesize test word
        test_text = "テスト" # "Tesuto" in Japanese
        speaker_id = char_data.get('speaker_id', 2)
        voice = char_data.get('voice_openai')

        audio_filename = temp_tts_client.synthesize(test_text, speaker_id=speaker_id, voice=voice)

        if audio_filename:
            return jsonify({"status": "success", "audio_url": f"/audio/{audio_filename}"})
        else:
            return jsonify({"status": "error", "message": "Failed to synthesize audio. Check credentials/URL."}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/toggle_debug', methods=['POST'])
def toggle_debug():
    global config
    data = request.json
    config['debug_mode'] = data.get('debug_mode', False)
    save_config()
    return jsonify({"status": "success", "debug_mode": config['debug_mode']})

@app.route('/api/toggle_voice', methods=['POST'])
def toggle_voice():
    global config
    data = request.json
    config['enable_voice'] = data.get('enable_voice', True)
    save_config()
    return jsonify({"status": "success", "enable_voice": config['enable_voice']})

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        return jsonify([])
    sessions = []
    for f in os.listdir(conversations_dir):
        if f.endswith('.json'):
            sessions.append(f.replace('.json', ''))
    return jsonify(sessions)

@app.route('/api/load_session', methods=['POST'])
def load_session():
    data = request.json
    session_id = data.get('session_id')
    if session_id:
        initialize_system(session_id)
        return jsonify({"status": "success", "history": conversation_history})
    return jsonify({"status": "error", "message": "Missing session_id"}), 400

@app.route('/api/new_session', methods=['POST'])
def new_session():
    initialize_system()
    return jsonify({"status": "success", "session_id": current_session_id})

@socketio.on('connect')
def handle_connect():
    print("Client connected.")
    emit('status', {'message': f"Connected. Character: {character_data['id']}"})

@socketio.on('user_message')
def handle_message(data):
    global turn_counter
    user_text = data.get('text')

    if not user_text:
        return

    debug_info = {}
    is_debug = config.get('debug_mode', False)
    start_time_total = time.time()

    # 1. Update history
    conversation_history.append({"role": "user", "content": user_text})
    turn_counter += 1

    # Format messages for LLM
    # Get last few messages for context to avoid context length issues
    context_msgs = conversation_history[-10:]

    emit('status', {'message': 'Sedang berpikir...'})

    try:
        # 2. Generate Response
        start_time_chat = time.time()
        system_prompt, retrieved_memories = build_system_prompt(user_text)

        if is_debug:
            debug_info['system_prompt'] = system_prompt
            debug_info['retrieved_memories'] = retrieved_memories
            debug_info['context_messages'] = context_msgs
            debug_info['chat_provider'] = config.get('providers', {}).get('chat', {}).get('type', 'unknown')

        raw_response_text = llm_client.generate_chat(context_msgs, system_prompt)
        chat_latency = time.time() - start_time_chat

        if is_debug:
            debug_info['raw_response'] = raw_response_text
            debug_info['chat_latency'] = round(chat_latency, 2)
            debug_info['chat_status'] = "Success" if raw_response_text else "Failed"

        if not raw_response_text:
            emit('error', {'message': 'Gagal mendapatkan respons dari LLM.'})
            if is_debug: emit('debug_info', debug_info)
            return

        mood, response_text = extract_mood_from_response(raw_response_text)

        if mood:
            memory_manager.update_temporary_state({"mood": mood})

        conversation_history.append({"role": "assistant", "content": response_text})
        save_session() # Save after every interaction

        # 3. Send Text to UI immediately
        emit('bot_response', {'text': response_text, 'audio_url': None})

        # 4. Process VoiceVox pipeline
        enable_voice = config.get('enable_voice', True)

        if enable_voice:
            emit('status', {'message': 'Memproses suara...'})

            dialogue_text = llm_client.extract_dialogue(response_text)

            if dialogue_text:
                speaker_id = character_data.get('speaker_id', 2)
                voice_openai = character_data.get('voice_openai')

                start_time_translate = time.time()
                if is_debug: debug_info['translate_provider'] = config.get('providers', {}).get('translation', {}).get('type', 'unknown')

                jp_text = llm_client.translate_to_japanese(dialogue_text)

                translate_latency = time.time() - start_time_translate
                if is_debug:
                    debug_info['translation'] = jp_text
                    debug_info['translate_latency'] = round(translate_latency, 2)
                    debug_info['translate_status'] = "Success" if jp_text else "Failed"

                if jp_text:
                    start_time_voice = time.time()
                    audio_filename = tts_client.synthesize(jp_text, speaker_id=speaker_id, voice=voice_openai)
                    voice_latency = time.time() - start_time_voice

                    if is_debug:
                        debug_info['voice_latency'] = round(voice_latency, 2)
                        debug_info['voice_status'] = "Success" if audio_filename else "Failed"

                    if audio_filename:
                        # Update the UI with the audio URL for the last message
                        emit('audio_ready', {'audio_url': f'/audio/{audio_filename}'})

            # Cleanup old cache
            tts_client.cleanup_cache()
        else:
            if is_debug:
                debug_info['translate_status'] = "Skipped"
                debug_info['voice_status'] = "Skipped"

        # 5. Trigger Memory Extraction if needed
        interval = config.get('memory_extraction_interval_turns', 5)
        if turn_counter % interval == 0:
            emit('status', {'message': 'Menyimpan memori...'})
            recent_log = conversation_history[-(interval * 2):] # User + Assistant pairs

            if is_debug: debug_info['memory_provider'] = config.get('providers', {}).get('memory', {}).get('type', 'unknown')

            mode = config.get('memory_extraction_mode', 'background')
            if mode == 'background':
                # Can't easily track time/status in background thread for this request's debug_info
                threading.Thread(target=perform_memory_extraction, args=(recent_log,)).start()
                if is_debug: debug_info['memory_extraction_status'] = "Started (Background)"
            else:
                start_time_mem = time.time()
                perform_memory_extraction(recent_log)
                mem_latency = time.time() - start_time_mem
                if is_debug:
                    debug_info['memory_extraction_latency'] = round(mem_latency, 2)
                    debug_info['memory_extraction_status'] = "Completed (Sync)"

        emit('status', {'message': 'Siap'})

        if is_debug:
            debug_info['total_latency'] = round(time.time() - start_time_total, 2)
            emit('debug_info', debug_info)

    except Exception as e:
        print(f"Error handling message: {e}")
        emit('error', {'message': f"Terjadi kesalahan: {str(e)}"})
        emit('status', {'message': 'Error'})
        if is_debug:
            debug_info['error'] = str(e)
            emit('debug_info', debug_info)

if __name__ == '__main__':
    initialize_system()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
