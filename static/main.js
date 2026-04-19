document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const replyIndicator = document.getElementById('reply-indicator');
    const replySnippet = document.getElementById('reply-snippet');
    const cancelReply = document.getElementById('cancel-reply');
    
    let currentReplyContext = null;
    const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    function appendMessage(text, side, isLoading = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${side} ${isLoading ? 'loading' : ''}`;
        
        if (isLoading) {
            msgDiv.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        } else {
            // Handle source citations if they exist
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

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let text = userInput.value.trim();
        if (!text) return;

        const displayUserText = text;
        
        // If we are replying, prepend the context for the LLM
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

            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            chatWindow.removeChild(loadingMsg);
            const msgElement = appendMessage(data.answer, 'bot');
            
            // Container for actions (Audio + Reply)
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'msg-actions';
            msgElement.appendChild(actionsDiv);

            // Add Reply Button
            const replyBtn = document.createElement('button');
            replyBtn.className = 'reply-btn';
            replyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H4"></path></svg> Reply';
            replyBtn.onclick = () => setReplyContext(data.answer);
            actionsDiv.appendChild(replyBtn);

            if (data.audio) {
                // Auto-play the audio
                const audio = new Audio(data.audio);
                audio.play().catch(e => console.log('Audio autoplay blocked:', e));
                
                // Add a play/pause button to the actions
                const playBtn = document.createElement('button');
                playBtn.className = 'audio-btn';
                playBtn.title = 'Pause/Play Audio';
                
                const playIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
                const pauseIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
                
                playBtn.innerHTML = pauseIcon; // Initially showing pause because it autoplays
                
                audio.onended = () => { playBtn.innerHTML = playIcon; };
                audio.onpause = () => { playBtn.innerHTML = playIcon; };
                audio.onplay = () => { playBtn.innerHTML = pauseIcon; };
                
                playBtn.onclick = () => {
                    if (audio.paused) {
                        audio.play();
                    } else {
                        audio.pause();
                    }
                };
                actionsDiv.appendChild(playBtn);
            }
        } catch (error) {
            chatWindow.removeChild(loadingMsg);
            appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Error:', error);
        }
    });
});
