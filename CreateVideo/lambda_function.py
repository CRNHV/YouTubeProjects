import subprocess
import datetime
import os
import wave
import json
import math

import boto3
import feedparser
import requests
import cv2
from PIL import ImageFont
from mutagen.mp3 import MP3
from vosk import Model, KaldiRecognizer

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

RESOURCES_DIR = os.path.abspath('resources')

RSS_FEED = 'https://www.brainyquote.com/link/quotebr.rss'

# Change BASE_DATE to the first day you are planning to upload a video
BASE_DATE = date = datetime.datetime(2023, 8, 1) 

CHUNK_SIZE = 1024

# Eleven Labs
VOICE_ID = 'ErXwobaYiN019PkySvjV'
VOICE_URL = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}'
VOICE_HEADERS = {
    'Accept': 'audio/mpeg',
    'Content-Type': 'application/json',
    'xi-api-key': os.environ.get('ELEVEN_LABS_API_KEY')
}

AUDIORATE = 16000

INTRO_TEXT = 'Quote of the day '

# YouTube API
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
PLAYLIST_ID = os.environ.get('PLAYLIST_ID')

# Total number of premade clips
TOTAL_CLIPS = 30

def lambda_handler(event, context):
    current_date = datetime.datetime.today()

    # Retrieve quote of the day
    author, quote, link = get_quote()

    # Retrive tts audio for quote
    audio_path = get_audio(quote)

    intro_path = f'{RESOURCES_DIR}/intro.mp3'

    # Combine intro and quote audio
    audio_path = concat_audio(intro_path, audio_path)

    # Create transcript of audio
    wav_path = mp3_to_wav(audio_path)
    transcript = transcribe_audio(wav_path)
    transcript_words = []
    for sentence in transcript:
        for word in sentence['result']:
            transcript_words.append(word)

    # Create subtitles from transcript
    sub_text = INTRO_TEXT + quote
    sub_words = sub_text.split(' ')
    subs_path = generate_subtitles(transcript_words, sub_words, current_date, author)

    # Set total length of video to be 1 second longer than the length of the audio
    audio = MP3(audio_path)
    duration = audio.info.length + 1

    # Select background clip based on day
    delta_date = current_date - BASE_DATE
    clip_num = delta_date.days % (TOTAL_CLIPS-1)
    clip_path = f'{RESOURCES_DIR}/clips/{clip_num}.mp4'

    # Loop background clip if necessary
    clip_path = loop_clip(clip_path, duration)

    # Edit all components together to create final video
    video_path = create_final_video(clip_path, audio_path, subs_path, duration)

    # Upload video to YouTube and add video to playlist
    youtube = get_authenticated_service()
    video_id = upload_video(video_path, link, youtube)
    add_video_to_playlist(video_id, youtube)

    # Remove all of the files that were created in order to create and upload the video
    for file in os.scandir('/tmp'):
        os.remove(file.path)

    print(f'Finished uploading video: {video_id}')


# Retrieves the quote, author, and link for the quote of the day from the BrainyQuote Quote of the Day RSS feed
def get_quote():
    print('Retrieving quote...')

    feed = feedparser.parse(RSS_FEED)
    quote_details = feed.entries[0]
    author = quote_details['title']
    link = quote_details['link']
    quote = quote_details['summary']

    quote = refine_quote(quote)

    return author, quote, link


# Replaces all punctuations with elipses to indicate a longer pause
def refine_quote(quote):
    new_quote = quote.replace('"', '')[:-1]
    new_quote = new_quote.replace('...', '.')
    new_quote = new_quote.replace(' -', '...')
    new_quote = new_quote.replace('.', '...')
    new_quote = new_quote.replace(',', '...')
    new_quote = new_quote.replace(';', '...')
    new_quote = new_quote.replace(':', '...')

    return new_quote + '.'


