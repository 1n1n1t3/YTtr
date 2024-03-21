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

Please carefully review the video details, paying special attention to the full transcript. Then,
provide a comprehensive written summary of the video following these steps:

1. Analyze the likely target audience for this video based on the topic. Consider their goals, pain
points, and level of familiarity with the subject. Tailor the tone and content of your summary to
resonate with this audience.

2. Identify the main sections or topics covered in the video based on the transcript. Use these to
outline your summary, creating an H1 heading for each main section.

3. Under each H1 section heading, write 1-3 sentences summarizing the key points in that section.
Aim to cover the main sections evenly, with the total summary length being 20-30% of the full video
length.

4. Use a mix of abstractive summarization (70-90%) and direct quotes from the transcript (10-30%).
Adjust this ratio as needed based on the type of content.

5. Organize the summary clearly using H2 and H3 subheadings as appropriate. Use bullet points to
break up long paragraphs or list items. Bold key terms. Use blockquotes for longer direct
quotations.

6. Generate clickable timestamp links for each section header and key point or quote used. To
calculate the timestamp link:
a. Note down the starting point of the relevant part of the video in H:MM:SS format (e.g. 0:14:16)
b. Convert the hours and minutes portions to seconds (e.g. 14 minutes = 14 * 60 = 840 seconds)
c. Add the remaining seconds (e.g. 840 + 16 = 856 seconds total)
d. Subtract 2 seconds to account for any slight misalignment (e.g. 856 - 2 = 854)
e. Append "&t=X" to the video URL, replacing X with the final total seconds (e.g. &t=854)
f. Format the full link as: [H:MM:SS]({video_url}&t=X)

6a. It is very important to pick accurate starting timestamps for the links. For example, consider the following transcript:
[0:01:28] did that very well
[0:01:30] and so anyways we got together and it
[0:01:32] was during the microprocessor Revolution
[0:01:34] this is 1993 in 1992 when we were
[0:01:37] getting together the PC Revolution was
[0:01:39] just getting going it was pretty clear
[0:01:41] the microprocessor was going to be very
[0:01:42] important and we thought why don't we
[0:01:44] build a company to go solve problems
[0:01:48] that a normal computer can't and so that
[0:01:51] that became the company's mission to go
[0:01:53] build a computer the type of computers
[0:01:55] and solve problems that normal computers
[0:01:57] can't and to this day we're focused on
[0:01:59] that and if you look at all the problems
[0:02:01] that that in the markets that we opened
[0:02:03] up as a result things like computational
[0:02:06] drug design weather simulation materials
[0:02:09] design these are all things that we're
[0:02:10] really proud of Robotics uh self-driving

The quote:
>We thought why don't we build a company to go solve problems that a normal computer can't and so that that became the company's mission to go build a computer the type of computers and solve problems that normal computers can't and to this day we're focused on that.
starts at [0:01:42], because it is at that timestamp the the first word "We" is found.

7. Vary the sentence structures throughout to keep the writing engaging. Ensure the transitions
between sentences and sections are smooth. Maintain a consistent voice that matches the tone of the
original video.

8. Conclude the summary with 2-4 concise, actionable takeaways for the target audience. Focus these
on the What, Why and How of the video's key messages.

9. Revise the full summary, checking for any unintentional bias or editorializing. Aim to neutrally
represent the content of the original video."""
        

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