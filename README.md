# DumbGenie

## Associated Videos

- [Original YouTube video](https://www.youtube.com/watch?v=fAHMBiI6rIk)

## Project Setup

This is a nodejs project and it is meant to run on AWS Lambda. The original YouTube video describes the code and setup process in more detail.

### Twitter

Go to the [developer page](https://developer.twitter.com/en/docs/twitter-api) for Twitter. You will need to sign up and create a project and app to obtain the necessary credentials. Follow this [tutorial](https://developer.twitter.com/en/docs/tutorials/step-by-step-guide-to-making-your-first-request-to-the-twitter-api-v2).

### Youtube

You will need to go through a similar process for the [YouTube API](https://developers.google.com/youtube/v3) to obtain an API key.

### Deploying to AWS

Start by creating a ZIP file for the code by running the following commands:
```
npm install
zip -r lambda.zip .
```
Sign up for an [AWS](https://aws.amazon.com/) account. After you create an account, create a new Lambda function. You can use [this guide](https://docs.aws.amazon.com/lambda/latest/dg/getting-started.html) if you are unsure. Choose `Node.js 12.x` as the runtime. For the code source, upload the `lambda.zip` file. Go to the lambda configuration and set the environment variables: `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `CONSUMER_KEY`, `CONSUMER_SECRET`, `YOUTUBE_API_KEY` appropriately. Lastly, add an EventBridge trigger to the lambda and configure it run once an hour. Now the code will run once an hour.