# Retrieves text to speech audio from Eleven Labs
def get_audio(text):
    print('Retrieving audio...')

    # Replace elipses with 5 dashes. Dashes are used to insert a pause in the tts for dramatic effect
    data = {
        'text': text.replace('...', ' - - - - -'),
        'model_id': 'eleven_monolingual_v1',
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75
        }
    }
    response = requests.post(VOICE_URL, json=data, headers=VOICE_HEADERS)

    audio_path = '/tmp/audio.mp3'
    with open(audio_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    return audio_path


# Executes a given shell command
def execute(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    if process.returncode != 0:
        print(out)
        print(err)
        exit()


# Concatenates the intro audio and quote audio together using ffmpeg
def concat_audio(intro_path, audio_path):
    print('Concatenating audios...')
    
    concat_filename = '/tmp/concat_audio.txt'
    output_filename = '/tmp/concat_audio.mp3'
    with open(concat_filename, 'w') as concat_file:
        concat_file.write(f"file '{intro_path}'\n")
        concat_file.write(f"file '{audio_path}'\n")
    
    execute(f'{RESOURCES_DIR}/ffmpeg -f concat -safe 0 -i {concat_filename} -y {output_filename}')

    return output_filename


# Converts an MP3 file to WAV file using ffmpeg
def mp3_to_wav(audio_path):
    print('Converting audio...')

    wav_path = '/tmp/audio.wav'
    execute(f'{RESOURCES_DIR}/ffmpeg -i {audio_path} -acodec pcm_s16le -ac 1 -ar {AUDIORATE} -y {wav_path}')
    return wav_path


# Transcribes the audio using Vosk speech recognition
def transcribe_audio(wav_path):
    print('Transcribing audio...')

    model_path = f'{RESOURCES_DIR}/vosk'
    model = Model(model_path)
    rec = KaldiRecognizer(model, AUDIORATE)
    rec.SetWords(True)

    wf = wave.open(wav_path, 'rb')

    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part_result = json.loads(rec.Result())
            results.append(part_result)

    part_result = json.loads(rec.FinalResult())
    results.append(part_result)
    return results

# Converts a timestamp from milliseconds to the format required by ASS subtitle file
# For example: 284ms will be converted to 0:00:02.84
def convert_timestamp(time_ms):
    seconds = math.floor((time_ms/1000)%60)
    minutes = math.floor((time_ms/(1000*60))%60)
    millis = time_ms - ((minutes*1000*60) + (seconds*1000))
    millis = round(millis/10)
    return f'0:{str(minutes).rjust(2, "0")}:{str(seconds).rjust(2, "0")}.{str(millis).rjust(2, "0")}'


# Writes a line of subtitles to the ASS subtitle file in the correct format
def write_subtitles(subs_file_name, words, start, end, style):
    text = ' '.join(words)
    start_time = convert_timestamp(start)
    end_time = convert_timestamp(end)

    with open(subs_file_name, 'a') as subs_file:
        subs_file.write(f'\nDialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}')


# Creates the ASS subtitle file which will define the style for the subtitles and when they should appear
def generate_subtitles(transcript_words, sub_words, date, author):
    print('Creating subtitles...')

    subs_file_path = '/tmp/subs.ass'

    # The base file defines the style of the subtitles and global variables, and will always be the same
    base_ass_file = '''[Script Info]
PlayResY: 600
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Info,Futura,30,&H00F5F5F5,&H00F5F5F5,&H000A0A0A,&H000A0A0A,-1,0,1,3,2,5,40,40,0,0
Style: Title,Futura,40,&H00F5F5F5,&H00F5F5F5,&H000A0A0A,&H000A0A0A,-1,0,1,3,3,5,20,20,0,0
Style: Sub,Futura,20,&H00F5F5F5,&H00F5F5F5,&H000A0A0A,&H000A0A0A,-1,0,1,2,2,5,20,20,0,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'''

    with open(subs_file_path, 'w') as subs_file:
        subs_file.write(base_ass_file)

    font = ImageFont.truetype(f'{RESOURCES_DIR}/Futura.ttc')

    start_time = 0
    last_end = 0
    words = []
    cur_words = []
    title = 0

    # Iterate over all the words in the transcript and generate subtitles
    # The subtitles will be shown such that one full line of words will be shown on the screen at a time
    # Therefore, if the current text width is longer than one line, or if there is a pause in the speech, then a new subtitle will need to be generated
    for i in range(len(transcript_words)):
        mark = transcript_words[i]
        cur_start = mark['start']
        text_width = font.getsize(f"{' '.join(cur_words)} {sub_words[i]}")[0]
        if ((cur_start - last_end) > 0.1) or text_width >= 125:
            # Use a different style of text for the intro sequence and write the date below the title
            if title == 0:
                write_subtitles(subs_file_path, words, start_time*1000, cur_start*1000, 'Title')
                date_string = date.strftime('%B %d, %Y')
                write_subtitles(subs_file_path, date_string.split(' '), 854, cur_start*1000, 'Info')
                title = 1
            else:
                write_subtitles(subs_file_path, words, start_time*1000, cur_start*1000, 'Info')
            words = []
            cur_words = []
            start_time = cur_start

        words.append(sub_words[i])
        cur_words.append(sub_words[i])
        last_end = mark['end']

    if len(words) > 0:
        write_subtitles(subs_file_path, words, start_time*1000, 60000, 'Info')

    # Write the authors name below the final line of text for half a second
    last_start = last_end + 0.5
    author_text = f'- {author}'
    write_subtitles(subs_file_path, author_text.split(' '), last_start*1000, 60000, 'Sub')

    return subs_file_path


# Loop the background clip using FFmpeg if the length of the quote is longer than the length of the clip
def loop_clip(clip_path, duration):
    video_capture = cv2.VideoCapture(clip_path)
    video_duration = video_capture.get(cv2.CAP_PROP_FRAME_COUNT)/30

    if video_duration >= duration:
        return clip_path
    
    print ('Looping clip...')

    output_filepath = '/tmp/looped.mp4'
    loops = math.floor(duration/video_duration)
    execute(f'{RESOURCES_DIR}/ffmpeg -stream_loop {loops} -i {clip_path} -y {output_filepath}')
    return output_filepath


# Edit all of the individualt components (background clip, tts audio, subtitles) together using FFmpeg
def create_final_video(clip_path, audio_path, subs_path, duration):
    print('Creating final video...')

    output_file = '/tmp/final.mp4'
    execute(f'{RESOURCES_DIR}/ffmpeg -i {audio_path} -i {clip_path} -vf "ass={subs_path}:fontsdir={RESOURCES_DIR}" -t {duration}s -y {output_file}')
    return output_file


# Get the access key from DynamoDB and refresh credentials if necessary to authenticate the YouTube API
def get_authenticated_service():
    print('Retrieving auth tokens...')

    ddb = boto3.client('dynamodb')

    response = ddb.get_item(
        TableName='AccessKeys',
        Key={
            'service': {
                'S': 'youtube_refresh'
            }
        }
    )
    
    refresh_token = response['Item']['key']['S']

    response = ddb.get_item(
        TableName='AccessKeys',
        Key={
            'service': {
                'S': 'youtube'
            }
        }
    )
    
    token = response['Item']['key']['S']

    user_info = {
        'token': token,
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    credentials = Credentials.from_authorized_user_info(user_info)
    if credentials.expired:
        credentials.refresh(Request())

    youtube = build('youtube', 'v3', credentials=credentials)    

    return youtube


# Upload the video to YouTube with the correct title and description
def upload_video(video_path, link, youtube):
    print('Uploading video...')

    title = 'Quote of the Day #motivation #shorts #quotes'
    description = f'''New quotes daily!

Quotes of the day playlist: https://www.youtube.com/playlist?list={PLAYLIST_ID}

Quote from BrainyQuote: {link}

#shorts #quotes'''

    tags = ['quotes', 'motivation', 'inspiration']
    category_id = 24
    privacy_status = 'public'

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': category_id,
            'tags': tags
        },
        'status': {
            'privacyStatus': privacy_status
        }
    }

    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    status, response = insert_request.next_chunk()
    print(response)
    return response['id']


# Once the video is uploaded to YouTube, add it to a Quote of the Day playlist
def add_video_to_playlist(video_id, youtube):
    print('Adding video to playlist...')

    part = 'snippet'
    body = {
        'snippet': {
            'playlistId': f'{PLAYLIST_ID}',
            'resourceId': {
                'kind': 'youtube#video',
                'videoId': video_id
            }
        }
    }

    youtube.playlistItems().insert(part=part, body=body).execute()
