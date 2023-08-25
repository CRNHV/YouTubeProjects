import json
import requests
import os
import boto3

client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
redirect_uri = os.environ.get('REDIRECT_URI')
token_uri = 'https://oauth2.googleapis.com/token'

ddb = boto3.client('dynamodb')

def lambda_handler(event, context):
    if event['rawPath'] != '/':
        return {
            'statusCode': 200,
            'body': json.dumps('Ignoring')
        }
    
    # Retrieve access token using auth code passed to the function
    code = event['queryStringParameters']['code']
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    response = requests.post(token_uri, data=data)
    
    access_token = response.json()['access_token']
    refresh_token = response.json()['refresh_token']
    
    # Update access token and refresh token in DynamoDB
    ddb.put_item(
        TableName='AccessKeys',
        Item={
            'service': {
                'S': 'youtube'
            },
            'key': {
                'S': access_token
            }
        } 
    )
    
    ddb.put_item(
        TableName='AccessKeys',
        Item={
            'service': {
                'S': 'youtube_refresh'
            },
            'key': {
                'S': refresh_token
            }
        } 
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Updated access key')
    }