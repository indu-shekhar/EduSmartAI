/**
 * Main application JavaScript
 * Handles global functionality and utilities
 */

class EduSmartAI {
    constructor() {
        this.sessionId = this.getSessionId();
        this.isProcessing = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupHTMX();
        this.setupMarkdown();
        this.setupToasts();
    }

    setupEventListeners() {
        // New session button
        document.getElementById('newSessionBtn')?.addEventListener('click', () => {
            this.createNewSession();
        });

        // Global error handler
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.showToast('An unexpected error occurred', 'error');
        });
    }

    setupHTMX() {
        // HTMX event handlers
        document.addEventListener('htmx:beforeRequest', (event) => {
            this.isProcessing = true;
            this.showProcessing();
        });

        document.addEventListener('htmx:afterRequest', (event) => {
            this.isProcessing = false;
            this.hideProcessing();
        });

        document.addEventListener('htmx:responseError', (event) => {
            this.showToast('Request failed. Please try again.', 'error');
        });
    }

    setupMarkdown() {
        // Configure marked.js
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return code;
                },
                breaks: true,
                gfm: true
            });
        }
    }

    setupToasts() {
        // Initialize Bootstrap toasts
        this.toastElement = document.getElementById('alertToast');
        this.toast = this.toastElement ? new bootstrap.Toast(this.toastElement) : null;
    }

    getSessionId() {
        let sessionId = localStorage.getItem('edusmartai_session_id');
        if (!sessionId) {
            sessionId = this.generateUUID();
            localStorage.setItem('edusmartai_session_id', sessionId);
        }
        return sessionId;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    createNewSession() {
        fetch('/chat/session/new', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.session_id) {
                this.sessionId = data.session_id;
                localStorage.setItem('edusmartai_session_id', this.sessionId);
                this.showToast('New session started', 'success');
                // Reload the page to refresh the chat
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error creating new session:', error);
            this.showToast('Failed to create new session', 'error');
        });
    }

    showToast(message, type = 'info') {
        if (!this.toast) return;

        const toastMessage = document.getElementById('toastMessage');
        const toastHeader = this.toastElement.querySelector('.toast-header i');
        
        // Update message
        toastMessage.textContent = message;
        
        // Update icon and color based on type
        const iconClasses = {
            'success': 'bi-check-circle-fill text-success',
            'error': 'bi-exclamation-circle-fill text-danger',
            'warning': 'bi-exclamation-triangle-fill text-warning',
            'info': 'bi-info-circle-fill text-primary'
        };
        
        toastHeader.className = `${iconClasses[type] || iconClasses.info} me-2`;
        
        this.toast.show();
    }

    showProcessing() {
        // Add processing indicator to send button
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
        }
    }

    hideProcessing() {
        // Remove processing indicator
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="bi bi-send-fill"></i>';
        }
    }

    renderMarkdown(text) {
        if (typeof marked !== 'undefined') {
            return marked.parse(text);
        }
        return text.replace(/\n/g, '<br>');
    }

    formatDateTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString();
    }

    formatTimeAgo(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'just now';
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    async apiCall(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

// Utility functions
window.EduSmartAI = {
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            app.showToast('Copied to clipboard', 'success');
        }).catch(() => {
            app.showToast('Failed to copy to clipboard', 'error');
        });
    },

    downloadText: function(text, filename) {
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new EduSmartAI();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EduSmartAI;
}
