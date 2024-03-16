import os
import re
import requests
from anthropic import Anthropic
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import youtube_transcript_api
import datetime

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes
# Set up Anthropic API client 
api_key = os.environ.get('ANTHROPIC_API_KEY', '')
client = Anthropic(api_key=api_key)

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
        prompt = f"""
Here is the transcript of a video, with timestamps preceding the spoken text:

<transcript>
{video_details['transcript']}
</transcript>

Your task is to create a comprehensive summary of the video based on this transcript.

To create the summary, follow these steps:
1. Read through the transcript carefully to understand the key points and overall narrative of the
video.
2. Use a blended summary technique that combines:
a) Abstractive summarization (rephrasing key points in your own words)
b) Extractive summarization (selectively pulling out the most important quotes from the transcript)
3. For each key point you include in the summary, include the relevant timestamp from the transcript
in brackets (e.g. [1:23:45]) to indicate which part of the video it corresponds to.
4. Organize the summary in a clear, logical way, with one paragraph per main topic or section of the
video. Use headings to delineate different sections if appropriate.
5. Make sure the summary is well-formatted and easy to read. Use proper grammar and punctuation. Use new lines and bolded text for headers.

Please note: The summary should NOT include the full transcript, only the main points and takeaways
in a condensed form. The goal is to convey the essential information from the video in a concise
way.
        """
        
        # Call Claude API to summarize video
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            #model="claude-3-opus-20240229",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract summary from API response
        summary = response.content[0].text;
        #summary = re.sub(r'\[(\d{1,2}:\d{1,2})\]', r"<a href='#' class='timestamp-link' data-timestamp='$1'>[$1]</a>", summary)
        #print(summary)
        return jsonify({"summary": str(summary)})
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