/**
 * Chat functionality JavaScript
 * Handles chat interface, messaging, and real-time updates
 */

class ChatManager {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.uploadForm = document.getElementById('uploadForm');
        this.fileInput = document.getElementById('fileInput');
        
        this.currentSessionId = app.sessionId;
        this.messageHistory = [];
        this.isTyping = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadConversationHistory();
        this.setupFileUpload();
        this.setupAutoScroll();
    }

    setupEventListeners() {
        // Chat form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // File upload
        document.getElementById('uploadBtn')?.addEventListener('click', () => {
            this.uploadFiles();
        });

        // Show citations
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('show-citations-btn')) {
                const messageId = e.target.dataset.messageId;
                this.showCitations(messageId);
            }
        });

        // Copy message
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-message-btn')) {
                const messageText = e.target.closest('.message-bubble').querySelector('.message-text').textContent;
                window.EduSmartAI.copyToClipboard(messageText);
            }
        });

        // Session management
        document.getElementById('newChatBtn')?.addEventListener('click', () => {
            this.createNewSession();
        });

        document.getElementById('clearHistoryBtn')?.addEventListener('click', () => {
            this.clearCurrentSession();
        });

        // Stats modal
        document.getElementById('showStatsBtn')?.addEventListener('click', () => {
            this.showSessionStats();
        });
    }

    setupFileUpload() {
        if (!this.fileInput) return;

        // Drag and drop
        const dropZone = document.querySelector('.upload-zone') || this.fileInput.parentElement;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.fileInput.files = files;
            this.updateFileList();
        });

        // File input change
        this.fileInput.addEventListener('change', () => {
            this.updateFileList();
        });
    }

    setupAutoScroll() {
        // Auto-scroll to bottom when new messages arrive
        this.observer = new MutationObserver(() => {
            this.scrollToBottom();
        });

        if (this.messagesContainer) {
            this.observer.observe(this.messagesContainer, {
                childList: true,
                subtree: true
            });
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Add user message to UI
        this.addMessageToUI('user', message);
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Remove typing indicator
                this.hideTypingIndicator();
                
                // Add assistant response
                this.addMessageToUI('assistant', data.response, {
                    citations: data.citations,
                    messageId: data.message_id,
                    responseType: data.response_type,
                    processingTime: data.processing_time
                });
            } else {
                throw new Error(data.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessageToUI('assistant', '❌ Sorry, I encountered an error processing your message. Please try again.', {
                isError: true
            });
            app.showToast('Failed to send message', 'error');
        }
    }

    addMessageToUI(role, content, options = {}) {
        const messageElement = document.createElement('div');
        messageElement.className = `message-bubble ${role} fade-in`;

        const contentElement = document.createElement('div');
        contentElement.className = `message-content ${role}`;

        if (role === 'assistant') {
            // Render markdown for assistant messages
            contentElement.innerHTML = app.renderMarkdown(content);
            
            // Highlight code blocks
            if (typeof hljs !== 'undefined') {
                contentElement.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
        } else {
            contentElement.innerHTML = content.replace(/\n/g, '<br>');
        }

        messageElement.appendChild(contentElement);

        // Add metadata
        if (options.processingTime || options.responseType) {
            const metaElement = document.createElement('div');
            metaElement.className = 'message-meta';
            
            let metaText = '';
            if (options.responseType && options.responseType !== 'query') {
                metaText += `Type: ${options.responseType} `;
            }
            if (options.processingTime) {
                metaText += `• ${options.processingTime}s`;
            }
            
            metaElement.textContent = metaText;
            messageElement.appendChild(metaElement);
        }

        // Add actions for assistant messages
        if (role === 'assistant' && !options.isError) {
            const actionsElement = document.createElement('div');
            actionsElement.className = 'message-actions';
            
            let actionsHTML = `
                <button class="btn btn-link btn-sm copy-message-btn" title="Copy message">
                    <i class="bi bi-clipboard"></i>
                </button>
            `;
            
            if (options.citations && options.citations.length > 0) {
                actionsHTML += `
                    <button class="btn btn-link btn-sm show-citations-btn" 
                            data-message-id="${options.messageId}" title="Show sources">
                        <i class="bi bi-book"></i> Sources (${options.citations.length})
                    </button>
                `;
            }
            
            actionsElement.innerHTML = actionsHTML;
            messageElement.appendChild(actionsElement);
        }

        // Remove welcome message if it exists
        const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const typingElement = document.createElement('div');
        typingElement.className = 'message-bubble assistant typing-indicator';
        typingElement.innerHTML = `
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        this.messagesContainer.appendChild(typingElement);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = this.messagesContainer.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        this.isTyping = false;
    }

    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }

    async loadConversationHistory() {
        try {
            const response = await fetch(`/chat/history?session_id=${this.currentSessionId}`);
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                // Clear welcome message
                this.messagesContainer.innerHTML = '';
                
                data.history.forEach(message => {
                    this.addMessageToUI('user', message.user_message);
                    this.addMessageToUI('assistant', message.assistant_response, {
                        citations: message.citations,
                        messageId: message.id,
                        responseType: message.response_type,
                        processingTime: message.processing_time
                    });
                });
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
        }
    }

    async uploadFiles() {
        const files = this.fileInput.files;
        if (!files || files.length === 0) {
            app.showToast('Please select files to upload', 'warning');
            return;
        }

        const formData = new FormData();
        for (let file of files) {
            formData.append('file', file);
        }

        // Show progress
        const progressElement = document.getElementById('uploadProgress');
        progressElement.classList.remove('d-none');

        try {
            const response = await fetch('/file/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                app.showToast('Files uploaded successfully', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                modal.hide();
                
                // Reset form
                this.fileInput.value = '';
                this.updateFileList();
                
                // Add system message
                this.addMessageToUI('assistant', `📁 Uploaded file: ${data.filename}. The file will be processed and added to the knowledge base.`);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading files:', error);
            app.showToast('Failed to upload files', 'error');
        } finally {
            progressElement.classList.add('d-none');
        }
    }

    updateFileList() {
        // Update file input label or show selected files
        const files = this.fileInput.files;
        const label = document.querySelector('label[for="fileInput"]');
        
        if (files.length > 0) {
            label.textContent = `${files.length} file(s) selected`;
        } else {
            label.textContent = 'Select files (PDF, DOC, TXT)';
        }
    }

    showCitations(messageId) {
        // Find citations for this message
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;

        // This would be populated from the message data
        // For now, show a placeholder
        const citationsModal = new bootstrap.Modal(document.getElementById('citationsModal'));
        const citationsContent = document.getElementById('citationsContent');
        
        citationsContent.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                Citations functionality will show detailed source information here.
            </div>
        `;
        
        citationsModal.show();
    }

    async showSessionStats() {
        try {
            const response = await fetch('/chat/session/stats');
            const data = await response.json();
            
            const statsModal = new bootstrap.Modal(document.getElementById('statsModal'));
            const statsContent = document.getElementById('statsContent');
            
            if (data.status === 'success') {
                statsContent.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Message Statistics</h6>
                            <ul class="list-unstyled">
                                <li><strong>Total Messages:</strong> ${data.total_messages}</li>
                                <li><strong>Query Responses:</strong> ${data.response_types?.query || 0}</li>
                                <li><strong>Summaries:</strong> ${data.response_types?.summary || 0}</li>
                                <li><strong>Comparisons:</strong> ${data.response_types?.compare || 0}</li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>Session Info</h6>
                            <ul class="list-unstyled">
                                <li><strong>Session Started:</strong> ${data.first_message ? app.formatDateTime(data.first_message) : 'N/A'}</li>
                                <li><strong>Last Activity:</strong> ${data.last_message ? app.formatDateTime(data.last_message) : 'N/A'}</li>
                                <li><strong>Avg Response Time:</strong> ${data.average_processing_time || 'N/A'}s</li>
                            </ul>
                        </div>
                    </div>
                `;
            } else {
                statsContent.innerHTML = '<div class="alert alert-warning">No statistics available for this session.</div>';
            }
            
            statsModal.show();
        } catch (error) {
            console.error('Error loading session stats:', error);
            app.showToast('Failed to load session statistics', 'error');
        }
    }

    createNewSession() {
        app.createNewSession();
    }

    async clearCurrentSession() {
        if (!confirm('Are you sure you want to clear the current session? This cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/chat/session/clear', {
                method: 'POST'
            });

            const data = await response.json();
            
            if (response.ok) {
                // Clear UI
                this.messagesContainer.innerHTML = `
                    <div class="welcome-message text-center text-muted py-5">
                        <i class="bi bi-mortarboard-fill display-4 mb-3"></i>
                        <h4>Welcome to EduSmartAI</h4>
                        <p>Your intelligent educational assistant powered by RAG technology.</p>
                        <p class="small">Ask questions about your study materials, request summaries, or compare concepts.</p>
                    </div>
                `;
                
                app.showToast('Session cleared successfully', 'success');
            } else {
                throw new Error(data.error || 'Failed to clear session');
            }
        } catch (error) {
            console.error('Error clearing session:', error);
            app.showToast('Failed to clear session', 'error');
        }
    }
}

// Initialize chat manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chatMessages')) {
        window.chatManager = new ChatManager();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatManager;
}
