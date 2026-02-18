const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);
let wsReady = false;

const messagesDiv = document.getElementById('messages');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const userListDiv = document.getElementById('userList');
const usernameInput = document.getElementById('username');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const historySearch = document.getElementById('historySearch');
const historyFilter = document.getElementById('historyFilter');
const loadHistoryBtn = document.getElementById('loadHistoryBtn');
const historyList = document.getElementById('historyList');
const historyLoading = document.getElementById('historyLoading');

let currentUser = '';
let historyOffset = 0;
const historyPageSize = 50;
let hasHistoryLoaded = false;
let firstNewMessageSent = false;
let commandAutocomplete = null;

ws.onmessage = function(event) {
    try {
        const data = JSON.parse(event.data);
        if (data.type === 'userlist') {
            userListDiv.innerHTML = '';
            data.users.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                
                const statusIndicator = document.createElement('div');
                statusIndicator.className = 'user-status';
                div.appendChild(statusIndicator);
                
                const usernameSpan = document.createElement('span');
                usernameSpan.textContent = u;
                div.appendChild(usernameSpan);
                
                userListDiv.appendChild(div);
            });
        } else if (data.type === 'message') {
            const msg = document.createElement('div');
            msg.className = 'message-item';
            
            if (hasHistoryLoaded && !firstNewMessageSent) {
                const newMessageDivider = document.createElement('div');
                newMessageDivider.className = 'new-messages-divider';
                newMessageDivider.innerHTML = '<span class="divider-text" style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);">New Messages</span>';
                newMessageDivider.style.opacity = '0';
                newMessageDivider.style.transform = 'translateY(-10px)';
                messagesDiv.appendChild(newMessageDivider);
                
                setTimeout(() => {
                    newMessageDivider.style.transition = 'all 0.5s ease';
                    newMessageDivider.style.opacity = '1';
                    newMessageDivider.style.transform = 'translateY(0)';
                }, 50);
                
                firstNewMessageSent = true;
            }
            
            let username = '';
            let messageText = '';
            let isOwn = false;
            
            if (data.username) {
                username = data.username;
                messageText = data.text;
                isOwn = (username === currentUser);
            } else {
                const match = data.text.match(/^([^:]+):\s([\s\S]*)$/);
                if (match) {
                    username = match[1];
                    messageText = match[2];
                    isOwn = (username === currentUser);
                } else {
                    messageText = data.text;
                }
            }
            
            if (isOwn) {
                msg.className += ' own';
            }
            
            const msgMeta = document.createElement('div');
            msgMeta.className = 'msg-meta';
            
            if (username) {
                const msgUser = document.createElement('span');
                msgUser.className = 'msg-user';
                msgUser.textContent = username;
                msgMeta.appendChild(msgUser);
            }
            
            const msgTime = document.createElement('span');
            msgTime.className = 'msg-time';
            msgTime.textContent = data.timestamp || formatTime();
            msgMeta.appendChild(msgTime);
            
            msg.appendChild(msgMeta);
            
            const msgContent = document.createElement('div');
            msgContent.className = 'msg-text';
            msgContent.textContent = messageText;
            msg.appendChild(msgContent);
            
            messagesDiv.appendChild(msg);
            scrollToBottom(messagesDiv, true);
            
            if (username && messageText && !isOwn) {
                showNotification(username, messageText);
            }
        } else if (data.type === 'error') {
            alert(data.text);
        } else if (data.type === 'info') {
            const info = document.createElement('div');
            info.className = 'message-item info-item';
            info.textContent = data.text;
            messagesDiv.appendChild(info);
            scrollToBottom(messagesDiv, true);
        } else if (data.type === 'private') {
            const msg = document.createElement('div');
            msg.className = 'message-item private-item';
            
            const msgMeta = document.createElement('div');
            msgMeta.className = 'msg-meta';
            
            const msgUser = document.createElement('span');
            msgUser.className = 'msg-user';
            msgUser.textContent = `[Private from ${data.from}]`;
            msgMeta.appendChild(msgUser);
            
            const msgTime = document.createElement('span');
            msgTime.className = 'msg-time';
            msgTime.textContent = formatTime();
            msgMeta.appendChild(msgTime);
            
            msg.appendChild(msgMeta);
            
            const msgContent = document.createElement('div');
            msgContent.className = 'msg-text';
            msgContent.textContent = data.text;
            msg.appendChild(msgContent);
            
            messagesDiv.appendChild(msg);
            scrollToBottom(messagesDiv, true);
            
            showNotification(`[Private] ${data.from}`, data.text);
        }
    } catch (e) {
        console.error('Invalid message', event.data);
    }
};

sendBtn.onclick = function() {
    const username = usernameInput.value.trim();
    const text = input.value.trim();
    
    if (!wsReady) {
        alert('Connection not ready. Please wait...');
        return;
    }
    
    if (!username) {
        alert('Please enter a username first');
        usernameInput.focus();
        return;
    }
    
    if (!text) {
        alert('Please enter a message');
        input.focus();
        return;
    }
    
    if (currentUser !== username) {
        currentUser = username;
        saveUsername(username);
        ws.send(username);
    }
    
    ws.send(text);
    input.value = '';
    input.focus();
};

input.addEventListener('keydown', function(e) {
    if (commandAutocomplete && commandAutocomplete.isVisible) {
        if (e.key === 'Enter' && commandAutocomplete.selectedIndex >= 0) {
            return;
        }
    }
    
    if (e.key === 'Enter') {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            const value = this.value;
            this.value = value.substring(0, start) + '\n' + value.substring(end);
            this.selectionStart = this.selectionEnd = start + 1;
            return;
        }
        e.preventDefault();
        sendBtn.click();
    }
});

