document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
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
            msgDiv.innerHTML = processedText;
        }
        
        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return msgDiv;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = '';
        appendMessage(text, 'user');

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
            appendMessage(data.answer, 'bot');
        } catch (error) {
            chatWindow.removeChild(loadingMsg);
            appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Error:', error);
        }
    });
});
