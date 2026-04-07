from google_auth_oauthlib.flow import InstalledAppFlow
import json

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    ['https://www.googleapis.com/auth/gmail.send',
     'https://www.googleapis.com/auth/calendar']
)
creds = flow.run_local_server(port=8094)
json.dump({
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': list(creds.scopes),
}, open('oauth_token.json', 'w'), indent=2)
print('Done!')
