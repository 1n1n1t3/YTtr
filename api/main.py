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
        prompt = f"""<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']}
View count: {video_details['views']}
Likes count: {video_details['likes']}
Video URL: {video_url}
Transcript: {video_details['transcript']}
</video_details>
<instructions>
Provide a comprehensive summary of this video to convey the most important information without watching the full video. 
- Aim for a summary length of 20-30% of the video length.
- Analyze the target audience's likely goals and pain points based on the topic.
- Tailor the tone and content to resonate with that audience.
- Identify the main sections and outline the summary based on the video structure. Use H1 heading for these.
- Dedicate 1-3 sentences to each sub-point, covering the outline evenly.
- Use 70-90% abstractive summarization and 10-30% direct quotes, adjusting for content type.
- Organize with H2 and H3 headings, bullet points, bolded terms, and blockquotes.
- Generate clickable timestamp links for each section header, key point, or quote.
To calculate timestamp links:
1. Diligently note down the starting point of the relevant timestamp in H:MM:SS format (e.g., 0:14:16).
2. Carefully convert hours and minutes to seconds (e.g., 14 minutes = 14 * 60 = 840 seconds).
3. Add the remaining seconds (e.g., 840 + 16 = 856 seconds total).
4. Subtract 2 seconds (e.g., 856 - 4 = 854).
6. Append &t=X to the video URL, replacing X with the final total seconds (e.g., &t=852).
7. Format the full link as [H:MM:SS]({video_url}&t=X).
- Vary sentence structures, ensure smooth transitions, and maintain consistent voice .
- Conclude with 2-4 actionable and concise takeaways focused on Whatmm Why and How .
- During revisions, check for unintentional bias or editorializing.
- Represent the video content neutrally.
</instructions>"""
        

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
            transcript_text = '\n'.join([f"[{str(datetime.timedelta(seconds=int(entry['start'])))}] {entry['text']}" for entry in transcript])
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