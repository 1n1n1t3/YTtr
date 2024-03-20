import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import youtube_transcript_api
import datetime

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes
# Set up Anthropic API client 
#api_key = os.environ.get('ANTHROPIC_API_KEY', '')
#client = Anthropic(api_key=api_key)

yt_api_Key = os.environ.get('YOUTUBE_API_KEY', '')
 
# ... (keep the existing helper functions extract_video_id, get_video_details)

@app.route('/summarize', methods=['POST', 'OPTIONS'])
@cross_origin()
def summarize():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    video_url = request.json['url']
    
    # Extract video ID from URL
    video_id = extract_video_id(video_url)

    # Get video details using YouTube Data API
    video_details = get_video_details(video_id)

    if video_details:
        # Prepare prompt for Claude model
        prompt = f"""Here are the details and transcript for a YouTube video:

<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']}
View count: {video_details['views']}
Likes count: {video_details['likes']}
Video URL: {video_url}
</video_details>

<video_transcript>
{video_details['transcript']}
</video_transcript>

Your task is to provide an comprehensive summary of this video that will allow someone to learn the
most important information presented without having to watch the full video.

First, carefully read through the entire transcript to fully understand the key points being made
and the overall narrative flow of the video. 

Then, use a blended summarization approach that combines:
a) Abstractive summarization - rephrase the most important points in your own words to concisely
capture the essence.
b) Extractive summarization - selectively pull out the most impactful direct quotes from the
transcript while noting the timestamp where they appeared.

For each claim, insightful quote or section header you include in the summary, append the timestamp at which it starts being addressed and create a clickable link that points to it.

Use this format for the links: [0:14:16]({video_url}&t=856)
where X is the number of elapsed seconds from the start of the video to that timestamp.

To calculate X with precision:
1. Note down the timestamp in this format: H:MM:SS like 0:14:16
2. Convert the hours, minutes and seconds to total elapsed seconds (e.g. 0 hours, 14 minutes, and 16
seconds equals 856 seconds total).
3. Append &t=X to the end of the video URL, replacing X with the total elapsed seconds.

Format the summary in a visually appealing and easy to read and understand way.
Use headings, bullet points, quoting, bolding and other formatting as appropriate to make the summary scannable and highlight the most important parts.

The goal is you generating a summary that efficiently conveys the core information from the video in a way that
is faster and easier to consume than watching the full video, while still preserving all the
important points."""
        

        return jsonify({"prompt": str(prompt)})
    else:
        return jsonify({"error": "Could not retrieve video details"}), 400

def extract_video_id(url):
    video_id = re.findall(r"v=(\S{11})", url)[0]
    return video_id

# Function to get video details from YouTube Data API
def get_video_details(video_id):
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={yt_api_Key}"
    json_url = requests.get(api_url)
    data = json_url.json()

    if 'items' in data and data['items']:
        video_data = data['items'][0]
        snippet = video_data['snippet']
        statistics = video_data['statistics']
        
        channel_title = snippet['channelTitle']
        video_title = snippet['title']  
        view_count = statistics['viewCount']
        like_count = statistics['likeCount']

        # Fetch transcript with timestamps
        try:
            transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = '\n'.join([f"[{datetime.timedelta(seconds=entry['start'])}] {entry['text']}" for entry in transcript])
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            transcript_text = None
        #print(transcript_text)
        return {
            "channel": channel_title,
            "title": video_title,
            "views": view_count,
            "likes": like_count,
            "transcript": transcript_text
        }
    else:
        return None