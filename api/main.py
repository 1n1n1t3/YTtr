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
        prompt = f"""Here are the details and transcript for a YouTube video followed by the instructions you need to
follow:
<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']}
View count: {video_details['views']}
Likes count: {video_details['likes']}
Video URL: {video_url}
Transcript:
{video_details['transcript']}
</video_details>

Your task is to provide a comprehensive summary of this video that will allow someone to learn the
most important information presented without having to watch the full video. The summary should be
of varying length depending on the length of the video.

First, carefully analyze the target audience for this video topic:
- Consider their demographics, prior knowledge, pain points, goals, and preferred communication
style
- Tailor the summary's tone, depth, examples, and language to best resonate with that audience

Next, analyze the structure and flow of the video based on the transcript:
- Identify the main sections or chapters based on topic transitions
- Note the timestamps where each new section begins and ends
- Determine the most logical order for the sections

Create an outline for the summary that mirrors the video's structure:
- Use the main video sections as the top-level outline points
- Add key sub-points under each section
- Aim for at least one sub-point per 2-3 minutes of video, adjusting for density

When writing the summary based on the outline:
- Dedicate 1-3 sentences to each outline sub-point to concisely capture the main ideas
- Avoid skipping points - aim to cover the outline comprehensively and evenly
- Summarize tangents more briefly than core points
- Use 80% abstractive summarization in your own words
- Use 20% extractive summarization of impactful direct quotes

Structure and format the summary:
- Begin with a 1-2 sentence overview of the main topic and key takeaways
- Use ## H2 and ### H3 headings to organize sections
- Apply a combination of numbered and non-numbered bullet points for lists
- Bold key terms and phrases sparingly
- Use blockquotes for direct transcript quotes on their own line:
> Like this example blockquote formatting.
- Provide 2-4 summary sentences after each heading

Generate clickable timestamp links for each claim, quote, or section header:
- Find the closest prior timestamp to the start of the relevant transcript section
- For multi-line quotes, use the first line's timestamp
- Add a 2 second (t=t-2) buffer before the target timestamp
- For very short sections, link 1 seconds (t=t-1) earlier for more context
- Format links as [H:MM:SS]({video_url}&t=X) where X is the number of elapsed seconds from the
start of the video to that timestamp.
To calculate X with precision:
1. Note down the timestamp in this format: H:MM:SS like 0:14:16
2. Convert the hours, minutes, and seconds to total elapsed seconds (e.g., 0 hours, 14 minutes, and
16 seconds equals 856 seconds total).
3. Append &t=X to the end of the video URL, replacing X with the total elapsed seconds.

Optimize the summary through revisions:
- Vary sentence structures for better flow
- Ensure smooth section transitions
- Maintain a consistent voice and tone
- Balance abstraction and direct quotes
- Trim redundancies and non-essential info
- Point out anything that requires watching the video to make sense

Conclude with 3-4 key actionable takeaways, each with:
- What: The specific insight or recommendation
- Why: The importance and benefit
- How: Steps to put it into practice
Phrase them as memorable action statements.

The goal is an engaging, standalone summary that efficiently conveys the video's core information in less time than watching the full video. """
        

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