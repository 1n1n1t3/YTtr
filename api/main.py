import os
import re
import requests
from anthropic import Anthropic
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import youtube_transcript_api
import datetime

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": ["chrome-extension://fkcjlbfohcfcfhjbbbjgjcedepjmmdgh"]}})
# Set up Anthropic API client 
api_key = os.environ.get('ANTHROPIC_API_KEY', '')
client = Anthropic(api_key=api_key)

yt_api_Key = os.environ.get('YOUTUBE_API_KEY', '')
 
# ... (keep the existing helper functions extract_video_id, get_video_details)

@app.route('/summarize', methods=['POST', 'OPTIONS'])
@cross_origin()
def summarize():
    try:
        if request.method == 'OPTIONS':
            # Handle preflight request
            response = jsonify()
            response.headers.add('Access-Control-Allow-Origin', 'chrome-extension://fkcjlbfohcfcfhjbbbjgjcedepjmmdgh')
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
            You are an AI assistant tasked with summarizing YouTube video transcripts. Your goal is to provide a concise summary of the main points discussed in the video, along with the corresponding timestamps.

            Here are the details of the video you need to summarize:

            Title: {video_details['title']}
            Channel: {video_details['channel']}
            Views: {video_details['views']}
            Likes: {video_details['likes']}

            Transcript:
            {video_details['transcript']}

            Instructions:
            1. Read through the entire transcript carefully to understand the main topics and key points discussed.
            2. Identify the most important and relevant points from the transcript.
            3. The provided transcript has timestamps in this format [h:mm:ss.ms]
            4. For each main point, provide a brief summary (1-2 short sentences) and include the corresponding timestamp in the format [mm:ss].
            5. Present the summary in a clear and organized manner, with each main point on a new line.

            Example output format:
            [mm:ss] First main point summary.
            [mm:ss] Second main point summary.
            [mm:ss] Third main point summary.
            ...

            Please provide your summary in the specified format.
            """
            
            try:
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
            except Exception as e:
                with app.app_context():
                    app.logger.error(f"Error calling Claude API: {e}")
                    return jsonify({"error": str(e)}), 500

            summary = ""

            with app.app_context():
                try:
                    response = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True
                    )
                except Exception as e:
                    app.logger.error(f"Error calling Claude API: {e}")
                    return jsonify({"error": str(e)}), 500

                for chunk in response.content:
                    summary += chunk.text
                    yield f"data: {summary}\n\n"

                yield f"data: {summary}\n\n"

    except Exception as e:
        app.logger.error(f"Error in summarize: {e}")
        return jsonify({"error": str(e)}), 500

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