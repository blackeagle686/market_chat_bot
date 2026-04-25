document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const mainUi         = document.getElementById('main-ui');
    const vaMainView     = document.getElementById('va-main-view');
    const chatContainer  = document.getElementById('chat-window-container');
    const closeChatBtn   = document.getElementById('close-chat-btn');
    
    // Voice UI Elements
    const mainMicBtn     = document.getElementById('main-mic-btn');
    const mainMicWrapper = document.getElementById('main-mic-wrapper');
    const statusText     = document.getElementById('main-status-text');
    const transcriptPrev = document.getElementById('transcript-preview');
    const footerEq       = document.getElementById('footer-equalizer');
    const footerText     = document.getElementById('footer-text');
    const exitBtn        = document.getElementById('exit-btn');
    
    // Chat Elements
    const chatForm      = document.getElementById('chat-form');
    const chatWindow    = document.getElementById('chat-window');
    const userInput     = document.getElementById('user-input');
    const replyIndicator = document.getElementById('reply-indicator');
    const replySnippet  = document.getElementById('reply-snippet');
    const cancelReply   = document.getElementById('cancel-reply');
    const chatMicBtn    = document.getElementById('chat-mic-btn');
    
    // Suggestions
    // Suggestions handled by delegated listener at bottom
    
    // Theme Toggle is now handled globally in base.html
    let currentReplyContext = null;
    const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    // ── Voice recording state ────────────────────────────────────────────────
    let isRecording = false;
    let recognition = null;   // Web Speech API instance
    let mediaRecorder = null; // MediaRecorder fallback
    let audioChunks  = [];

    // ── Helpers ──────────────────────────────────────────────────────────────
    function showChatView() {
        chatContainer.classList.remove('d-none');
        chatContainer.style.opacity = '1';
        chatContainer.style.pointerEvents = 'auto';
        vaMainView.classList.add('hidden');
        vaMainView.style.opacity = '0';
        vaMainView.style.pointerEvents = 'none';
    }

    function hideChatView() {
        chatContainer.classList.add('d-none');
        chatContainer.style.opacity = '0';
        chatContainer.style.pointerEvents = 'none';
        vaMainView.classList.remove('hidden');
        vaMainView.style.opacity = '1';
        vaMainView.style.pointerEvents = 'auto';
        statusText.textContent = "Listening...";
        transcriptPrev.classList.remove('visible');
    }

    closeChatBtn.addEventListener('click', hideChatView);

    // Exit button removed from HTML — guard against null
    if (exitBtn) {
        exitBtn.addEventListener('click', () => {
            hideChatView();
            stopRecordingAll();
        });
    }


    function appendMessage(text, side, isLoading = false) {
        showChatView();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${side} ${isLoading ? 'loading' : ''}`;

        if (isLoading) {
            msgDiv.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        } else {
            const citationRegex = /\[Source: ([^\]]+)\]/g;
            const suggestionRegex = /\[Suggestions: ([^\]]+)\]/;
            
            let processedText = text.replace(citationRegex, '<span class="source-tag">Source: $1</span>');
            
            // Extract suggestions
            const sMatch = processedText.match(suggestionRegex);
            let suggestions = [];
            if (sMatch) {
                suggestions = sMatch[1].split(',').map(s => s.trim());
                processedText = processedText.replace(suggestionRegex, '');
            }

            msgDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(processedText) : processedText;
            
            if (suggestions.length > 0) {
                renderSuggestions(suggestions, msgDiv);
            }
        }

        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return msgDiv;
    }

    function renderSuggestions(suggestions, msgElement) {
        if (!suggestions || suggestions.length === 0) return;
        
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'msg-suggestions';
        
        suggestions.forEach(text => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.innerHTML = `<i class="bi bi-stars"></i> ${text}`;
            chip.onclick = () => sendMessage(text);
            suggestionsDiv.appendChild(chip);
        });
        
        msgElement.appendChild(suggestionsDiv);
    }

    function processTableActions(msgElement) {
        const tables = msgElement.querySelectorAll('table');
        tables.forEach(table => {
            const rows = Array.from(table.querySelectorAll('tr'));
            rows.forEach((row, index) => {
                if (index === 0) {
                    // Header row: add "Info" column
                    const th = document.createElement('th');
                    th.textContent = 'Info';
                    row.appendChild(th);
                } else {
                    // Data row: add button
                    // Get row content to use as context BEFORE adding the button cell
                    const rowData = Array.from(row.cells)
                        .map(cell => cell.textContent.trim())
                        .filter(t => t)
                        .join(', ');
                    
                    const td = document.createElement('td');
                    const infoBtn = document.createElement('button');
                    infoBtn.className = 'row-info-btn';
                    infoBtn.innerHTML = '<i class="bi bi-info-circle"></i>';
                    infoBtn.title = 'Get more info about this product';
                    
                    infoBtn.onclick = () => {
                        sendMessage(`Tell me more information and a detailed description about this product: ${rowData}`);
                    };
                    
                    td.appendChild(infoBtn);
                    row.appendChild(td);
                }
            });
        });
    }

    function setReplyContext(text) {
        currentReplyContext = text;
        const snippet = text.length > 50 ? text.substring(0, 50) + '...' : text;
        replySnippet.innerText = `"${snippet}"`;
        replyIndicator.classList.remove('d-none');
        userInput.focus();
    }

    function clearReplyContext() {
        currentReplyContext = null;
        replyIndicator.classList.add('d-none');
    }

    if (cancelReply) cancelReply.addEventListener('click', clearReplyContext);

    // ── Send a message text ──────────────────────────────────────────────────
    async function sendMessage(text) {
        text = text.trim();
        if (!text) return;

        showChatView();

        const displayUserText = text;
        if (currentReplyContext) {
            text = `[User is replying to this previous message: "${currentReplyContext}"]\n\nQuestion: ${text}`;
            clearReplyContext();
        }

        userInput.value = '';
        appendMessage(displayUserText, 'user');
        const loadingMsg = appendMessage('', 'bot', true);

        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('session_id', sessionId);

            const response = await fetch('/chat', { method: 'POST', body: formData });
            const data = await response.json();

            chatWindow.removeChild(loadingMsg);
            const msgElement = appendMessage(data.answer, 'bot');
            processTableActions(msgElement);

            // Actions row
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'msg-actions';
            msgElement.appendChild(actionsDiv);

            // Reply button
            const replyBtn = document.createElement('button');
            replyBtn.className = 'reply-btn';
            replyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H4"></path></svg> Reply';
            replyBtn.onclick = () => setReplyContext(data.answer);
            actionsDiv.appendChild(replyBtn);

            // Audio playback button
            if (data.audio) {
                const audio = new Audio(data.audio);
                // audio.play() removed as per user request to default to paused

                const playBtn = document.createElement('button');
                playBtn.className = 'audio-btn';
                playBtn.title = 'Pause/Play Audio';

                const playIcon  = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
                const pauseIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';

                playBtn.innerHTML = playIcon; // Default to play icon since it's paused
                audio.onended = () => { playBtn.innerHTML = playIcon; };
                audio.onpause = () => { playBtn.innerHTML = playIcon; };
                audio.onplay  = () => { playBtn.innerHTML = pauseIcon; };
                playBtn.onclick = () => audio.paused ? audio.play() : audio.pause();
                actionsDiv.appendChild(playBtn);
            }
        } catch (error) {
            chatWindow.removeChild(loadingMsg);
            appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Error:', error);
        }
    }

    // ── Form submit (keyboard / send button) ─────────────────────────────────
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            sendMessage(userInput.value);
        });
    }

    // ── Voice UI helpers ─────────────────────────────────────────────────────
    function setRecordingUI(state) {
        // state: 'idle' | 'recording' | 'transcribing'
        mainMicWrapper.classList.remove('is-recording', 'is-transcribing');
        chatMicBtn.classList.remove('recording');
        
        if (state === 'idle') {
            statusText.textContent = "Verdant Assistant";
            footerEq.classList.remove('active');
            footerText.textContent = "AWAITING VOICE INPUT";
            transcriptPrev.classList.remove('visible');
        } else if (state === 'recording') {
            mainMicWrapper.classList.add('is-recording');
            chatMicBtn.classList.add('recording');
            statusText.textContent = "Listening...";
            footerEq.classList.add('active');
            footerText.textContent = "RECORDING...";
            transcriptPrev.textContent = "...";
            transcriptPrev.classList.add('visible');
            userInput.placeholder = "Listening...";
        } else if (state === 'transcribing') {
            mainMicWrapper.classList.add('is-transcribing');
            chatMicBtn.classList.add('recording'); // Keep red while transcribing
            statusText.textContent = "Processing...";
            footerEq.classList.remove('active');
            footerText.textContent = "TRANSCRIBING...";
            userInput.placeholder = "Processing...";
        }
    }

    // ── Strategy 1: Web Speech API (Chrome / Edge / Safari 17+) ─────────────
    function startWebSpeech() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        // Use document language (en or ar)
        const docLang = document.documentElement.lang || 'en';
        recognition.lang = docLang === 'ar' ? 'ar-SA' : 'en-US';
        
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.continuous = false;

        recognition.onstart = () => {
            isRecording = true;
            setRecordingUI('recording');
        };

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            transcriptPrev.textContent = '"' + transcript + '"';
            userInput.value = transcript;
        };

        recognition.onend = () => {
            isRecording = false;
            setRecordingUI('idle');
            const transcript = userInput.value.trim();
            userInput.placeholder = "Type your question...";
            
            if (transcript) {
                // Brief delay so user sees what was transcribed
                setTimeout(() => {
                    sendMessage(transcript);
                }, 800);
            }
        };

        recognition.onerror = (event) => {
            console.warn('Web Speech error:', event.error);
            isRecording = false;
            setRecordingUI('idle');
            if (event.error !== 'no-speech') {
                appendMessage(`⚠️ Microphone error: ${event.error}`, 'bot');
            }
        };

        try {
            recognition.start();
        } catch (e) {
            console.error("[Mic] Recognition start failed:", e);
            isRecording = false;
            setRecordingUI('idle');
            appendMessage(`⚠️ Could not start speech recognition: ${e.message || e}`, 'bot');
        }
    }

    function stopWebSpeech() {
        if (recognition) {
            recognition.stop();
            recognition = null;
        }
    }

    // ── Strategy 2: MediaRecorder → /transcribe (Whisper fallback) ───────────
    async function startMediaRecorder() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            const types = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
            let supportedType = types.find(t => MediaRecorder.isTypeSupported(t));
            console.log("[Mic] Using MIME type:", supportedType);
            
            mediaRecorder = new MediaRecorder(stream, { mimeType: supportedType });

            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };

            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                setRecordingUI('transcribing');

                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', blob, 'voice.webm');
                formData.append('lang', document.documentElement.lang || 'en');

                try {
                    const res = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await res.json();
                    setRecordingUI('idle');
                    if (data.text && data.text.trim()) {
                        transcriptPrev.textContent = '"' + data.text.trim() + '"';
                        userInput.value = data.text.trim();
                        // Brief delay so user sees what was transcribed
                        setTimeout(() => {
                            sendMessage(userInput.value);
                        }, 800);
                    } else {
                        appendMessage("⚠️ Couldn't understand the audio. Please try again.", 'bot');
                    }
                } catch (err) {
                    setRecordingUI('idle');
                    appendMessage('⚠️ Transcription failed. Please try again.', 'bot');
                    console.error(err);
                }
            };

            mediaRecorder.start();
            isRecording = true;
            setRecordingUI('recording');
        } catch (err) {
            console.error('Mic access denied:', err);
            appendMessage('⚠️ Microphone access denied. Please allow microphone access and try again.', 'bot');
        }
    }

    function stopMediaRecorder() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder = null;
        }
        isRecording = false;
    }

    function stopRecordingAll() {
        setRecordingUI('idle');
        if (hasWebSpeech) stopWebSpeech();
        else stopMediaRecorder();
        isRecording = false;
    }

    // ── Mic button click handler ─────────────────────────────────────────────
    const hasWebSpeech = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    console.log("[Mic] Web Speech API supported:", hasWebSpeech);

    if (mainMicBtn) {
        mainMicBtn.addEventListener('click', () => {
            console.log("[Mic] Main Mic Clicked. isRecording:", isRecording);
            toggleRecording();
        });
    }

    if (chatMicBtn) {
        chatMicBtn.addEventListener('click', () => {
            console.log("[Mic] Chat Mic Clicked. isRecording:", isRecording);
            toggleRecording();
        });
    }

    // Wire all suggestion chips (initial and dynamic)
    document.addEventListener('click', (e) => {
        const chip = e.target.closest('.suggestion-chip');
        if (chip) {
            const text = chip.textContent.trim();
            if (text) sendMessage(text);
        }
    });

    function toggleRecording() {
        if (!isRecording) {
            console.log("[Mic] Starting recording...");
            if (hasWebSpeech) startWebSpeech();
            else startMediaRecorder();
        } else {
            console.log("[Mic] Stopping recording...");
            stopRecordingAll();
        }
    }

    // Initial setup
    setRecordingUI('idle');
    // Don't override status text here, let setRecordingUI handle it
});
