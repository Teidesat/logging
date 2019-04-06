var pc = new RTCPeerConnection({
    sdpSemantics: 'unified-plan'
});

// connect video
pc.addEventListener('track', function(evt) {
    if (evt.track.kind == 'video') {
        document.getElementById('video').srcObject = evt.streams[0];
    }
});

function createDataChannel(pc) {
    dc = pc.createDataChannel('dataChannel', parameters);
    dc.onclose = function() {
        console.log('Data channel closed');
    };

    dc.onopen = function() {
        console.log('Data channel open');
        dc.send('test');
    };

    dc.onmessage = function(evt) {
        console.log('Message received: ' + evt.data);
    };
}

function negotiate() {
    pc.addTransceiver('video', {direction: 'recvonly'});
    createDataChannel(pc);
    return pc.createOffer().then(function(offer) {
        return pc.setLocalDescription(offer);
    }).then(function() {
        // wait for ICE gathering to complete
        return new Promise(function(resolve) {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                function checkState() {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                }
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(function() {
        var offer = pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {
        return pc.setRemoteDescription(answer);
    }).catch(function(e) {
        alert(e);
    });
}

function start() {
    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function stop() {
    document.getElementById('stop').style.display = 'none';

    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
}
