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
        prompt = f"""Here are the details for the video to summarize:

<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']}
View count: {video_details['views']}
Likes count: {video_details['likes']}
Transcript: 
{video_details['transcript']}
</video_details>

The video URL is: {video_url}

Please carefully review the video details above, paying special attention to the full transcript. Then, provide a comprehensive written summary of the video following these steps:

1. Analyze the likely target audience for this video based on the topic. Consider their goals, pain points, and level of familiarity with the subject. Tailor the tone and content of your summary to resonate with this audience on an emotional level, using persuasive language where appropriate.

2. Break down the video transcript into a chain of key sections or topics. Use these to logically structure your summary, creating an H1 heading for each main point in the chain of reasoning. 

3. Under each H1 section heading, write 1-3 sentences concisely summarizing the essential information from that section. Aim for an even coverage of the main points, with the total summary length being 20-30% of the full video length.

4. Combine abstractive summarization (70-90%) with judicious use of direct quotes from the transcript (10-30%). Adjust this ratio as needed based on the type of content. Endeavor to address the full breadth of the transcript without significant omissions.

5. Organize the summary clearly using H2 and H3 subheadings as appropriate to reinforce the logical flow. Utilize bullet points to enhance readability of longer paragraphs or list items. Selectively bold key terms for emphasis. Use blockquotes to highlight longer verbatim quotations.

6. Generate clickable timestamp links for each section header and key point or quote used. Append them after the relevant text. To calculate the timestamp link:

a. Note down the starting point of the relevant part of the video in H:MM:SS format (e.g. 0:14:16) 
b. Convert the hours and minutes portions to seconds (e.g. 14 minutes = 14 * 60 = 840 seconds)
c. Add the remaining seconds (e.g. 840 + 16 = 856 seconds total) 
d. Subtract 2 seconds to add buffer for the user between opening the link and hearing the intended content (e.g. 856 - 2 = 854)
e. Append "&t=X" to the video URL, replacing X with the final total seconds (e.g. &t=854)
f. Format the full link as: [H:MM:SS]({video_url}&t=X)

It is crucial to select precise starting timestamps for the links. For example, consider the following transcript excerpt:

0:01:42 We thought why don't we 
0:01:44 build a company to go solve problems
0:01:48 that a normal computer can't and so that 
0:01:51 that became the company's mission to go
0:01:53 build a computer the type of computers
0:01:55 and solve problems that normal computers 
0:01:57 can't and to this day we're focused on
0:01:59 that

The correct starting timestamp for the quote "We thought why don't we build a company to go solve problems that a normal computer can't" would be 0:01:42, because that is when the first word "We" appears in the transcript. However, applying the rule from 6.d. you'll subtract 2 seconds and the timestamp becomes 0:01:40 which calculated to seconds is t=100.

7. Vary the sentence structures throughout to maintain an engaging narrative flow. Ensure smooth transitions between sentences and sections. Adopt a consistent voice aligned with the original video's tone.

8. Conclude the summary with 2-4 concise, actionable takeaways for the target audience. Focus these on the What, Why and How of the video's key messages. Frame them persuasively to inspire the reader to act on the insights.

9. Revise the full summary, checking for any unintended bias or editorializing. Aim to neutrally represent the content of the original video. Consider engaging in a feedback loop with a human reviewer to iteratively optimize the summary.

Provide your final video summary."""
        

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
            transcript_text = '\n'.join([f"{str(datetime.timedelta(seconds=int(entry['start'])))} {entry['text']}" for entry in transcript])
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