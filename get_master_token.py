import json
import webbrowser
import gpsoauth

email = 'james.beeching9@gmail.com'
android_id = '0123456789abcdef'

print("Opening https://accounts.google.com/EmbeddedSetup in your browser...")
print()
webbrowser.open('https://accounts.google.com/EmbeddedSetup')
print("Steps:")
print("  1. Log in and click 'I agree' (ignore any loading spinner)")
print("  2. Open DevTools (F12) > Application > Cookies > accounts.google.com")
print("  3. Find the cookie named 'oauth_token' (starts with oauth2_4/...)")
print()
token = input("Paste the oauth_token cookie value here: ").strip()

master_response = gpsoauth.exchange_token(email, token, android_id)

print(f"Full response for debugging:")
print(json.dumps(master_response))

if 'Token' not in master_response:
    print(f"\nError: {master_response.get('Error', 'Unknown error')}")
else:
    master_token = master_response['Token']
    print(f"\nMaster token: {master_token}")