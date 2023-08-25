import json
import boto3
import requests
import os
import smtplib
from email.mime.text import MIMEText

ddb = boto3.client('dynamodb')

def lambda_handler(event, context):
    invalidate_token()
    send_email()
    
# Invalidate the existing token refresh token
# If we don't invalidate the current token, then we may not receive a new refesh token
def invalidate_token():
    response = ddb.get_item(
        TableName='AccessKeys',
        Key={
            'service': {
                'S': 'youtube_refresh'
            }
        }
    )
    
    token = response['Item']['key']['S']
    requests.post('https://oauth2.googleapis.com/revoke', params={'token': token}, headers = {'content-type': 'application/x-www-form-urlencoded'})
    

# Send email to yourself containing the authorization refresh URL
def send_email():
    refresh_url = os.environ.get('REFRESH_URL')
    smtpServer = 'smtp.gmail.com'
    port = 587
    senderName = os.environ.get('SENDER_NAME')
    senderEmail = os.environ.get('SENDER_EMAIL')
    recipients = [senderEmail]
    password = os.environ.get('PASSWORD')
    subject = 'Refresh Credentials'
    
    htmlText = '''
        <html>
        <head></head>
        <body>
        <a href="{}">refresh link</a>
        </body>
        </html>
        '''.format(refresh_url)
    
    
    
    message = MIMEText(htmlText, 'html')
    message['Subject'] = subject
    message['From'] = '{} <{}>'.format(senderName, senderEmail)
    message['To'] = recipients[0]
    
    with smtplib.SMTP(smtpServer, port=port) as server:
        server.starttls()
        server.login(senderEmail, password=password)
        server.send_message(message)
