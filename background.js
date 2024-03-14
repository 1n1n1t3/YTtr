chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'summarize') {
      var videoUrl = request.url;
      var videoId = extractVideoId(videoUrl);
      
      if (videoId) {
        // Call serverless function to summarize video
        fetch('https://y-1j2i307bd-ddavidkovs-projects.vercel.app/summarize', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({url: videoUrl})
        })
        .then(response => response.json())
        .then(data => {
          var summary = data.summary;
          chrome.runtime.sendMessage({action: 'updateSummary', summary: summary});
        })
        .catch(error => {
          console.error('Error calling serverless function:', error);
          chrome.runtime.sendMessage({action: 'updateSummary', summary: null});
        });
      } else {
        chrome.runtime.sendMessage({action: 'updateSummary', summary: null});
      }
    }
  });
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'summarize') {
        // Existing code...
    } else if (request.action === 'updateSummary') {
        // Store the summary in the background script's storage
        chrome.storage.local.set({ 'summary': request.summary });
    }
});
  function extractVideoId(url) {
    var regex = /[?&]v=([^&#]+)/;
    var match = url.match(regex);
    return match ? match[1] : null;
  }