window.addEventListener('load', function() {
    requestNotificationPermission();
    const savedUsername = loadUsername();
    if (savedUsername) {
        const usernameInput = document.getElementById('username');
        usernameInput.value = savedUsername;
        setCurrentUser(savedUsername);
        if (isWsReady()) {
            getWs().send(savedUsername);
        }
    }
    loadInitialHistory();
    initVoiceChat();
    
    initScreenShareFullscreen();
    initScreenShareDrag();
    initScreenShareResize();
    
    const inputArea = document.getElementById('inputArea');
    const input = document.getElementById('input');
    setCommandAutocomplete(new CommandAutocomplete(input, inputArea));
});
