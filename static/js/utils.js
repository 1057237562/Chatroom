function scrollToBottom(element, smooth = true) {
    if (!element) return;
    if (smooth && 'scrollBehavior' in document.documentElement.style) {
        element.scrollTo({
            top: element.scrollHeight,
            behavior: 'smooth'
        });
    } else {
        element.scrollTop = element.scrollHeight;
    }
}

function saveUsername(username) {
    localStorage.setItem('chatroom_username', username);
}

function loadUsername() {
    return localStorage.getItem('chatroom_username') || '';
}

function formatTime(date = new Date()) {
    const h = String(date.getHours()).padStart(2, '0');
    const m = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

window.scrollToBottom = scrollToBottom;
window.saveUsername = saveUsername;
window.loadUsername = loadUsername;
window.formatTime = formatTime;
window.escapeHtml = escapeHtml;
