// Toast Notification System

const TOAST_ICONS = {
    success: '&#10003;',
    error: '&#10007;',
    warning: '&#9888;',
    info: '&#8505;'
};

const TOAST_TITLES = {
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info'
};

// Create toast container if it doesn't exist
function getToastContainer() {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {object} options - Optional settings
 * @param {string} options.title - Custom title (defaults to type name)
 * @param {number} options.duration - Duration in ms (default: 5000, 0 = no auto-close)
 */
function showToast(message, type = 'info', options = {}) {
    const container = getToastContainer();
    const title = options.title || TOAST_TITLES[type] || 'Notification';
    const duration = options.duration !== undefined ? options.duration : 5000;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${TOAST_ICONS[type] || TOAST_ICONS.info}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this.parentElement)">&times;</button>
    `;

    container.appendChild(toast);

    // Auto-close after duration
    if (duration > 0) {
        setTimeout(() => {
            closeToast(toast);
        }, duration);
    }

    return toast;
}

/**
 * Close a toast notification with animation
 * @param {HTMLElement} toast - The toast element to close
 */
function closeToast(toast) {
    if (!toast || toast.classList.contains('toast-exit')) return;

    toast.classList.add('toast-exit');
    setTimeout(() => {
        toast.remove();
    }, 300);
}

// Convenience functions
function toastSuccess(message, options = {}) {
    return showToast(message, 'success', options);
}

function toastError(message, options = {}) {
    return showToast(message, 'error', options);
}

function toastWarning(message, options = {}) {
    return showToast(message, 'warning', options);
}

function toastInfo(message, options = {}) {
    return showToast(message, 'info', options);
}
