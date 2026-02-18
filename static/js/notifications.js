let notificationEnabled = false;
let audioContext = null;

function initAudioContext() {
    if (!audioContext) {
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.log('Web Audio API not supported');
        }
    }
    return audioContext;
}

function playNotificationSound() {
    const ctx = initAudioContext();
    if (!ctx) return;
    
    try {
        if (ctx.state === 'suspended') {
            ctx.resume();
        }
        
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        
        oscillator.frequency.setValueAtTime(800, ctx.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(600, ctx.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
        
        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 0.3);
    } catch (e) {
        console.log('Failed to play notification sound:', e);
    }
}

function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('This browser does not support notifications');
        showNotificationStatus('unsupported');
        return;
    }
    
    if (Notification.permission === 'granted') {
        notificationEnabled = true;
        showNotificationStatus('granted');
        return;
    }
    
    if (Notification.permission === 'denied') {
        showNotificationStatus('denied');
        return;
    }
    
    showNotificationStatus('default');
    
    Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
            notificationEnabled = true;
            showNotificationStatus('granted');
            console.log('Notification permission granted');
            
            initAudioContext();
        } else if (permission === 'denied') {
            showNotificationStatus('denied');
        } else {
            showNotificationStatus('default');
        }
    });
}

function showNotificationStatus(status) {
    let statusDiv = document.getElementById('notification-status');
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'notification-status';
        statusDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; padding: 8px 12px; border-radius: 4px; font-size: 12px; z-index: 1000; transition: opacity 0.3s;';
        document.body.appendChild(statusDiv);
    }
    
    switch (status) {
        case 'granted':
            statusDiv.textContent = '🔔 通知已启用';
            statusDiv.style.background = '#4CAF50';
            statusDiv.style.color = 'white';
            break;
        case 'denied':
            statusDiv.textContent = '🔕 通知已禁用';
            statusDiv.style.background = '#f44336';
            statusDiv.style.color = 'white';
            break;
        case 'unsupported':
            statusDiv.textContent = '⚠️ 浏览器不支持通知';
            statusDiv.style.background = '#ff9800';
            statusDiv.style.color = 'white';
            break;
        case 'default':
            statusDiv.innerHTML = '🔔 <a href="#" onclick="requestNotificationPermission(); return false;" style="color: white; text-decoration: underline;">点击启用通知</a>';
            statusDiv.style.background = '#2196F3';
            statusDiv.style.color = 'white';
            break;
    }
    
    setTimeout(() => {
        statusDiv.style.opacity = '0';
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.parentNode.removeChild(statusDiv);
            }
        }, 300);
    }, 5000);
}

function showNotification(username, message) {
    if (!notificationEnabled) {
        return;
    }
    
    playNotificationSound();
    
    if (document.hasFocus()) {
        return;
    }
    
    const notification = new Notification(`💬 ${username}`, {
        body: message,
        icon: '/static/favicon.ico',
        tag: 'chatroom-message',
        requireInteraction: false,
        silent: true,
        renotify: true
    });
    
    notification.onclick = function() {
        window.focus();
        notification.close();
    };
    
    setTimeout(() => {
        notification.close();
    }, 5000);
}

window.initAudioContext = initAudioContext;
window.playNotificationSound = playNotificationSound;
window.requestNotificationPermission = requestNotificationPermission;
window.showNotificationStatus = showNotificationStatus;
window.showNotification = showNotification;
