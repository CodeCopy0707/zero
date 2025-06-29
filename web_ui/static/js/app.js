// Agent Zero Gemini Web UI JavaScript

class AgentZeroUI {
    constructor() {
        this.websocket = null;
        this.clientId = this.generateClientId();
        this.isConnected = false;
        this.messageQueue = [];
        this.isRecording = false;
        this.recognition = null;

        this.initializeElements();
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadInitialData();
    }
    
    generateClientId() {
        return 'client_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeElements() {
        this.elements = {
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-btn'),
            chatMessages: document.getElementById('chat-messages'),
            typingIndicator: document.getElementById('typing-indicator'),
            connectionStatus: document.getElementById('connection-status'),
            statusIndicator: document.getElementById('status-indicator'),
            agentState: document.getElementById('agent-state'),
            agentCount: document.getElementById('agent-count'),
            memoryCount: document.getElementById('memory-count'),
            toolsCount: document.getElementById('tools-count'),
            toolsList: document.getElementById('tools-list'),
            agentHierarchy: document.getElementById('agent-hierarchy'),
            memoryList: document.getElementById('memory-list'),
            activityList: document.getElementById('activity-list'),
            responseTime: document.getElementById('response-time'),
            successRate: document.getElementById('success-rate'),
            totalInteractions: document.getElementById('total-interactions'),
            uptime: document.getElementById('uptime'),
            charCount: document.getElementById('char-count'),
            clearChatButton: document.getElementById('clear-chat-btn'),
            newChatButton: document.getElementById('new-chat-btn'),
            resetAgentButton: document.getElementById('reset-agent-btn'),
            exportChatButton: document.getElementById('export-chat-btn'),
            attachButton: document.getElementById('attach-btn'),
            voiceButton: document.getElementById('voice-btn')
        };
    }
    
