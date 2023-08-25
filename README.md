# YouTube Automation
This project is meant to be deployed as multiple [AWS Lambda Functions](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) in order to upload Quote of the Day videos to YouTube in a completely automated way. The architecture of the entire project is shown below:

![High level diagram](high-level-diagram.jpg)

If you are not interested in completley automating the process of uploading the video to YouTube, then you can mainly focus on the code from the [CreateVideo Lambda Function](CreateVideo/lambda_function.py) to just automate the entire editing process.

## Associated Videos
- [Original YouTube video](https://youtu.be/vLOgzi5y9xE)
- Code walkthrough video (Coming very soon)

## Prerequisites
- [Eleven Labs API](https://api.elevenlabs.io/docs)
    - Create an account at https://elevenlabs.io/
    - Your API key can be found by going to your 'Profile' tab
- [YouTube API](https://developers.google.com/youtube/v3)
    - Follow the steps [here](https://developers.google.com/youtube/v3/getting-started#before-you-start) to set up the YouTube API
        - You mainly need to just follow steps 1 trhough 3 and you can ignore steps about obtaining authorization credentials
- [AWS Account](https://aws.amazon.com/)
    - Create an AWS account at https://portal.aws.amazon.com/billing/signup
- [Pexels API](https://www.pexels.com/api/) (Optional)
    - This step is optional if you want to automatically collect stock footage from Pexels
    - Create a new account on https://www.pexels.com/
    - Your API key can be found [here](https://www.pexels.com/api/new/)
- [FFmpeg](https://ffmpeg.org/ffmpeg.html) (Optional)
    - This step is optional if you want to automate preprocessing video clips
    - Install FFmpeg using the method of your choice from [here](https://ffmpeg.org/download.html)

## UpdateAccessKey
This Lambda function serves as the callback function in the [OAuth 2.0 flow](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps) to obtain the access key in order to use the YouTube API.

### Setup and Deploy the Lambda Function
1. Start by creating a new AWS Lambda function
    1. Set the runtime to `Python 3.9`
    2. Under the advanced settings check the box for `Enable function URL` and select `NONE` for the `Auth type` setting
    3. Once the function is created you can find the function URL under the `Configuration` tab. Note down this function URL for later
2. Create a DynamoDB table to store YouTube access tokens
    1. Go to DynamoDB in AWS and create a new table with the name `AccessKeys`
    2. Set the partition key to `service` as `String` type
3. Create OAuth 2.0 credentials
    1. Go to the [credentials](https://console.developers.google.com/apis/credentials) page
    2. Click `Create credentials` > `OAuth client ID`
    3. Select the `Web application` application type
    4. Add a new authorized redirect URI and put the Lambda function URL
    5. Create the credentials and note down the client ID and client secret for later
4. Configure OAuth consent screen
    1. Go through the steps to [configure the OAuth consent screen](https://developers.google.com/workspace/guides/configure-oauth-consent). You can put any valid values for the App information/domain.
    2. Add `on.aws` as an authorized domain
    3. For the scopes, add the `https://www.googleapis.com/auth/youtube` scope
    4. For the test users, add the email for the YouTube account you want to upload videos for
5. Upload code for the Lambda function by [creating a .zip depoloyment package with dependencies](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-dependencies)
    1. Navigate to the UpdateAccessKey directory
        ```
        cd UpdateAccessKey
        ```
    2. Create package directory to install dependencies to
        ```
        mkdir package
        ```
    3. Install the `requests` package
        ```
        pip install --target ./package requests
        ```
    4. Create .zip file with installed packages
        ```
        cd package
        zip -r ../lambda.zip .
        ```
    5. Add lambda code to .zip file
        ```
        cd ..
        zip lambda.zip lambda_function.py
        ```
    6. Upload the .zip file as the code to the Lambda function
6. Configure environment variables
    1. Go to `Configuration` > `Environment variables` on the Lambda function
    2. Set the following environment variables:
        1. CLIENT_ID = \<Google OAuth client ID>
        2. CLIENT_SECRET = \<Google OAuth client secret>
        3. REDIRECT_URI = \<Lambda Function URL>
7. Grant the [function execution role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html) with DynamoDB full access
8. Navigate to the following URL (line breaks and spaces for readability). Replace `redirect_uri` and `client_id` values with your own
    ```
    https://accounts.google.com/o/oauth2/v2/auth?
        scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube&
        access_type=offline&
        response_type=code&
        include_granted_scopes=true&
        response_type=code&
        redirect_uri=<Lambda function URL>&
        client_id=<Google OAuth client ID>
    ```
9. Select the account you want to upload YouTube videos to and grant your app access to upload videos to your YouTube channel
10. If successful, you should see that the access key has been updated successfully and the access token has been updated in DynamoDB. Now you have an access token and refresh token that will be used by the CreateVideo Lambda function to automatically upload videos to YouTube

## RefreshAccessKey
If your OAuth app has a publishing status of `Testing` then the refresh token will expire after one week, so once a week the YouTube API tokens will need to be manually refreshed. This is the only manual part to this project and only needs to be done once a week. If you are able to publish your app then the refresh token should last indefinitley, and this step will not be needed. In order to minimize the effort required to manually refresh the access tokens, this Lambda function automatically invalidates the old access tokens and emails the authorization URL to yourself once a week. Then all you have to do is click the authorization URL from your email and reauthorize your app to get new tokens. You will need to have already followed the steps to setup the UpdateAccessKey Lambda function before setting up this function. You can also manually invalidate the old credentials and reauthorize your app manually once a week if you do not want to setup this Lambda function.

### Setup and Deploy the Lambda Function
1. Create an app password for the Google account you want to send and receive emails from
    1. Follow the [steps to create an app password](https://support.google.com/mail/answer/185833?hl=en) and mark it down for later
2. Create a new AWS Lambda function
    1. Set the runtime to `Python 3.9`
    2. Set the environment variables as follows
        1. PASSWORD=\<App password from setp 1>
        2. REFRESH_URL=\<Auth URL from step 7 of UpdateAccessKey setup>
        3. SENDER_EMAIL=\<Email of account with app password>
        4. SENDER_NAME=\<Name of sender which will appear in inbox>
3. Upload code for the Lambda function by [creating a .zip depoloyment package with dependencies](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-dependencies)
    1. Navigate to the RefreshAccessKey directory
        ```
        cd RefreshAccessKey
        ```
    2. Create package directory to install dependencies to
        ```
        mkdir package
        ```
    3. Install the `requests` package
        ```
        pip install --target ./package requests
        ```
    4. Create .zip file with installed packages
        ```
        cd package
        zip -r ../lambda.zip .
        ```
    5. Add lambda code to .zip file
        ```
        cd ..
        zip lambda.zip lambda_function.py
        ```
    6. Upload the .zip file as the code to the Lambda function
4. Add trigger to Lambda function
    1. Go to `Configuration` > `Triggers` and add a new trigger
    2. Select `EventBridge` as the source
    3. Create a new rule with the schedule expression for once a week. For example, the following expresssion will trigger the function once a week at 19:00 UTC on Wednesdays
        ```
        cron(0 19 ? * WED *)
        ```
5. Grant the [function execution role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html) with DynamoDB full access
6. Now once a week you will be sent an email with the link to reauthenticate your OAuth app in order to refresh access tokens

## CreateVideo
This Lambda function will automatically assemble the quote of the day video. It retrieves the quote from the [BrainyQuote quote of the day RSS feed](https://www.brainyquote.com/feeds/todays_quote). It uses Eleven Labs to create tts audio and then uses FFmpeg to edit the video together. It will then upload the video to YouTube using the YouTube API. This function is deployed as a container image instead of a .zip deployment package. This is because the code and resources of this Lambda function is too large to upload as a .zip file.

### Setup
Currently, the `CreateVideo/resources` directory structure looks like this:
```
resources
│   Futura.ttc
│   intro.mp3
│
└───clips
    │   get_clips.py
```

After completing the setup steps, the directory structure should look like:
```
resources
│   Futura.ttc
│   intro.mp3
│   ffmpeg
│
└───clips
│   │   get_clips.py
│   │   1.mp4
│   │   2.mp4
│   │   3.mp4
│   │   ...
│
└───vosk
    |...
```
1. Download FFmpeg executable to `resources` directory
    1. The FFmpeg executable can be downloaded from [here](https://ffmpeg.org/download.html) by following the steps for steps for your platform
    2. If you are on Linux, you can download the FFmpeg executable to the `resources` directory using the following commands:
       ```
       wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
       tar -xf ffmpeg-release-amd64-static.tar.xz
       mv ffmpeg-6.0-amd64-static/ffmpeg CreateVideo/resources/ffmpeg
       rm ffmpeg-release-amd64-static.tar.xz
       rm -rf ffmpeg-6.0-amd64-static
       ```
2. Download Vosk model to `resources` directory
    1. Download a Vosk model from [here](https://alphacephei.com/vosk/models) to use for Vosk speech recognition. The model used in this project is the `vosk-model-en-us-0.22` model.
    2. Once downloaded, unzip the file and place the directory in the `recources` directory and rename it to `vosk`
    3. This can be done with the following commands:
        ```
        wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
        unzip vosk-model-en-us-0.22.zip
        mv vosk-model-en-us-0.22 CreateVideo/resources/vosk
        rm vosk-model-en-us-0.22.zip
        ```
3. Download and preprocess background clips to `resources/clips` directory
    1. If you have a Pexels API key and FFmpeg installed, you can automate this process by running the `get_clips.py` script in the `resources/clips` directory:
        ```
        cd CreateVideo/resources/clips
        export PEXELS_API_KEY=<your Pexels API key>
        python get_clips.py
        ```
    2. Otherwise, you can manually retrieve your own background clips, resize them to be 1080x1920 pixels, and name them appropriatley

### Deploy Lambda Function
As previously mentioned this function is [deployed as a container image](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-instructions) instead of a .zip deployment package due to the size of the code and resources. You will need to have Docker and the AWS CLI installed as prerequisites
1. Build the Docker image using the following commands:
    ```
    cd CreateVideo
    docker build -t lambda-image:latest .
2. Deploy the image
    1. Get the login password to authenticate Docker CLI to your Amazon ECR registry
        ```
        aws ecr get-login-password --region <YourAWSRegion> | docker login --username AWS --password-stdin <YourAWSaccountID>.dkr.ecr.<YourAWSRegion>.amazonaws.com
        ```
    2. Create repository in Amazon ECR
        ```
        aws ecr create-repository --repository-name youtube-automation --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
        ```
    3. Copy the `repositoryUri` from the output of the previous command
    4. Tag your local image into Amazon ECR as the latest version
        ```
        docker tag lambda-image:latest <ECRrepositoryUri>:latest
        ```
    5. Deploy local image to Amazon ECR
        ```
        docker push <ECRrepositoryUri>:latest
        ```
    6. Create a new AWS Lambda function
        1. Select `Container image` and enter the ECR image that you deployed in teh last step
        2. Set the runtime to `Python 3.9`
        3. Add DynamoDB full access permission to the execution role
        4. Configure timeout to be 15 minutes, memory to be 10240MB, and ephemeral storage to be 5120MB
        5. Add a new EventBride trigger to Lambda function with a rule to trigger the function daily. For example, the following rule triggers the function everyday at 16:00 UTC
            ```
            cron(0 16 * * ? *)
            ```
        6. Configure the evironment variables
            1. CLIENT_ID=\<GoogleOauthClientID>
            2. CLIENT_SECRET=\<GoogleOauthClientSecret>
            3. ELEVEN_LABS_API_KEY=\<ElevenLabsAPIKey>
            4. PLAYLIST_ID=\<YouTubePlaylistID>

The Lambda function is now configured to run once a day and will upload a new quote of the day video to your YouTube channel automatically.  
