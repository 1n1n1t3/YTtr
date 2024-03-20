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
        prompt = f"""
<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']} 
View count: {video_details['views']}
Likes count: {video_details['likes']}
Video URL: {video_url}
Transcript: 
{video_details['transcript']}
</video_details>

Instructions:
1. Carefully analyze the target audience for this video topic. Consider their demographics, prior knowledge, pain points, goals, and preferred communication style. Tailor the summary's tone, depth, examples, and language to best resonate with that audience.

2. Identify the main sections or chapters in the video based on topic transitions. Note down the exact start and end timestamps for each section in HH:MM:SS format. Determine the most logical order to present the sections in the summary.

3. Create an outline that mirrors the video's structure:
- Use the main video sections as the top-level ## H1 headings 
- Add key sub-points under each section as ### H2 headings
- Aim for 1 sub-point per 2-3 minutes of video, adjusting for content density

4. Write the summary following this outline:
- Dedicate 1-3 concise sentences to each H2 sub-point to capture the main ideas
- Cover all points comprehensively and evenly, avoiding skipping any
- Summarize tangents more briefly than core points 
- Use 80% abstractive summarization in your own words
- Use 20% extractive summarization of impactful direct quotes
- Bold a few key terms or phrases in each section

5. Generate precise clickable timestamp links for each heading, claim, or quote:
- Note down the exact HH:MM:SS timestamp from the start of the relevant sentence and/or section
- Convert HH:MM:SS to total elapsed seconds (e.g. 00:05:30 = 330 seconds)
- Append &t=[seconds] to the end of the video URL 
- Wrap the timestamp in square brackets and make it a clickable link:
[HH:MM:SS]({video_url}&t=[seconds])

6. Begin with a 1-2 sentence overview of the video's main topic and key takeaways.

7. Use blockquotes for any direct transcript quotes on their own line:
> Like this example blockquote formatting.

8. Provide 2-4 summary sentences after each H1 or H2 heading.

9. Revise the summary to optimize the writing:
- Vary sentence structures for better flow 
- Ensure smooth transitions between sections
- Maintain a consistent voice and tone
- Balance abstraction and direct quotes
- Flag anything that requires watching the video to fully make sense

10. Conclude with key actionable takeaways, each specifying:  
- What: The specific insight or recommendation
- Why: The importance and benefit
- How: Steps to put it into practice
Phrase them as memorable action statements."""
        

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