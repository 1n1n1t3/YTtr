document.addEventListener('DOMContentLoaded', function() {
    var summarizeBtn = document.getElementById('summarizeBtn');
    var summaryOutput = document.getElementById('summaryOutput');

    // Load the stored summary when the popup is opened
    chrome.storage.local.get(['summary'], function(result) {
        if (result.summary) {
            summaryOutput.innerHTML = result.summary;
            addTimestampClickHandlers();
        }
    });

    summarizeBtn.addEventListener('click', function() {
        chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
            var currentUrl = tabs[0].url;
            var youtubeRegex = /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([^&]+)/;
            var match = currentUrl.match(youtubeRegex);

            if (match) {
                chrome.runtime.sendMessage({ action: 'summarize', url: currentUrl });
                summaryOutput.textContent = 'Summarizing video...';
            } else {
                summaryOutput.textContent = 'The current tab is not a YouTube video.';
            }
        });
    });

    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        if (request.action === 'updateSummary') {
            if (request.summary) {
                var formattedSummary = request.summary.replace(/\n/g, '<br>').replace(/\[(\d{1,2}:\d{1,2})\]/g, function(match, p1) {
                    return "<a href='#' class='timestamp-link' data-timestamp='" + p1 + "'>[" + p1 + "]</a>";
                });
                summaryOutput.innerHTML = formattedSummary;
                // Send the summary to the background script for storage
                chrome.runtime.sendMessage({ action: 'updateSummary', summary: formattedSummary });
                addTimestampClickHandlers();
            } else {
                summaryOutput.textContent = 'Failed to summarize video.';
            }
        }
    });

    function addTimestampClickHandlers() {
        var timestampLinks = document.querySelectorAll('.timestamp-link');
        timestampLinks.forEach(function(link) {
            link.addEventListener('click', function(event) {
                event.preventDefault();
                var timestamp = this.getAttribute('data-timestamp');
                var minutes = parseInt(timestamp.split(':')[0], 10);
                var seconds = parseInt(timestamp.split(':')[1], 10);
                var totalSeconds = minutes * 60 + seconds;
                chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, { action: 'seekToTimestamp', timestamp: totalSeconds });
                });
            });
        });
    }

});
