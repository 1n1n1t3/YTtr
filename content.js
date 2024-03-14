chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'seekToTimestamp') {
        var player = document.querySelector('video');
        if (player) {
            player.currentTime = request.timestamp;
        }
    }
});