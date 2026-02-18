let voiceClient = null;

function initVoiceChat() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const voiceWsUrl = `${wsProtocol}//${window.location.host}/ws/voice`;
    voiceClient = new VoiceChatClient(voiceWsUrl);
    
    voiceClient.onUserListUpdate = (users, screenSharer, screenActive) => {
        updateVoiceParticipants(users, screenSharer);
        updateScreenShareState(screenSharer, screenActive);
    };
    
    voiceClient.onConnected = (roomId) => {
        updateVoiceStatus('connected', `Connected to ${roomId}`);
        showVoiceControls(true);
    };
    
    voiceClient.onDisconnected = () => {
        updateVoiceStatus('disconnected', 'Disconnected');
        showVoiceControls(false);
        hideScreenShare();
    };
    
    voiceClient.onError = (error) => {
        console.error('Voice chat error:', error);
        updateVoiceStatus('error', `Error: ${error}`);
    };
    
    voiceClient.onUserJoined = (username) => {
        updateVoiceStatus('connected', `${username} joined`);
    };
    
    voiceClient.onUserLeft = (username) => {
        updateVoiceStatus('connected', `${username} left`);
    };
    
    voiceClient.onScreenStateChange = (sharer, active) => {
        updateScreenShareState(sharer, active);
    };
    
    voiceClient.onScreenFrame = (fromUser, frameData) => {
        console.log('Received screen frame from:', fromUser, 'data length:', frameData ? frameData.length : 0);
        displayScreenFrame(fromUser, frameData);
    };
}

function updateVoiceStatus(status, message) {
    const statusEl = document.getElementById('voiceStatus');
    const statusText = statusEl.querySelector('.status-text');
    statusText.textContent = message;
    statusEl.className = `voice-status ${status}`;
}

function updateVoiceParticipants(users, screenSharer) {
    const participantsEl = document.getElementById('voiceParticipants');
    const currentUser = getCurrentUser ? getCurrentUser() : '';
    
    if (!users || users.length === 0) {
        participantsEl.innerHTML = '<div class="voice-no-users">No participants</div>';
        return;
    }
    
    participantsEl.innerHTML = users.map(user => {
        const isSharing = user === screenSharer;
        const sharingClass = isSharing ? 'sharing' : '';
        const sharingIndicator = isSharing ? '<span class="sharing-indicator">📺</span>' : '';
        return `
        <div class="voice-participant ${sharingClass} ${user === currentUser ? 'self' : ''}">
            <div class="participant-avatar">${user.charAt(0).toUpperCase()}</div>
            <span class="participant-name">${user}${user === currentUser ? ' (You)' : ''}${sharingIndicator}</span>
        </div>
    `}).join('');
}

function showVoiceControls(connected) {
    document.getElementById('joinVoiceBtn').style.display = connected ? 'none' : 'inline-block';
    document.getElementById('voiceMuteBtn').style.display = connected ? 'inline-block' : 'none';
    document.getElementById('screenShareBtn').style.display = connected ? 'inline-block' : 'none';
    document.getElementById('leaveVoiceBtn').style.display = connected ? 'inline-block' : 'none';
}

async function joinVoiceChat() {
    const currentUser = getCurrentUser ? getCurrentUser() : '';
    
    if (!currentUser) {
        alert('Please enter your username first');
        return;
    }
    
    if (!voiceClient) {
        initVoiceChat();
    }
    
    try {
        updateVoiceStatus('connecting', 'Connecting...');
        await voiceClient.connect(currentUser, 'default');
    } catch (error) {
        console.error('Failed to join voice chat:', error);
        updateVoiceStatus('error', `Failed to connect: ${error.message}`);
    }
}

function leaveVoiceChat() {
    if (voiceClient) {
        voiceClient.disconnect();
        showVoiceControls(false);
        updateVoiceParticipants([]);
        updateVoiceStatus('disconnected', 'Click to join voice chat');
    }
}

function toggleVoiceMute() {
    if (voiceClient) {
        const muted = voiceClient.toggleMute();
        const muteBtn = document.getElementById('voiceMuteBtn');
        muteBtn.textContent = muted ? '🔇' : '🎤';
        muteBtn.classList.toggle('muted', muted);
    }
}

function getVoiceClient() {
    return voiceClient;
}

document.getElementById('voiceToggleBtn').addEventListener('click', function() {
    const panel = document.getElementById('voicePanel');
    panel.classList.toggle('active');
});

document.getElementById('voicePanelClose').addEventListener('click', function() {
    document.getElementById('voicePanel').classList.remove('active');
});

document.getElementById('joinVoiceBtn').addEventListener('click', joinVoiceChat);
document.getElementById('leaveVoiceBtn').addEventListener('click', leaveVoiceChat);
document.getElementById('voiceMuteBtn').addEventListener('click', toggleVoiceMute);

window.initVoiceChat = initVoiceChat;
window.updateVoiceStatus = updateVoiceStatus;
window.updateVoiceParticipants = updateVoiceParticipants;
window.showVoiceControls = showVoiceControls;
window.joinVoiceChat = joinVoiceChat;
window.leaveVoiceChat = leaveVoiceChat;
window.toggleVoiceMute = toggleVoiceMute;
window.getVoiceClient = getVoiceClient;
