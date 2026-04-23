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
    
    // Suggestions
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    
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

    // Clicking exit just resets view for now
    exitBtn.addEventListener('click', () => {
        hideChatView();
        stopRecordingAll();
    });

    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const text = chip.textContent.trim();
            sendMessage(text);
        });
    });

    function appendMessage(text, side, isLoading = false) {
        showChatView();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${side} ${isLoading ? 'loading' : ''}`;

        if (isLoading) {
            msgDiv.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        } else {
            const citationRegex = /\[Source: ([^\]]+)\]/g;
            let processedText = text.replace(citationRegex, '<span class="source-tag">Source: $1</span>');
            msgDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(processedText) : processedText;
        }

        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return msgDiv;
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

    cancelReply.addEventListener('click', clearReplyContext);

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
                audio.play().catch(e => console.log('Audio autoplay blocked:', e));

                const playBtn = document.createElement('button');
                playBtn.className = 'audio-btn';
                playBtn.title = 'Pause/Play Audio';

                const playIcon  = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
                const pauseIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';

                playBtn.innerHTML = pauseIcon;
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
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        sendMessage(userInput.value);
    });

    // ── Voice UI helpers ─────────────────────────────────────────────────────
    function setRecordingUI(state) {
        // state: 'idle' | 'recording' | 'transcribing'
        mainMicWrapper.classList.remove('is-recording', 'is-transcribing');
        
        if (state === 'idle') {
            statusText.textContent = "Verdant Assistant";
            footerEq.classList.remove('active');
            footerText.textContent = "AWAITING VOICE INPUT";
            transcriptPrev.classList.remove('visible');
        } else if (state === 'recording') {
            mainMicWrapper.classList.add('is-recording');
            statusText.textContent = "Listening...";
            footerEq.classList.add('active');
            footerText.textContent = "RECORDING...";
            transcriptPrev.textContent = "...";
            transcriptPrev.classList.add('visible');
        } else if (state === 'transcribing') {
            mainMicWrapper.classList.add('is-transcribing');
            statusText.textContent = "Processing...";
            footerEq.classList.remove('active');
            footerText.textContent = "TRANSCRIBING...";
        }
    }

    // ── Strategy 1: Web Speech API (Chrome / Edge / Safari 17+) ─────────────
    function startWebSpeech() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
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
            if (transcript) sendMessage(transcript);
        };

        recognition.onerror = (event) => {
            console.warn('Web Speech error:', event.error);
            isRecording = false;
            setRecordingUI('idle');
            if (event.error !== 'no-speech') {
                appendMessage(`⚠️ Microphone error: ${event.error}`, 'bot');
            }
        };

        recognition.start();
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
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };

            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                setRecordingUI('transcribing');

                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', blob, 'voice.webm');

                try {
                    const res = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await res.json();
                    setRecordingUI('idle');
                    if (data.text && data.text.trim()) {
                        transcriptPrev.textContent = '"' + data.text.trim() + '"';
                        userInput.value = data.text.trim();
                        sendMessage(userInput.value);
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

    mainMicBtn.addEventListener('click', () => {
        if (!isRecording) {
            if (hasWebSpeech) startWebSpeech();
            else startMediaRecorder();
        } else {
            stopRecordingAll();
        }
    });

    // Initial setup
    setRecordingUI('idle');
    statusText.textContent = "Listening..."; // start with listening as default
});
