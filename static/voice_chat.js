class VoiceChatClient {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.scriptProcessor = null;
        this.audioQueue = {};
        this.isPlaying = false;
        this.isConnected = false;
        this.currentRoom = null;
        this.username = null;
        this.muted = false;
        
        this.screenStream = null;
        this.screenCanvas = null;
        this.screenCtx = null;
        this.isScreenSharing = false;
        this.screenSharer = null;
        this.frameRate = 10;
        this.quality = 0.7;
        this.maxWidth = 1280;
        this.maxHeight = 720;
        
        this.onUserListUpdate = null;
        this.onConnected = null;
        this.onDisconnected = null;
        this.onError = null;
        this.onUserJoined = null;
        this.onUserLeft = null;
        this.onScreenStateChange = null;
        this.onScreenFrame = null;
        
        this.sampleRate = 16000;
        this.bufferSize = 4096;
    }
    
    async connect(username, roomId = 'default') {
        this.username = username;
        this.currentRoom = roomId;
        
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = async () => {
                console.log('Voice chat WebSocket connected');
                this.ws.send(JSON.stringify({
                    type: 'join',
                    room_id: roomId,
                    username: username
                }));
                
                try {
                    await this._initAudio();
                    this.isConnected = true;
                    if (this.onConnected) {
                        this.onConnected(roomId);
                    }
                    resolve();
                } catch (error) {
                    console.error('Failed to initialize audio:', error);
                    reject(error);
                }
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this._handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse voice message:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('Voice chat WebSocket error:', error);
                if (this.onError) {
                    this.onError('Connection error');
                }
                reject(error);
            };
            
            this.ws.onclose = () => {
                console.log('Voice chat WebSocket closed');
                this._cleanup();
                if (this.onDisconnected) {
                    this.onDisconnected();
                }
            };
        });
    }
    
    async _initAudio() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: this.sampleRate
        });
        
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: this.sampleRate
            }
        });
        
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.scriptProcessor = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
        
        this.scriptProcessor.onaudioprocess = (event) => {
            if (this.muted || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const inputData = event.inputBuffer.getChannelData(0);
            const pcmData = this._floatTo16BitPCM(inputData);
            this._sendAudio(pcmData);
        };
        
        source.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioContext.destination);
        
        console.log('Audio initialized');
    }
    
    _floatTo16BitPCM(float32Array) {
        const buffer = new ArrayBuffer(float32Array.length * 2);
        const view = new DataView(buffer);
        for (let i = 0; i < float32Array.length; i++) {
            let s = Math.max(-1, Math.min(1, float32Array[i]));
            view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return new Int16Array(buffer);
    }
    
    _16BitPCMToFloat(int16Array) {
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            const s = int16Array[i];
            float32Array[i] = s < 0 ? s / 0x8000 : s / 0x7FFF;
        }
        return float32Array;
    }
    
    _sendAudio(pcmData) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const uint8Data = new Uint8Array(pcmData.buffer);
        
        const message = {
            type: 'audio',
            data: Array.from(uint8Data)
        };
        
        this.ws.send(JSON.stringify(message));
    }
    
    _handleMessage(data) {
        switch (data.type) {
            case 'user_list':
                console.log('Voice chat users:', data.users);
                this.screenSharer = data.screen_sharer || null;
                this.isScreenSharing = this.screenSharer === this.username;
                if (this.onUserListUpdate) {
                    this.onUserListUpdate(data.users, data.screen_sharer, data.screen_active);
                }
                break;
                
            case 'audio':
                this._playAudio(data.from_user, data.data);
                break;
                
            case 'user_joined':
                console.log('User joined voice:', data.username);
                if (this.onUserJoined) {
                    this.onUserJoined(data.username);
                }
                break;
                
            case 'user_left':
                console.log('User left voice:', data.username);
                if (this.onUserLeft) {
                    this.onUserLeft(data.username);
                }
                break;
                
            case 'screen_state':
                this.screenSharer = data.sharer;
                this.isScreenSharing = data.sharer === this.username;
                if (this.onScreenStateChange) {
                    this.onScreenStateChange(data.sharer, data.active);
                }
                break;
                
            case 'screen_frame':
                if (this.onScreenFrame) {
                    this.onScreenFrame(data.from_user, data.data);
                }
                break;
                
            case 'screen_error':
                console.error('Screen share error:', data.message);
                if (this.onError) {
                    this.onError(data.message);
                }
                break;
                
            case 'error':
                console.error('Voice chat error:', data.message);
                if (this.onError) {
                    this.onError(data.message);
                }
                break;
        }
    }
    
    _playAudio(fromUser, uint8Data) {
        if (!this.audioContext) {
            return;
        }
        
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        const int16Data = new Int16Array(new Uint8Array(uint8Data).buffer);
        const floatData = this._16BitPCMToFloat(int16Data);
        
        const audioBuffer = this.audioContext.createBuffer(
            1,
            floatData.length,
            this.sampleRate
        );
        
        audioBuffer.getChannelData(0).set(floatData);
        
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        source.start();
    }
    
    toggleMute() {
        this.muted = !this.muted;
        return this.muted;
    }
    
    setMute(muted) {
        this.muted = muted;
    }
    
    isMuted() {
        return this.muted;
    }
    
    async startScreenShare(options = {}) {
        if (this.isScreenSharing) {
            return true;
        }
        
        try {
            const displayMediaOptions = {
                video: {
                    cursor: "always",
                    displaySurface: options.displaySurface || "monitor"
                },
                audio: false
            };
            
            this.screenStream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions);
            
            const videoTrack = this.screenStream.getVideoTracks()[0];
            if (videoTrack) {
                const settings = videoTrack.getSettings();
                console.log('Screen share settings:', settings);
            }
            
            this.screenCanvas = document.createElement('canvas');
            this.screenCtx = this.screenCanvas.getContext('2d');
            
            const video = document.createElement('video');
            video.srcObject = this.screenStream;
            video.muted = true;
            video.playsInline = true;
            
            await video.play();
            
            this._screenVideo = video;
            
            this.screenStream.getVideoTracks()[0].onended = () => {
                this.stopScreenShare();
            };
            
            this.ws.send(JSON.stringify({ type: 'screen_start' }));
            this.isScreenSharing = true;
            
            this._startFrameCapture();
            
            console.log('Screen sharing started');
            return true;
            
        } catch (error) {
            console.error('Failed to start screen share:', error);
            this.isScreenSharing = false;
            return false;
        }
    }
    
    _startFrameCapture() {
        if (!this._screenVideo || !this.screenCanvas || !this.screenCtx) {
            return;
        }
        
        const captureFrame = () => {
            if (!this.isScreenSharing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const video = this._screenVideo;
            const canvas = this.screenCanvas;
            const ctx = this.screenCtx;
            
            let width = video.videoWidth;
            let height = video.videoHeight;
            
            if (width > this.maxWidth) {
                const ratio = this.maxWidth / width;
                width = this.maxWidth;
                height = Math.floor(height * ratio);
            }
            if (height > this.maxHeight) {
                const ratio = this.maxHeight / height;
                height = this.maxHeight;
                width = Math.floor(width * ratio);
            }
            
            if (canvas.width !== width || canvas.height !== height) {
                canvas.width = width;
                canvas.height = height;
            }
            
            ctx.drawImage(video, 0, 0, width, height);
            
            const dataUrl = canvas.toDataURL('image/jpeg', this.quality);
            
            this.ws.send(JSON.stringify({
                type: 'screen_frame',
                data: dataUrl
            }));
            
            this._frameTimeout = setTimeout(captureFrame, 1000 / this.frameRate);
        };
        
        captureFrame();
    }
    
    stopScreenShare() {
        if (!this.isScreenSharing) {
            return;
        }
        
        if (this._frameTimeout) {
            clearTimeout(this._frameTimeout);
            this._frameTimeout = null;
        }
        
        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
            this.screenStream = null;
        }
        
        if (this._screenVideo) {
            this._screenVideo.srcObject = null;
            this._screenVideo = null;
        }
        
        this.screenCanvas = null;
        this.screenCtx = null;
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'screen_stop' }));
        }
        
        this.isScreenSharing = false;
        console.log('Screen sharing stopped');
    }
    
    isCurrentlyScreenSharing() {
        return this.isScreenSharing;
    }
    
    getScreenSharer() {
        return this.screenSharer;
    }
    
    disconnect() {
        this.stopScreenShare();
        this._cleanup();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    _cleanup() {
        this.isConnected = false;
        
        if (this.scriptProcessor) {
            this.scriptProcessor.disconnect();
            this.scriptProcessor = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        this.audioQueue = {};
    }
    
    getParticipants() {
        return this.participants || [];
    }
}

window.VoiceChatClient = VoiceChatClient;
