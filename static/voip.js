class VOIPClient {
    constructor(wsUrl) {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnection = null;
        this.currentCallId = null;
        this.currentCallType = null;
        this.remoteUser = null;
        this.isInitiator = false;
        this.onCallRequest = null;
        this.onCallAccepted = null;
        this.onCallRejected = null;
        this.onCallEnded = null;
        this.onRemoteStream = null;
        this.onError = null;
        this.onCallBusy = null;
        
        this.iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
    }
    
    connect(username) {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                this.ws.send(JSON.stringify({ type: 'register', username }));
                resolve();
            };
            
            this.ws.onmessage = (event) => {
                this._handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onerror = (error) => {
                console.error('VOIP WebSocket error:', error);
                if (this.onError) this.onError('Connection error');
                reject(error);
            };
            
            this.ws.onclose = () => {
                console.log('VOIP WebSocket closed');
                this._cleanup();
            };
        });
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this._cleanup();
    }
    
    async startCall(targetUser, callType = 'audio') {
        if (this.peerConnection) {
            throw new Error('Already in a call');
        }
        
        this.remoteUser = targetUser;
        this.currentCallType = callType;
        this.isInitiator = true;
        
        try {
            await this._createPeerConnection();
            this.localStream = await this._getUserMedia(callType);
            
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
            
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this._sendMessage({
                type: 'call_request',
                to_user: targetUser,
                call_type: callType
            });
            
            return true;
        } catch (error) {
            console.error('Failed to start call:', error);
            this._cleanup();
            throw error;
        }
    }
    
    async acceptCall(callId, callType) {
        this.currentCallId = callId;
        this.currentCallType = callType;
        this.isInitiator = false;
        
        try {
            await this._createPeerConnection();
            this.localStream = await this._getUserMedia(callType);
            
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
            
            this._sendMessage({
                type: 'call_accept',
                call_id: callId
            });
            
            return true;
        } catch (error) {
            console.error('Failed to accept call:', error);
            this._cleanup();
            throw error;
        }
    }
    
    rejectCall(callId) {
        this._sendMessage({
            type: 'call_reject',
            call_id: callId
        });
    }
    
    endCall() {
        if (this.currentCallId) {
            this._sendMessage({
                type: 'call_end',
                call_id: this.currentCallId
            });
        }
        this._cleanup();
    }
    
    toggleMute() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                return !audioTrack.enabled;
            }
        }
        return false;
    }
    
    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !videoTrack.enabled;
                return !videoTrack.enabled;
            }
        }
        return false;
    }
    
    async _createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.iceServers);
        
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this._sendMessage({
                    type: 'ice_candidate',
                    to_user: this.remoteUser,
                    candidate: event.candidate.toJSON(),
                    call_id: this.currentCallId
                });
            }
        };
        
        this.peerConnection.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            if (this.onRemoteStream) {
                this.onRemoteStream(this.remoteStream);
            }
        };
        
        this.peerConnection.onconnectionstatechange = () => {
            console.log('Connection state:', this.peerConnection.connectionState);
            if (this.peerConnection.connectionState === 'disconnected' ||
                this.peerConnection.connectionState === 'failed') {
                this.endCall();
            }
        };
    }
    
    async _getUserMedia(callType) {
        const constraints = {
            audio: true,
            video: callType === 'video'
        };
        return await navigator.mediaDevices.getUserMedia(constraints);
    }
    
    _handleMessage(data) {
        console.log('VOIP message received:', data.type);
        
        switch (data.type) {
            case 'call_request':
                this.currentCallId = data.call_id;
                this.remoteUser = data.from_user;
                this.currentCallType = data.payload?.call_type || 'audio';
                if (this.onCallRequest) {
                    this.onCallRequest(data.from_user, data.call_id, this.currentCallType);
                }
                break;
                
            case 'call_accept':
                this.currentCallId = data.call_id;
                if (this.onCallAccepted) {
                    this.onCallAccepted(data.from_user);
                }
                this._sendOffer();
                break;
                
            case 'call_reject':
                if (this.onCallRejected) {
                    this.onCallRejected(data.from_user);
                }
                this._cleanup();
                break;
                
            case 'call_end':
                if (this.onCallEnded) {
                    this.onCallEnded(data.from_user);
                }
                this._cleanup();
                break;
                
            case 'call_busy':
                if (this.onCallBusy) {
                    this.onCallBusy(data.from_user);
                }
                this._cleanup();
                break;
                
            case 'sdp_offer':
                this._handleOffer(data.payload.sdp);
                break;
                
            case 'sdp_answer':
                this._handleAnswer(data.payload.sdp);
                break;
                
            case 'ice_candidate':
                this._handleIceCandidate(data.payload.candidate);
                break;
                
            case 'call_error':
                if (this.onError) {
                    this.onError(data.payload?.error || 'Unknown error');
                }
                break;
        }
    }
    
    async _sendOffer() {
        if (!this.peerConnection || !this.isInitiator) return;
        
        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this._sendMessage({
                type: 'sdp_offer',
                to_user: this.remoteUser,
                sdp: offer,
                call_id: this.currentCallId
            });
        } catch (error) {
            console.error('Failed to send offer:', error);
        }
    }
    
    async _handleOffer(sdp) {
        if (!this.peerConnection) return;
        
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(sdp));
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            
            this._sendMessage({
                type: 'sdp_answer',
                to_user: this.remoteUser,
                sdp: answer,
                call_id: this.currentCallId
            });
        } catch (error) {
            console.error('Failed to handle offer:', error);
        }
    }
    
    async _handleAnswer(sdp) {
        if (!this.peerConnection) return;
        
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(sdp));
        } catch (error) {
            console.error('Failed to handle answer:', error);
        }
    }
    
    async _handleIceCandidate(candidate) {
        if (!this.peerConnection) return;
        
        try {
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (error) {
            console.error('Failed to add ICE candidate:', error);
        }
    }
    
    _sendMessage(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    _cleanup() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        this.remoteStream = null;
        this.currentCallId = null;
        this.currentCallType = null;
        this.remoteUser = null;
        this.isInitiator = false;
    }
}

window.VOIPClient = VOIPClient;
