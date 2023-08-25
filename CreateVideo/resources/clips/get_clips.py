import requests
import os
import subprocess
import cv2


# Execute a given shell command
def execute(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    if process.returncode != 0:
        print(out)
        print(err)
        exit()

# Crops and resizes the clip to be 1080x1920 pixels
def crop_video(input_video, output_video):
    vid = cv2.VideoCapture(input_video)
    height = vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
    width = vid.get(cv2.CAP_PROP_FRAME_WIDTH)
    
    if width/height > 0.5625:
        left_margin = (width*(1920/height)-1080)/2
        execute(f'ffmpeg -i {input_video} -vf "scale=-1:1920, crop=1080:1920:{left_margin}:0, fps=30" -an -y {output_video}')
    else:
        top_margin = (height*(1080/width)-1920)/2
        execute(f'ffmpeg -i {input_video} -vf "scale=1080:-1, crop=1080:1920:0:{top_margin}, fps=30" -an -y {output_video}')


def main():
    pexels_headers = {
    'Authorization': os.environ.get('PEXELS_API_KEY'),
    }

    params = {
        'query': 'drone nature',
        'per_page': '30',
    }

    response = requests.get('https://api.pexels.com/videos/search', params=params, headers=pexels_headers)

    # Retrieve all the clips from Pexels
    for i, video in enumerate(response.json()['videos']):
        print(f'Getting video: {i+1}')
        video_id = video['id']
        video_url = f'https://www.pexels.com/video/{video_id}/download'
        video_response = requests.get(video_url)
        
        # Save video to a temporary file
        temp_filename = 'tmp.mp4'
        with open(temp_filename, 'wb') as video_file:
            video_file.write(video_response.content)

        # Crop the temporary file using FFmpeg and save it to as a new video
        video_filename = f'{i+1}.mp4'
        crop_video(temp_filename, video_filename)

    # Remove temporary file
    os.remove(temp_filename)


if __name__ == '__main__':
    main()