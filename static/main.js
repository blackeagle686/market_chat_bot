document.addEventListener('DOMContentLoaded', () => {
    const chatForm      = document.getElementById('chat-form');
    const chatWindow    = document.getElementById('chat-window');
    const userInput     = document.getElementById('user-input');
    const replyIndicator = document.getElementById('reply-indicator');
    const replySnippet  = document.getElementById('reply-snippet');
    const cancelReply   = document.getElementById('cancel-reply');
    const micBtn        = document.getElementById('mic-btn');
    const inputGroup    = micBtn.closest('.input-group');
    const voiceStatus   = document.getElementById('voice-status');
    const voiceStatusTxt = document.getElementById('voice-status-text');

    let currentReplyContext = null;
    const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    // ── Voice recording state ────────────────────────────────────────────────
    let isRecording = false;
    let recognition = null;   // Web Speech API instance (primary)
    let mediaRecorder = null; // MediaRecorder fallback
    let audioChunks  = [];

    // ── Helpers ──────────────────────────────────────────────────────────────
    function appendMessage(text, side, isLoading = false) {
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
    const micIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>`;
    const stopIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2" ry="2"></rect></svg>`;
    const spinnerIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a10 10 0 0 1 10 10"></path></svg>`;

    function setRecordingUI(state) {
        // state: 'idle' | 'recording' | 'transcribing'
        micBtn.classList.remove('recording', 'transcribing');
        voiceStatus.style.display = 'none';
        inputGroup.classList.remove('is-recording');

        if (state === 'idle') {
            micBtn.innerHTML = micIcon;
        } else if (state === 'recording') {
            micBtn.classList.add('recording');
            micBtn.innerHTML = stopIcon;
            voiceStatus.style.display = 'flex';
            voiceStatus.classList.remove('transcribing-label');
            voiceStatusTxt.textContent = 'Recording… click to stop';
            inputGroup.classList.add('is-recording');
        } else if (state === 'transcribing') {
            micBtn.classList.add('transcribing');
            micBtn.innerHTML = spinnerIcon;
            voiceStatus.style.display = 'flex';
            voiceStatus.classList.add('transcribing-label');
            voiceStatusTxt.textContent = 'Transcribing…';
            inputGroup.classList.add('is-recording');
        }
    }

    // ── Strategy 1: Web Speech API (Chrome / Edge / Safari 17+) ─────────────
    function startWebSpeech() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US'; // English
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
                // Stop all mic tracks
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

    // ── Mic button click handler ─────────────────────────────────────────────
    const hasWebSpeech = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

    micBtn.addEventListener('click', () => {
        if (!isRecording) {
            // Start recording
            if (hasWebSpeech) {
                startWebSpeech();
            } else {
                startMediaRecorder();
            }
        } else {
            // Stop recording
            setRecordingUI('idle');
            if (hasWebSpeech) {
                stopWebSpeech();
            } else {
                stopMediaRecorder();
            }
            isRecording = false;
        }
    });
});
