function updateScreenShareState(sharer, active) {
    const screenBtn = document.getElementById('screenShareBtn');
    const voiceClient = getVoiceClient ? getVoiceClient() : null;
    const currentUser = getCurrentUser ? getCurrentUser() : '';
    
    if (sharer && sharer !== currentUser) {
        screenBtn.style.display = 'none';
        screenBtn.classList.remove('active');
    } else if (voiceClient && voiceClient.isConnected) {
        screenBtn.style.display = 'inline-block';
        if (active && sharer === currentUser) {
            screenBtn.classList.add('active');
        } else {
            screenBtn.classList.remove('active');
        }
    }
    
    if (active && sharer) {
        showScreenShareContainer(sharer);
    } else {
        hideScreenShare();
    }
}

function showScreenShareContainer(sharer) {
    const container = document.getElementById('screenShareContainer');
    const title = document.getElementById('screenShareTitle');
    title.textContent = `${sharer}'s Screen`;
    container.style.display = 'flex';
}

function hideScreenShare() {
    const container = document.getElementById('screenShareContainer');
    container.style.display = 'none';
    const overlay = document.getElementById('screenShareOverlay');
    overlay.classList.remove('hidden');
}

function displayScreenFrame(fromUser, frameData) {
    const img = document.getElementById('screenShareImage');
    const overlay = document.getElementById('screenShareOverlay');
    
    img.src = frameData;
    overlay.classList.add('hidden');
    
    showScreenShareContainer(fromUser);
}

async function toggleScreenShare() {
    const voiceClient = getVoiceClient ? getVoiceClient() : null;
    
    if (!voiceClient || !voiceClient.isConnected) {
        return;
    }
    
    const screenBtn = document.getElementById('screenShareBtn');
    
    if (voiceClient.isCurrentlyScreenSharing()) {
        voiceClient.stopScreenShare();
        screenBtn.classList.remove('active');
    } else {
        const success = await voiceClient.startScreenShare();
        if (success) {
            screenBtn.classList.add('active');
        }
    }
}

function initScreenShareFullscreen() {
    const container = document.getElementById('screenShareContainer');
    const fullscreenBtn = document.getElementById('screenShareFullscreenBtn');
    let savedState = null;
    
    fullscreenBtn.addEventListener('click', function() {
        if (container.classList.contains('fullscreen')) {
            container.classList.remove('fullscreen');
            if (savedState) {
                container.style.width = savedState.width;
                container.style.height = savedState.height;
                container.style.left = savedState.left;
                container.style.top = savedState.top;
                savedState = null;
            }
        } else {
            savedState = {
                width: container.style.width || container.offsetWidth + 'px',
                height: container.style.height || container.offsetHeight + 'px',
                left: container.style.left || container.offsetLeft + 'px',
                top: container.style.top || container.offsetTop + 'px'
            };
            container.classList.add('fullscreen');
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && container.classList.contains('fullscreen')) {
            container.classList.remove('fullscreen');
            if (savedState) {
                container.style.width = savedState.width;
                container.style.height = savedState.height;
                container.style.left = savedState.left;
                container.style.top = savedState.top;
                savedState = null;
            }
        }
    });
}

function initScreenShareDrag() {
    const container = document.getElementById('screenShareContainer');
    const header = container.querySelector('.screen-share-header');
    let isDragging = false;
    let startX, startY, initialX, initialY;
    
    header.addEventListener('mousedown', function(e) {
        if (e.target.classList.contains('screen-share-close') || 
            e.target.closest('.screen-share-fullscreen-btn') ||
            container.classList.contains('fullscreen')) {
            return;
        }
        isDragging = true;
        container.classList.add('dragging');
        
        const rect = container.getBoundingClientRect();
        startX = e.clientX;
        startY = e.clientY;
        initialX = rect.left;
        initialY = rect.top;
        
        container.style.transform = 'none';
        container.style.left = initialX + 'px';
        container.style.top = initialY + 'px';
        
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        let newX = initialX + deltaX;
        let newY = initialY + deltaY;
        
        const maxX = window.innerWidth - container.offsetWidth;
        const maxY = window.innerHeight - container.offsetHeight;
        
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));
        
        container.style.left = newX + 'px';
        container.style.top = newY + 'px';
    });
    
    document.addEventListener('mouseup', function() {
        if (isDragging) {
            isDragging = false;
            container.classList.remove('dragging');
        }
    });
}

function initScreenShareResize() {
    const container = document.getElementById('screenShareContainer');
    const handles = container.querySelectorAll('.screen-share-resize-handle');
    let isResizing = false;
    let currentHandle = null;
    let startX, startY, startWidth, startHeight, startLeft, startTop;
    const minWidth = 320;
    const minHeight = 200;
    
    handles.forEach(handle => {
        handle.addEventListener('mousedown', function(e) {
            if (container.classList.contains('fullscreen')) {
                return;
            }
            isResizing = true;
            container.classList.add('resizing');
            currentHandle = this.dataset.resize;
            
            startX = e.clientX;
            startY = e.clientY;
            startWidth = container.offsetWidth;
            startHeight = container.offsetHeight;
            startLeft = container.offsetLeft;
            startTop = container.offsetTop;
            
            e.preventDefault();
            e.stopPropagation();
        });
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        
        let newWidth = startWidth;
        let newHeight = startHeight;
        let newLeft = startLeft;
        let newTop = startTop;
        
        switch (currentHandle) {
            case 'se':
                newWidth = Math.max(minWidth, startWidth + deltaX);
                newHeight = Math.max(minHeight, startHeight + deltaY);
                break;
            case 'sw':
                newWidth = Math.max(minWidth, startWidth - deltaX);
                newHeight = Math.max(minHeight, startHeight + deltaY);
                newLeft = startLeft + (startWidth - newWidth);
                break;
            case 'ne':
                newWidth = Math.max(minWidth, startWidth + deltaX);
                newHeight = Math.max(minHeight, startHeight - deltaY);
                newTop = startTop + (startHeight - newHeight);
                break;
            case 'nw':
                newWidth = Math.max(minWidth, startWidth - deltaX);
                newHeight = Math.max(minHeight, startHeight - deltaY);
                newLeft = startLeft + (startWidth - newWidth);
                newTop = startTop + (startHeight - newHeight);
                break;
        }
        
        const maxWidth = window.innerWidth - newLeft;
        const maxHeight = window.innerHeight - newTop;
        
        newWidth = Math.min(newWidth, maxWidth);
        newHeight = Math.min(newHeight, maxHeight);
        
        container.style.width = newWidth + 'px';
        container.style.height = newHeight + 'px';
        container.style.left = newLeft + 'px';
        container.style.top = newTop + 'px';
    });
    
    document.addEventListener('mouseup', function() {
        isResizing = false;
        currentHandle = null;
        container.classList.remove('resizing');
    });
}

document.getElementById('screenShareBtn').addEventListener('click', toggleScreenShare);

document.getElementById('screenShareClose').addEventListener('click', function() {
    const container = document.getElementById('screenShareContainer');
    container.style.display = 'none';
    if (container.classList.contains('fullscreen')) {
        container.classList.remove('fullscreen');
    }
});

window.updateScreenShareState = updateScreenShareState;
window.showScreenShareContainer = showScreenShareContainer;
window.hideScreenShare = hideScreenShare;
window.displayScreenFrame = displayScreenFrame;
window.toggleScreenShare = toggleScreenShare;
window.initScreenShareFullscreen = initScreenShareFullscreen;
window.initScreenShareDrag = initScreenShareDrag;
window.initScreenShareResize = initScreenShareResize;