usernameInput.addEventListener('blur', function() {
    const username = this.value.trim();
    if (username && currentUser !== username && wsReady) {
        currentUser = username;
        saveUsername(username);
        ws.send(username);
    }
});

usernameInput.addEventListener('keyup', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        input.focus();
    }
});

fileInput.addEventListener('change', async function() {
    const file = fileInput.files[0];
    if (!file) return;
    
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    try {
        uploadStatus.textContent = 'Uploading...';
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.url) {
            const imgContainer = document.createElement('div');
            imgContainer.className = 'message-item';
            
            const img = document.createElement('img');
            img.src = data.url;
            img.style.maxWidth = '300px';
            img.style.maxHeight = '300px';
            img.style.margin = '8px 0';
            
            imgContainer.appendChild(img);
            messagesDiv.appendChild(imgContainer);
            scrollToBottom(messagesDiv, true);
        }
        uploadStatus.textContent = '';
        fileInput.value = '';
    } catch (error) {
        uploadStatus.textContent = 'Upload failed';
        console.error('Upload error:', error);
    }
});

ws.addEventListener('open', function() {
    wsReady = true;
    const savedUsername = loadUsername();
    if (savedUsername) {
        usernameInput.value = savedUsername;
        currentUser = savedUsername;
        ws.send(savedUsername);
    }
    if (typeof initVOIP === 'function') {
        initVOIP();
    }
});

async function loadHistory() {
    try {
        historyLoading.style.display = 'block';
        const keyword = historySearch.value.trim();
        const username = historyFilter.value.trim();
        
        let url = `/api/history?limit=${historyPageSize}&offset=${historyOffset}`;
        if (username) url += `&username=${encodeURIComponent(username)}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success && data.messages) {
            if (historyOffset === 0) {
                historyList.innerHTML = '';
            }
            
            data.messages.forEach(msg => {
                const msgDiv = document.createElement('div');
                msgDiv.className = 'history-message';
                msgDiv.innerHTML = `<strong>${msg.username}</strong> <span class="time">${msg.timestamp}</span><br/><span class="content">${escapeHtml(msg.content)}</span>`;
                historyList.appendChild(msgDiv);
            });
            
            historyOffset += data.messages.length;
            
            if (data.messages.length < historyPageSize) {
                const endMsg = document.createElement('div');
                endMsg.className = 'history-end';
                endMsg.textContent = '--- End of history ---';
                historyList.appendChild(endMsg);
            }
        }
        historyLoading.style.display = 'none';
    } catch (error) {
        console.error('Error loading history:', error);
        historyLoading.style.display = 'none';
    }
}

loadHistoryBtn.addEventListener('click', function() {
    historyOffset = 0;
    loadHistory();
});

historySearch.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        historyOffset = 0;
        loadHistory();
    }
});

historyFilter.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        historyOffset = 0;
        loadHistory();
    }
});

const historyContainer = document.querySelector('.history-container');
historyContainer.addEventListener('scroll', function() {
    if (historyContainer.scrollTop + historyContainer.clientHeight >= historyContainer.scrollHeight - 10) {
        const endMsg = historyList.querySelector('.history-end');
        if (!endMsg) {
            loadHistory();
        }
    }
});

async function loadInitialHistory() {
    try {
        const res = await fetch('/api/history/initial?limit=20');
        const data = await res.json();
        
        if (data.success && data.messages.length > 0) {
            const reversedMessages = [...data.messages].reverse();
            reversedMessages.forEach((msg, index) => {
                const msgDiv = document.createElement('div');
                msgDiv.className = 'message-item history-message-item';
                msgDiv.style.opacity = '0';
                msgDiv.style.transform = 'translateY(20px)';
                
                const msgMeta = document.createElement('div');
                msgMeta.className = 'msg-meta';
                
                const msgUser = document.createElement('span');
                msgUser.className = 'msg-user';
                msgUser.textContent = msg.username;
                msgMeta.appendChild(msgUser);
                
                const msgTime = document.createElement('span');
                msgTime.className = 'msg-time';
                msgTime.textContent = msg.timestamp;
                msgMeta.appendChild(msgTime);
                
                msgDiv.appendChild(msgMeta);
                
                const msgContent = document.createElement('div');
                msgContent.className = 'msg-text';
                msgContent.textContent = msg.content;
                msgDiv.appendChild(msgContent);
                
                messagesDiv.appendChild(msgDiv);
                
                setTimeout(() => {
                    msgDiv.style.transition = 'all 0.3s ease';
                    msgDiv.style.opacity = '1';
                    msgDiv.style.transform = 'translateY(0)';
                }, 150 + (index * 50));
            });
            
            setTimeout(() => {
                scrollToBottom(messagesDiv, true);
                hasHistoryLoaded = true;
            }, 150 + (reversedMessages.length * 50));
        } else {
            hasHistoryLoaded = true;
        }
    } catch (error) {
        console.error('Error loading initial history:', error);
        hasHistoryLoaded = true;
    }
}

function getCurrentUser() {
    return currentUser;
}

function setCurrentUser(username) {
    currentUser = username;
}

function getWs() {
    return ws;
}

function isWsReady() {
    return wsReady;
}

function getCommandAutocomplete() {
    return commandAutocomplete;
}

function setCommandAutocomplete(instance) {
    commandAutocomplete = instance;
}

window.ws = ws;
window.getCurrentUser = getCurrentUser;
window.setCurrentUser = setCurrentUser;
window.getWs = getWs;
window.isWsReady = isWsReady;
window.getCommandAutocomplete = getCommandAutocomplete;
window.setCommandAutocomplete = setCommandAutocomplete;
window.loadHistory = loadHistory;
window.loadInitialHistory = loadInitialHistory;
