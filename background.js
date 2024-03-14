chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'summarize') {
      var videoUrl = request.url;
      var videoId = extractVideoId(videoUrl);

      if (videoId) {
          // Call serverless function to summarize video
          fetch('https://y-ttr-amber.vercel.app/summarize', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify({ url: videoUrl }),
          mode: 'no-cors'
          }) 
          .then(response => {
              if (!response.ok) {
                  throw new Error('Network response was not ok');
              }
              return readChunkedResponse(response.body.getReader());
          })
          .then(data => {
              var summary = data.trim();
              chrome.runtime.sendMessage({ action: 'updateSummary', summary: summary });
          })
          .catch(error => {
              console.error('Error calling API:', error);
              chrome.runtime.sendMessage({ action: 'updateSummary', summary: null });
          });
      } else {
          chrome.runtime.sendMessage({ action: 'updateSummary', summary: null });
      }
  }
});

chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === 'updateSummary') {
      // Store the summary in the background script's storage
      chrome.storage.local.set({ 'summary': request.summary });
  }
});

function extractVideoId(url) {
  var regex = /[?&]v=([^&#]+)/;
  var match = url.match(regex);
  return match ? match[1] : null;
}

// Function to read the chunked response
async function readChunkedResponse(reader) {
  let result = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    const chunk = new TextDecoder().decode(value);
    const dataPrefix = 'data: ';
    if (chunk.startsWith(dataPrefix)) {
      result += chunk.slice(dataPrefix.length);
    } else if (chunk.trim().length > 0) {
      result += chunk;
    }
  }
  return result;
}