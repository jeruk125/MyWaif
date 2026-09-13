document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // UI Elements

    // Call loadSettings on load to get the debug state initially
    loadSettings();
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const audioPlayer = document.getElementById('audio-player');

    const voiceToggleBtn = document.getElementById('voice-toggle-btn');
    const debugToggleBtn = document.getElementById('debug-toggle-btn');
    const debugSidebar = document.getElementById('debug-sidebar');
    const closeDebugBtn = document.getElementById('close-debug-btn');
    const debugContent = document.getElementById('debug-content');

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

    socket.on('debug_info', (data) => {
        if (!debugSidebar.classList.contains('open')) return;

        debugContent.innerHTML = ''; // Clear previous

        const createDebugItem = (title, content, isObject = false) => {
            if (!content && content !== 0) return '';
            let val = isObject ? JSON.stringify(content, null, 2) : content;
            return `
                <div class="debug-item">
                    <h4>${title}</h4>
                    <pre>${val}</pre>
                </div>
            `;
        };

        const createStatusItem = (title, status, latency, provider) => {
            if (!status) return '';
            let statusClass = 'status-failed';
            if (status.includes('Success') || status.includes('Completed')) statusClass = 'status-success';
            if (status.includes('Skipped')) statusClass = 'status-skipped';
            return `
                <div class="debug-item">
                    <h4>${title}</h4>
                    <div>Status: <span class="${statusClass}">${status}</span></div>
                    ${provider ? `<div>Provider: ${provider}</div>` : ''}
                    ${latency ? `<div>Latency: ${latency}s</div>` : ''}
                </div>
            `;
        };

        let html = '';

        if (data.total_latency) {
            html += `<div class="debug-item"><h4>Total Pipeline Time</h4><div>${data.total_latency}s</div></div>`;
        }

        if (data.error) {
            html += createDebugItem('Error', data.error);
        }

        html += createStatusItem('Chat Generation', data.chat_status, data.chat_latency, data.chat_provider);
        html += createStatusItem('Translation', data.translate_status, data.translate_latency, data.translate_provider);
        html += createStatusItem('VoiceVox', data.voice_status, data.voice_latency, null);
        html += createStatusItem('Memory Extraction', data.memory_extraction_status, data.memory_extraction_latency, data.memory_provider);

        html += createDebugItem('Retrieved Memories', data.retrieved_memories, true);
        html += createDebugItem('System Prompt', data.system_prompt);
        html += createDebugItem('Raw Response', data.raw_response);

        if (html === '') {
            html = '<p class="debug-empty">No debug data received yet.</p>';
        }

        debugContent.innerHTML = html;
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
    function updateVoiceToggleUI(isOn) {
        if (isOn) {
            voiceToggleBtn.classList.add('voice-on');
            voiceToggleBtn.innerText = '🔊 Voice: On';
        } else {
            voiceToggleBtn.classList.remove('voice-on');
            voiceToggleBtn.innerText = '🔇 Voice: Off';
        }
    }

    function updateDebugToggleUI(isOn) {
        const container = document.querySelector('.container');
        if (isOn) {
            debugToggleBtn.classList.add('debug-on');
            debugToggleBtn.innerText = '🐛 Debug: On';
            debugSidebar.classList.add('open');
            if (container) container.classList.add('debug-open');
            if (debugContent.innerHTML.trim() === '') {
                debugContent.innerHTML = '<p class="debug-empty">Waiting for interaction...</p>';
            }
        } else {
            debugToggleBtn.classList.remove('debug-on');
            debugToggleBtn.innerText = '🐛 Debug: Off';
            debugSidebar.classList.remove('open');
            if (container) container.classList.remove('debug-open');
        }
    }

    function loadSettings() {
        fetch('/api/config')
            .then(res => res.json())
            .then(config => {
                const isVoiceOn = config.enable_voice !== undefined ? config.enable_voice : true;
                updateVoiceToggleUI(isVoiceOn);
                updateDebugToggleUI(config.debug_mode);
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

    voiceToggleBtn.onclick = () => {
        const isCurrentlyOn = voiceToggleBtn.classList.contains('voice-on');
        const newState = !isCurrentlyOn;

        fetch('/api/toggle_voice', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enable_voice: newState})
        }).then(res => res.json())
          .then(data => {
              if (data.status === 'success') {
                  updateVoiceToggleUI(data.enable_voice);
              }
          });
    };

    debugToggleBtn.onclick = () => {
        const isCurrentlyOn = debugToggleBtn.classList.contains('debug-on');
        const newState = !isCurrentlyOn;

        fetch('/api/toggle_debug', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({debug_mode: newState})
        }).then(res => res.json())
          .then(data => {
              if (data.status === 'success') {
                  updateDebugToggleUI(data.debug_mode);
              }
          });
    };

    closeDebugBtn.onclick = () => {
        fetch('/api/toggle_debug', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({debug_mode: false})
        }).then(res => res.json())
          .then(data => {
              if (data.status === 'success') {
                  updateDebugToggleUI(false);
              }
          });
    };

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