    setupEventListeners() {
        // Send message on button click
        this.elements.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Send message on Ctrl+Enter
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea and update character count
        this.elements.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateCharacterCount();
            this.updateSendButton();
        });

        // Clear chat
        this.elements.clearChatButton?.addEventListener('click', () => {
            this.clearChat();
        });

        // New chat
        this.elements.newChatButton?.addEventListener('click', () => {
            this.newChat();
        });

        // Reset agent
        this.elements.resetAgentButton?.addEventListener('click', () => {
            this.resetAgent();
        });

        // Export chat
        this.elements.exportChatButton?.addEventListener('click', () => {
            this.exportChat();
        });

        // Voice input
        this.elements.voiceButton?.addEventListener('click', () => {
            this.toggleVoiceInput();
        });

        // Attach file
        this.elements.attachButton?.addEventListener('click', () => {
            this.attachFile();
        });
    }
    
    autoResizeTextarea() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.clientId}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus('connected');
            
            // Send queued messages
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                this.websocket.send(JSON.stringify(message));
            }
        };
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                this.connectWebSocket();
            }, 3000);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'response':
                this.hideTypingIndicator();
                this.addMessage('agent', data.message, data.timestamp);
                break;
                
            case 'typing':
                this.showTypingIndicator();
                break;
                
            case 'error':
                this.hideTypingIndicator();
                this.addMessage('error', data.message, data.timestamp);
                break;
                
            case 'status':
                this.updateStatus(data.data);
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Clear input
        this.elements.messageInput.value = '';
        this.autoResizeTextarea();
        
        // Send via WebSocket
        const messageData = {
            type: 'chat',
            message: message,
            timestamp: new Date().toISOString()
        };
        
        if (this.isConnected) {
            this.websocket.send(JSON.stringify(messageData));
        } else {
            this.messageQueue.push(messageData);
            this.updateConnectionStatus('reconnecting');
        }
    }
    
    addMessage(type, content, timestamp = null) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `message-wrapper ${type === 'user' ? 'user' : 'assistant'}`;

        if (type === 'error') {
            messageWrapper.className = 'message-wrapper assistant error-message';
        }

        const avatarIcon = type === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        const senderName = type === 'user' ? 'You' : 'Agent Zero';

        // Format content (convert markdown-like formatting)
        const formattedContent = this.formatMessageContent(content);

        messageWrapper.innerHTML = `
            <div class="message-avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${senderName}</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-text">${formattedContent}</div>
            </div>
        `;

        this.elements.chatMessages.appendChild(messageWrapper);
        this.scrollToBottom();

        // Update metrics
        this.updateMetrics();

        // Add to activity log
        this.addActivity(type === 'user' ? 'Message Sent' : 'Response Received', 'fas fa-comment');
    }
    
    formatMessageContent(content) {
        // Basic markdown-like formatting
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        // Format code blocks
        formatted = formatted.replace(/```(\w+)?\n?(.*?)```/gs, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
        });
        
        // Format tool calls
        formatted = formatted.replace(/TOOL_CALL:\s*(\w+)\((.*?)\)/g, (match, toolName, params) => {
            return `<div class="tool-call"><strong>🔧 Tool Call:</strong> ${toolName}(${params})</div>`;
        });
        
        return formatted;
    }
    
    showTypingIndicator() {
        this.elements.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.elements.typingIndicator.style.display = 'none';
    }
    
    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }
    
    updateConnectionStatus(status) {
        const statusText = this.elements.connectionStatus;
        const statusIcon = this.elements.statusIndicator;

        switch (status) {
            case 'connected':
                statusIcon.className = 'fas fa-circle text-success me-1';
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusIcon.className = 'fas fa-circle text-danger me-1';
                statusText.textContent = 'Disconnected';
                break;
            case 'reconnecting':
                statusIcon.className = 'fas fa-circle text-warning me-1';
                statusText.textContent = 'Reconnecting...';
                break;
            case 'error':
                statusIcon.className = 'fas fa-circle text-danger me-1';
                statusText.textContent = 'Error';
                break;
            default:
                statusIcon.className = 'fas fa-circle text-secondary me-1';
                statusText.textContent = 'Unknown';
        }
    }
    
    async loadInitialData() {
        try {
            // Load status
            const statusResponse = await fetch('/api/status');
            const status = await statusResponse.json();
            this.updateStatus(status);
            
            // Load tools
            const toolsResponse = await fetch('/api/tools');
            const toolsData = await toolsResponse.json();
            this.updateTools(toolsData.tools);
            
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }
    
    updateStatus(status) {
        if (status.root_agent) {
            this.elements.agentState.textContent = status.root_agent.state;
            this.elements.agentState.className = `badge bg-${this.getStatusColor(status.root_agent.state)}`;
        }

        this.elements.agentCount.textContent = status.total_agents || 0;

        // Update other counts if available
        if (this.elements.memoryCount) {
            this.elements.memoryCount.textContent = status.memory_count || 0;
        }

        if (this.elements.toolsCount) {
            this.elements.toolsCount.textContent = status.tools_count || 0;
        }
    }
    
    getStatusColor(state) {
        const colorMap = {
            'idle': 'success',
            'thinking': 'primary',
            'acting': 'warning',
            'communicating': 'info',
            'error': 'danger',
            'terminated': 'secondary'
        };
        return colorMap[state] || 'secondary';
    }
    
    updateTools(tools) {
        if (!tools || tools.length === 0) {
            this.elements.toolsList.innerHTML = '<div class="text-muted">No tools available</div>';
            return;
        }
        
        const toolsHtml = tools.map(tool => `
            <div class="tool-item">
                <div class="tool-name">${tool.name}</div>
                <div class="tool-description">${tool.description}</div>
            </div>
        `).join('');
        
        this.elements.toolsList.innerHTML = toolsHtml;
    }
    
    clearChat() {
        // Remove all messages except welcome message
        const messages = this.elements.chatMessages.querySelectorAll('.message-wrapper');
        messages.forEach((message, index) => {
            if (index > 0) { // Keep first message (welcome)
                message.remove();
            }
        });

        this.addActivity('Chat Cleared', 'fas fa-trash');
    }

    newChat() {
        this.clearChat();
        this.addActivity('New Chat Started', 'fas fa-plus');
    }

    updateCharacterCount() {
        const text = this.elements.messageInput.value;
        const count = text.length;

        if (this.elements.charCount) {
            this.elements.charCount.textContent = count;

            // Update color based on limit
            if (count > 3500) {
                this.elements.charCount.style.color = 'var(--danger-color)';
            } else if (count > 3000) {
                this.elements.charCount.style.color = 'var(--warning-color)';
            } else {
                this.elements.charCount.style.color = 'var(--text-muted)';
            }
        }
    }

    updateSendButton() {
        const hasText = this.elements.messageInput.value.trim().length > 0;
        this.elements.sendButton.disabled = !hasText;
    }

    addActivity(title, icon) {
        if (!this.elements.activityList) return;

        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';

        const timeStr = new Date().toLocaleTimeString();

        activityItem.innerHTML = `
            <div class="activity-icon">
                <i class="${icon}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${title}</div>
                <div class="activity-time">${timeStr}</div>
            </div>
        `;

        // Add to top of list
        this.elements.activityList.insertBefore(activityItem, this.elements.activityList.firstChild);

        // Keep only last 10 activities
        const activities = this.elements.activityList.querySelectorAll('.activity-item');
        if (activities.length > 10) {
            activities[activities.length - 1].remove();
        }
    }

    updateMetrics() {
        // Update total interactions
        if (this.elements.totalInteractions) {
            const current = parseInt(this.elements.totalInteractions.textContent) || 0;
            this.elements.totalInteractions.textContent = current + 1;
        }

        // Update uptime (simplified)
        if (this.elements.uptime && !this.startTime) {
            this.startTime = Date.now();
        }

        if (this.elements.uptime && this.startTime) {
            const uptime = Math.floor((Date.now() - this.startTime) / 60000); // minutes
            this.elements.uptime.textContent = `${uptime}m`;
        }
    }

    exportChat() {
        const messages = this.elements.chatMessages.querySelectorAll('.message-wrapper');
        let chatText = 'Agent Zero Gemini Chat Export\n';
        chatText += '=' + '='.repeat(40) + '\n\n';

        messages.forEach(message => {
            const isUser = message.classList.contains('user');
            const content = message.querySelector('.message-text').textContent;
            const time = message.querySelector('.message-time').textContent;

            chatText += `[${time}] ${isUser ? 'User' : 'Agent'}: ${content}\n\n`;
        });

        const blob = new Blob([chatText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agent-zero-chat-${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.addActivity('Chat Exported', 'fas fa-download');
    }

    toggleVoiceInput() {
        // Voice input functionality
        if (!this.isRecording) {
            this.startVoiceRecording();
        } else {
            this.stopVoiceRecording();
        }
    }

    startVoiceRecording() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Speech recognition not supported in this browser');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isRecording = true;
            this.elements.voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
            this.elements.voiceButton.classList.add('recording');
            this.addActivity('Voice Recording Started', 'fas fa-microphone');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.elements.messageInput.value = transcript;
            this.updateCharacterCount();
            this.updateSendButton();
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.stopVoiceRecording();
        };

        this.recognition.onend = () => {
            this.stopVoiceRecording();
        };

        this.recognition.start();
    }

    stopVoiceRecording() {
        if (this.recognition) {
            this.recognition.stop();
        }

        this.isRecording = false;
        this.elements.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        this.elements.voiceButton.classList.remove('recording');
        this.addActivity('Voice Recording Stopped', 'fas fa-microphone-slash');
    }

    attachFile() {
        // File attachment functionality
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.pdf,.doc,.docx,.json,.csv,.py,.js,.html,.css,.md';
        input.multiple = false;

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                try {
                    // Check file size (max 10MB)
                    if (file.size > 10 * 1024 * 1024) {
                        alert('File size must be less than 10MB');
                        return;
                    }

                    // Read file content
                    const fileContent = await this.readFileContent(file);

                    // Add file content to message input
                    const currentMessage = this.elements.messageInput.value;
                    const fileMessage = `\n\n[File: ${file.name}]\n${fileContent}\n[End of file]\n\n`;

                    this.elements.messageInput.value = currentMessage + fileMessage;
                    this.updateCharacterCount();
                    this.updateSendButton();

                    this.addActivity(`File Attached: ${file.name} (${this.formatFileSize(file.size)})`, 'fas fa-paperclip');

                } catch (error) {
                    console.error('Error reading file:', error);
                    alert('Error reading file: ' + error.message);
                }
            }
        };

        input.click();
    }

    readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                resolve(e.target.result);
            };

            reader.onerror = (e) => {
                reject(new Error('Failed to read file'));
            };

            // Read as text for supported file types
            if (file.type.startsWith('text/') ||
                file.name.endsWith('.txt') ||
                file.name.endsWith('.md') ||
                file.name.endsWith('.py') ||
                file.name.endsWith('.js') ||
                file.name.endsWith('.html') ||
                file.name.endsWith('.css') ||
                file.name.endsWith('.json')) {
                reader.readAsText(file);
            } else {
                // For other files, read as data URL
                reader.readAsDataURL(file);
            }
        });
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async resetAgent() {
        if (!confirm('Are you sure you want to reset the agent?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/reset', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.clearChat();
                this.addMessage('system', 'Agent has been reset successfully.');
                this.loadInitialData();
            } else {
                this.addMessage('error', `Failed to reset agent: ${result.error}`);
            }
        } catch (error) {
            console.error('Error resetting agent:', error);
            this.addMessage('error', 'Failed to reset agent due to network error.');
        }
    }
}

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.agentUI = new AgentZeroUI();
});
