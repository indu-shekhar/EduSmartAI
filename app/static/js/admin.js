/**
 * Admin dashboard JavaScript
 * Handles admin interface and system monitoring
 */

class AdminDashboard {
    constructor() {
        this.refreshInterval = null;
        this.processingModal = null;
        this.configModal = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupModals();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Index management buttons
        document.getElementById('refreshIndexBtn')?.addEventListener('click', () => {
            this.refreshIndex(false);
        });

        document.getElementById('rebuildIndexBtn')?.addEventListener('click', () => {
            this.refreshIndex(true);
        });

        document.getElementById('reIngestBtn')?.addEventListener('click', () => {
            this.triggerReingestion();
        });

        // Maintenance buttons
        document.getElementById('cleanupBtn')?.addEventListener('click', () => {
            this.performCleanup();
        });

        document.getElementById('exportLogsBtn')?.addEventListener('click', () => {
            this.exportLogs();
        });

        document.getElementById('viewConfigBtn')?.addEventListener('click', () => {
            this.viewConfiguration();
        });

        // Refresh buttons
        document.getElementById('refreshLogsBtn')?.addEventListener('click', () => {
            this.loadLogs();
        });

        // Manual refresh
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshDashboard();
            }
        });
    }

    setupModals() {
        this.processingModal = new bootstrap.Modal(document.getElementById('processingModal'), {
            backdrop: 'static',
            keyboard: false
        });

        this.configModal = new bootstrap.Modal(document.getElementById('configModal'));
    }

    async loadInitialData() {
        await Promise.all([
            this.loadSystemHealth(),
            this.loadMetrics(),
            this.loadLogs(),
            this.loadActiveSessions()
        ]);
    }

    startAutoRefresh() {
        // Refresh data every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadSystemHealth();
            this.loadMetrics();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async loadSystemHealth() {
        try {
            const response = await fetch('/admin/health');
            const data = await response.json();

            const statusElement = document.getElementById('systemStatus');
            if (statusElement) {
                statusElement.textContent = data.status || 'Unknown';
                statusElement.className = data.status === 'healthy' ? 'text-success' : 'text-danger';
            }

            // Update index status
            const indexStatusElement = document.getElementById('indexStatus');
            if (indexStatusElement && data.rag_system) {
                indexStatusElement.textContent = data.rag_system === 'success' ? 'Ready' : 'Error';
                indexStatusElement.className = data.rag_system === 'success' ? 'text-success' : 'text-warning';
            }

        } catch (error) {
            console.error('Error loading system health:', error);
            const statusElement = document.getElementById('systemStatus');
            if (statusElement) {
                statusElement.textContent = 'Error';
                statusElement.className = 'text-danger';
            }
        }
    }

    async loadMetrics() {
        try {
            const response = await fetch('/admin/metrics');
            const data = await response.json();

            if (data.database_metrics) {
                const totalMessagesElement = document.getElementById('totalMessages');
                const totalFilesElement = document.getElementById('totalFiles');

                if (totalMessagesElement) {
                    totalMessagesElement.textContent = data.database_metrics.total_messages || 0;
                }

                if (totalFilesElement) {
                    totalFilesElement.textContent = data.database_metrics.total_files || 0;
                }
            }

            // Update processing activity
            this.updateProcessingActivity(data.processing_metrics);

        } catch (error) {
            console.error('Error loading metrics:', error);
        }
    }

    async loadLogs() {
        try {
            const response = await fetch('/admin/logs');
            const data = await response.json();

            const logsTableBody = document.getElementById('logsTableBody');
            if (logsTableBody && data.logs) {
                if (data.logs.length === 0) {
                    logsTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No logs available</td></tr>';
                } else {
                    logsTableBody.innerHTML = data.logs.map(log => {
                        const duration = log.end_time && log.start_time 
                            ? this.calculateDuration(log.start_time, log.end_time)
                            : 'N/A';

                        const statusBadge = this.getStatusBadge(log.status);

                        return `
                            <tr>
                                <td>${app.formatDateTime(log.start_time)}</td>
                                <td>${log.operation_type}</td>
                                <td>${statusBadge}</td>
                                <td>${log.files_processed || 0} / ${log.total_files || 0}</td>
                                <td>${duration}</td>
                            </tr>
                        `;
                    }).join('');
                }
            }

        } catch (error) {
            console.error('Error loading logs:', error);
        }
    }

    async loadActiveSessions() {
        try {
            const response = await fetch('/admin/sessions');
            const data = await response.json();

            const activeSessionsElement = document.getElementById('activeSessions');
            if (activeSessionsElement && data.active_sessions) {
                if (data.active_sessions.length === 0) {
                    activeSessionsElement.innerHTML = '<p class="text-muted">No active sessions</p>';
                } else {
                    activeSessionsElement.innerHTML = `
                        <div class="list-group">
                            ${data.active_sessions.map(session => `
                                <div class="list-group-item">
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">Session ${session.session_id.substring(0, 8)}...</h6>
                                        <small>${app.formatTimeAgo(session.last_activity)}</small>
                                    </div>
                                    <p class="mb-1">${session.message_count} messages</p>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            }

        } catch (error) {
            console.error('Error loading active sessions:', error);
        }
    }

    updateProcessingActivity(processingMetrics) {
        const activityElement = document.getElementById('processingActivity');
        if (!activityElement || !processingMetrics) return;

        if (processingMetrics.latest_indexing) {
            const latest = processingMetrics.latest_indexing;
            const statusBadge = this.getStatusBadge(latest.status);
            
            activityElement.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-title">Latest: ${latest.operation_type}</h6>
                        <p class="card-text">
                            ${statusBadge}
                            <br>
                            <small class="text-muted">
                                Started: ${app.formatDateTime(latest.start_time)}
                                ${latest.end_time ? `<br>Completed: ${app.formatDateTime(latest.end_time)}` : ''}
                            </small>
                        </p>
                    </div>
                </div>
            `;
        } else {
            activityElement.innerHTML = '<p class="text-muted">No recent processing activity</p>';
        }
    }

    async refreshIndex(forceRebuild = false) {
        const action = forceRebuild ? 'Rebuilding' : 'Refreshing';
        this.showProcessingModal(`${action} vector index...`);

        try {
            const response = await fetch('/admin/refresh-index', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    force_rebuild: forceRebuild
                })
            });

            const data = await response.json();

            if (response.ok) {
                app.showToast(`Index ${forceRebuild ? 'rebuilt' : 'refreshed'} successfully`, 'success');
            } else {
                throw new Error(data.error || 'Operation failed');
            }

        } catch (error) {
            console.error('Error refreshing index:', error);
            app.showToast(`Failed to ${forceRebuild ? 'rebuild' : 'refresh'} index`, 'error');
        } finally {
            this.hideProcessingModal();
            this.loadMetrics(); // Refresh metrics
        }
    }

    async triggerReingestion() {
        this.showProcessingModal('Re-ingesting files...');

        try {
            const response = await fetch('/admin/re-ingest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (response.ok) {
                app.showToast('Re-ingestion completed successfully', 'success');
            } else {
                throw new Error(data.error || 'Re-ingestion failed');
            }

        } catch (error) {
            console.error('Error triggering re-ingestion:', error);
            app.showToast('Failed to trigger re-ingestion', 'error');
        } finally {
            this.hideProcessingModal();
            this.loadMetrics(); // Refresh metrics
        }
    }

    async performCleanup() {
        const days = prompt('Delete data older than how many days?', '7');
        if (!days || isNaN(days)) return;

        this.showProcessingModal('Cleaning up old data...');

        try {
            const response = await fetch('/admin/cleanup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    days: parseInt(days)
                })
            });

            const data = await response.json();

            if (response.ok) {
                app.showToast('Cleanup completed successfully', 'success');
            } else {
                throw new Error(data.error || 'Cleanup failed');
            }

        } catch (error) {
            console.error('Error during cleanup:', error);
            app.showToast('Failed to perform cleanup', 'error');
        } finally {
            this.hideProcessingModal();
            this.loadMetrics(); // Refresh metrics
        }
    }

    async exportLogs() {
        try {
            const response = await fetch('/admin/logs');
            const data = await response.json();

            if (data.logs) {
                const logsText = data.logs.map(log => {
                    return `[${log.start_time}] ${log.operation_type}: ${log.status} (${log.files_processed}/${log.total_files} files)`;
                }).join('\n');

                const filename = `edusmartai-logs-${new Date().toISOString().split('T')[0]}.txt`;
                window.EduSmartAI.downloadText(logsText, filename);
                app.showToast('Logs exported successfully', 'success');
            }

        } catch (error) {
            console.error('Error exporting logs:', error);
            app.showToast('Failed to export logs', 'error');
        }
    }

    async viewConfiguration() {
        try {
            const response = await fetch('/admin/config');
            const data = await response.json();

            const configContent = document.getElementById('configContent');
            if (configContent) {
                configContent.textContent = JSON.stringify(data.configuration, null, 2);
            }

            this.configModal.show();

        } catch (error) {
            console.error('Error loading configuration:', error);
            app.showToast('Failed to load configuration', 'error');
        }
    }

    showProcessingModal(message) {
        const processingMessage = document.getElementById('processingMessage');
        if (processingMessage) {
            processingMessage.textContent = message;
        }
        this.processingModal.show();
    }

    hideProcessingModal() {
        this.processingModal.hide();
    }

    refreshDashboard() {
        app.showToast('Refreshing dashboard...', 'info');
        this.loadInitialData();
    }

    getStatusBadge(status) {
        const badges = {
            'completed': '<span class="badge bg-success">Completed</span>',
            'running': '<span class="badge bg-primary">Running</span>',
            'failed': '<span class="badge bg-danger">Failed</span>',
            'pending': '<span class="badge bg-warning">Pending</span>'
        };
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    calculateDuration(startTime, endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);

        if (diffMinutes > 0) {
            return `${diffMinutes}m ${diffSeconds % 60}s`;
        }
        return `${diffSeconds}s`;
    }

    // Cleanup when page unloads
    destroy() {
        this.stopAutoRefresh();
    }
}

// Initialize admin dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('systemStatus')) {
        window.adminDashboard = new AdminDashboard();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.adminDashboard) {
        window.adminDashboard.destroy();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminDashboard;
}
