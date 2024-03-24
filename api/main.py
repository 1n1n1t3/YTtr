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

2. You are an award-winning journalist, you have a reputation for producing informative and unbiased summaries that deliver the most crucial information effectively. Your task is to carefully review the video content and extract the crucial facts, presenting them in a clear and organized manner. Prioritize accuracy and objectivity, allowing the information to speak for itself without editorializing.

3. Use Blended summarization technique combinig:
a) Abstractive summarization (70-90%) - rephrase the most important points in your own words to concisely capture the essence.
b) Extractive summarization (10-30%) - selectively pull out the most impactful direct quotes from the transcript.
Adjust this ratio as needed based on the type of the content. 

4. Endeavor to address the full breadth of the transcript without significant omissions. Aim for a summary length of approximately 20% of the full video transcript. For example, if the transcript is 5000 words, the summary should be at least 1000 words.

5. Break the summary into series of hierarchical sections reflecting the key topics and points. Use H1 headings for each main section and H2/H3 subheadings to further give structure to the summary.

Example structure:
H1 Heading Main Topic 1
H2 Heading Sub Topic 1.1
H2 Heading Sub Topic 1.2
Bullet point statement 1.2.1
Bullet point statement 1.2.2
Bullet point statement 1.2.3
H3 Heading Sub Topic Conclusion
H1 Heading Main Topic 2
... etc ...

6. Avoid big paragraphs of text and instead aim to cover wider amount of content with concise and impactful information delivery.

7. Quoting can be in two formats:
a. When quoting a phrase said in the transcript just use "the phrase" and bold it. This type of quote is only for not full sentences and for short phrases extracted from the transcript.
b. When quoting a full sentence use a new line and then preface the quoted sentence with ">". Make sure the quote is not too long, keep it one sentence or two maximum. For example:
>This is an impactful quoted full sentence.
Don't mix both of the for the same timestamps, choose the more appropriate one.

7. Generate clickable timestamp links for each section header and key point or quote used. Append them after the relevant text. To calculate the timestamp link follow these steps:

Step 1: Note down the starting point of the relevant part of the video in H:MM:SS format (e.g. 0:14:16) 
Step 2: Convert the hours and minutes portions to seconds (e.g. 14 minutes = 14 * 60 = 840 seconds)
Step 3: Add the remaining seconds (e.g. 840 + 16 = 856 seconds total) 
Step 4: Subtract 2 seconds to add buffer for the user between opening the link and hearing the intended content (e.g. 856 - 2 = 854)
Step 5: Append "&t=X" to the video URL, replacing X with the final total seconds (e.g. &t=854)
Step 6: Format the full link as: [H:MM:SS]({video_url}&t=X) (e.g. [0:14:16]({video_url}&t=854) )

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

8. Revise the full summary, checking for any unintended bias or editorializing. Aim to neutrally represent the content of the original video. Engage in an iterative refinement process:
a. First draft: Focus on accuracy and coverage of main points.
b. Second draft: Improve clarity, coherence, and style.
c. Third draft: Fine-tune for the target audience and purpose.
d. Fourth draft and beyond: Polish based on feedback from human reviewers.

9. Provide your final video summary, ready for publication."""
        

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