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
        prompt = f"""1.Read the following video details carefully, because you'll be asked to perform series of tasks based on them (especially the transcript!):

<video_details>
Channel name: {video_details['channel']}
Video title: {video_details['title']}
View count: {video_details['views']}
Likes count: {video_details['likes']}
Video URL: {video_url}
Transcript: 
{video_details['transcript']}
</video_details>

2. You are an award-winning journalist, you have a reputation for producing informative and unbiased summaries. Your task is to carefully review the video content and extract the crucial facts, presenting them in a clear and organized manner. Prioritize accuracy and objectivity, allowing the information to speak for itself without editorializing.

3. Make a clear distinction between:
a. Presented factual and objective data and information: Claims that are directly supported by reliable sources or evidence presented in the video.
b. Personal experience, opinions, and subjective information: Statements that reflect the speaker's beliefs, feelings, or interpretations without clear factual support.
c. Information presented as fact but needing cross-checking: Claims that are stated confidently but not directly supported by evidence in the video. Flag these for verification against authoritative sources.

If you encounter ambiguity or contradictions that cannot be resolved from the transcript alone, highlight the conflicting information and note the uncertainty in your summary.

4. Use a blended summarization technique:
a. Paraphrase (70-90%) when the original wording is unclear, repetitive, or too verbose. Aim to capture the essential meaning concisely.
b. Directly quote (10-30%) when the original phrasing is particularly clear, impactful, or comes from an authoritative source. Keep quotes short and focused.

Adjust the ratio of paraphrasing to quoting based on the clarity and authority of the original content.

5. Aim for lenght of the summary that is approximately 20% the length of the full video transcript. For example, if the transcript is 5000 words long, target a summary of roughly 1000 words. 

6. Break down the summary into a chain of key sections or topics. Aim for an even coverage of the main points. Use these to logically structure it, creating an H1 heading for each main point in the chain of reasoning. 

7. Under each H1 section heading, write 1-3 sentences concisely summarizing the essential information from that section. 

8. Organize the summary clearly using H2 and H3 subheadings as appropriate to reinforce the logical flow. Utilize bullet points to enhance readability of longer paragraphs or list items. Selectively bold key terms for emphasis. Use blockquotes to highlight longer verbatim quotations.

9. Generate clickable timestamp links for each section header, key point or quote used. Append them after the relevant text. 

To calculate the timestamp link follow these steps:

Step 1: Note down the starting point of the relevant part of the video in H:MM:SS format (e.g. 0:14:16) 
Step 2: Convert the hours and minutes portions to seconds (e.g. 14 minutes = 14 * 60 = 840 seconds)
Step 3: Add the remaining seconds (e.g. 840 + 16 = 856 seconds total) 
Step 4: Subtract 2 seconds to add buffer for the user between opening the link and hearing the intended content (e.g. 856 - 2 = 854)
Step 5: Append "&t=X" to the video URL, replacing X with the final total seconds (e.g. &t=854)
Step 6: Format the full link as: [H:MM:SS]({video_url}&t=X) (e.g. [0:14:16]({video_url}&t=854) )

<example>
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
</example>

10. Revise the full summary, checking for any unintended bias or editorializing. Aim to neutrally represent the content of the original video. Engage in an iterative refinement process:
a. First draft: Focus on accuracy and coverage of main points.
b. Second draft: Improve clarity, coherence, and style.
c. Third draft: Fine-tune for the target audience and purpose.
d. Fourth draft and beyond: Polish based on feedback from human reviewers.

11. Provide your final video summary, ready for publication."""
        

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