document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // UI Elements
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const audioPlayer = document.getElementById('audio-player');

    const settingsBtn = document.getElementById('settings-btn');
    const sessionsBtn = document.getElementById('sessions-btn');
    const settingsModal = document.getElementById('settings-modal');
    const sessionsModal = document.getElementById('sessions-modal');
    const closeBtn = document.querySelector('.close-btn');
    const closeSessionsBtn = document.getElementById('close-sessions-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const newSessionBtn = document.getElementById('new-session-btn');
    const sessionsList = document.getElementById('sessions-list');

    let audioQueue = [];
    let isPlaying = false;

    // --- WebSocket Events ---
    socket.on('connect', () => {
        statusIndicator.innerText = "Connected";
    });

    socket.on('status', (data) => {
        statusIndicator.innerText = data.message;
    });

    socket.on('bot_response', (data) => {
        appendMessage('bot', data.text);
    });

    socket.on('audio_ready', (data) => {
        if(data.audio_url) {
            playAudio(data.audio_url);

            // Optional: attach a play button to the last bot message
            const botMessages = document.querySelectorAll('.message.bot');
            if (botMessages.length > 0) {
                const lastMsg = botMessages[botMessages.length - 1];
                if (!lastMsg.querySelector('.play-audio-btn')) {
                    const playBtn = document.createElement('button');
                    playBtn.innerHTML = '▶';
                    playBtn.className = 'play-audio-btn';
                    playBtn.onclick = () => playAudio(data.audio_url);
                    lastMsg.appendChild(playBtn);
                }
            }
        }
    });

    socket.on('error', (data) => {
        appendMessage('bot', "❌ Error: " + data.message);
    });

    // --- Chat Functions ---
    function sendMessage() {
        const text = messageInput.value.trim();
        if (text) {
            appendMessage('user', text);
            socket.emit('user_message', { text: text });
            messageInput.value = '';
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.innerText = text;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Input handlers
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // --- Audio Playback ---
    function playAudio(url) {
        audioQueue.push(url);
        if (!isPlaying) {
            processAudioQueue();
        }
    }

    function processAudioQueue() {
        if (audioQueue.length === 0) {
            isPlaying = false;
            return;
        }

        isPlaying = true;
        const url = audioQueue.shift();
        audioPlayer.src = url;
        audioPlayer.play().catch(e => {
            console.error("Audio playback error:", e);
            processAudioQueue();
        });
    }

    audioPlayer.onended = () => {
        processAudioQueue();
    };

    function loadChatHistory() {
        chatContainer.innerHTML = '';
        fetch('/api/load_session', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: window.currentSessionId})
        }).then(res => res.json())
          .then(data => {
              if(data.status === 'success') {
                  data.history.forEach(msg => {
                      if(msg.role !== 'system') {
                          appendMessage(msg.role === 'user' ? 'user' : 'bot', msg.content);
                      }
                  });
              }
          });
    }

    // --- Settings Management ---
    function loadSettings() {
        fetch('/api/config')
            .then(res => res.json())
            .then(config => {
                document.getElementById('set-character').value = config.active_character;
                document.getElementById('set-voicevox').value = config.voicevox_url;
                document.getElementById('set-mem-mode').value = config.memory_extraction_mode;
                document.getElementById('set-mem-interval').value = config.memory_extraction_interval_turns;

                // Providers
                if(config.providers) {
                    ['chat', 'translation', 'memory'].forEach(type => {
                        const p = config.providers[type];
                        if(p) {
                            document.getElementById(`${type.substring(0,4)}-type`).value = p.type;
                            document.getElementById(`${type.substring(0,4)}-url`).value = p.base_url || '';
                            document.getElementById(`${type.substring(0,4)}-model`).value = p.model_name || '';
                            document.getElementById(`${type.substring(0,4)}-key`).value = p.api_key || '';
                        }
                    });
                }
            });
    }

    sessionsBtn.onclick = () => {
        fetch('/api/sessions')
            .then(res => res.json())
            .then(sessions => {
                sessionsList.innerHTML = '';
                sessions.forEach(sid => {
                    const btn = document.createElement('button');
                    btn.innerText = `Session: ${sid.substring(0, 8)}...`;
                    btn.style.display = 'block';
                    btn.style.width = '100%';
                    btn.style.padding = '10px';
                    btn.style.marginBottom = '5px';
                    btn.style.backgroundColor = '#2a2a40';
                    btn.style.color = 'white';
                    btn.style.border = '1px solid #555';
                    btn.style.cursor = 'pointer';
                    btn.onclick = () => {
                        window.currentSessionId = sid;
                        sessionsModal.style.display = "none";
                        loadChatHistory();
                        statusIndicator.innerText = "Loaded Session";
                    };
                    sessionsList.appendChild(btn);
                });
                sessionsModal.style.display = "block";
            });
    }

    newSessionBtn.onclick = () => {
        fetch('/api/new_session', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                window.currentSessionId = data.session_id;
                sessionsModal.style.display = "none";
                chatContainer.innerHTML = '';
                statusIndicator.innerText = "Started New Session";
            });
    }

    settingsBtn.onclick = () => {
        loadSettings();
        settingsModal.style.display = "block";
    }

    closeBtn.onclick = () => {
        settingsModal.style.display = "none";
    }

    closeSessionsBtn.onclick = () => {
        sessionsModal.style.display = "none";
    }

    window.onclick = (e) => {
        if (e.target == settingsModal) {
            settingsModal.style.display = "none";
        } else if (e.target == sessionsModal) {
            sessionsModal.style.display = "none";
        }
    }

    saveSettingsBtn.onclick = () => {
        const newConfig = {
            active_character: document.getElementById('set-character').value,
            voicevox_url: document.getElementById('set-voicevox').value,
            memory_extraction_mode: document.getElementById('set-mem-mode').value,
            memory_extraction_interval_turns: parseInt(document.getElementById('set-mem-interval').value),
            providers: {
                chat: {
                    type: document.getElementById('chat-type').value,
                    base_url: document.getElementById('chat-url').value,
                    model_name: document.getElementById('chat-model').value,
                    api_key: document.getElementById('chat-key').value
                },
                translation: {
                    type: document.getElementById('trans-type').value,
                    base_url: document.getElementById('trans-url').value,
                    model_name: document.getElementById('trans-model').value,
                    api_key: document.getElementById('trans-key').value
                },
                memory: {
                    type: document.getElementById('mem-type').value,
                    base_url: document.getElementById('mem-url').value,
                    model_name: document.getElementById('mem-model').value,
                    api_key: document.getElementById('mem-key').value
                }
            }
        };

        fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(newConfig)
        }).then(() => {
            settingsModal.style.display = "none";
            // Clear chat on settings change to restart fresh
            chatContainer.innerHTML = '';
            statusIndicator.innerText = "Settings saved. Restarting session...";
            setTimeout(() => {
                 window.location.reload();
            }, 1000);
        });
    };
});
