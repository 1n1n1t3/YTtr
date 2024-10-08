import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import yt_dlp
import requests

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
a. presented factual and objective data and information
b. personal experience, opinions and subjective information 
c. information presented as a fact, but might need cross-checking
Report all three, but flag them appropriately so the reader knows which is which. If you are unsure or don't have enough information to provide a confident categorization, simply say "I don't know" or "I'm not sure."

4. Use blended summarization technique combining  abstractive summarization (70-90%) extractive summarization (10-30%). Adjust this ratio as needed based on the type of content. Endeavor to address the full breadth of the transcript without significant omissions. Make sure the extracted quotes are short, important and impactful to the narrative.

5. Aim for length of the summary that is approximately 20% the length of the full video transcript. For example, if the transcript is 5000 words long, target a summary of roughly 1000 words. Try to cover the video in full without gaps.

6. Break down the summary into a chain of key sections or topics. Use these to logically structure it, creating an H1 heading for each main point in the chain of reasoning. 

7. Under each H1 section heading, write 1-3 sentences concisely summarizing the essential information from that section. Aim for an even coverage of the main points.

8. Organize the summary clearly using H2 and H3 subheadings as appropriate to reinforce the logical flow. Utilize bullet points to enhance readability of longer paragraphs or list items. Selectively bold key terms for emphasis. Use blockquotes to highlight longer verbatim quotations.

9. Generate clickable timestamp links for each section header and key point or quote used. Append them after the relevant text. To calculate the timestamp link follow these steps:

a. Note down the starting point of the relevant part of the video in H:MM:SS format (e.g. 0:14:16) 
b. Convert the hours and minutes portions to seconds (e.g. 14 minutes = 14 * 60 = 840 seconds)
c. Add the remaining seconds (e.g. 840 + 16 = 856 seconds total) 
d. Subtract 2 seconds to add buffer for the user between opening the link and hearing the intended content (e.g. 856 - 2 = 854)
e. Append "&t=X" to the video URL, replacing X with the final total seconds (e.g. &t=854)
f. Format the full link as: [H:MM:SS]({video_url}&t=X) (e.g. [0:14:16]({video_url}&t=854) )

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

10. Vary the sentence structures throughout to maintain an engaging narrative flow. Ensure smooth transitions between sentences and sections. Adopt a consistent voice aligned with the original video's tone.

11. Revise the full summary, checking for any unintended bias or editorializing. Aim to neutrally represent the content of the original video. Consider engaging in a feedback loop with a human reviewer to iteratively optimize the summary.

12. Provide your final video summary, ready for publication. Use all known Markdown operators to present the output."""
        

        return jsonify({"prompt": str(prompt)})
    else:
        return jsonify({"error": "Could not retrieve video details"}), 400

def extract_video_id(url):
    video_id = re.findall(r"v=(\S{11})", url)[0]
    return video_id

# Function to get video details from YouTube Data API
def get_video_details(video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        
        if 'entries' in info:
            video = info['entries'][0]
        else:
            video = info
        
        transcript = None
        if 'subtitles' in video and 'en' in video['subtitles']:
            subtitle_info = video['subtitles']['en']
            subtitle_url = subtitle_info[0]['url']
            transcript = requests.get(subtitle_url).text
        
        return {
            "channel": video['channel'],
            "title": video['title'], 
            "views": video['view_count'],
            "likes": video.get('like_count', None),
            "transcript": transcript
        }
