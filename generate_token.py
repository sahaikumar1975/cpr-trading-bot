"""Fyers Token Generator - Run daily before market"""
from fyers_apiv3 import fyersModel
import webbrowser

print("=" * 60)
print("FYERS ACCESS TOKEN GENERATOR")
print("=" * 60)

app_id = input("\nEnter Fyers App ID: ").strip()
secret_key = input("Enter Fyers Secret Key: ").strip()
redirect_uri = "https://127.0.0.1"

session = fyersModel.SessionModel(
    client_id=app_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code"
)

login_url = session.generate_authcode()
print(f"\n🔗 Opening browser...\n{login_url}\n")
webbrowser.open(login_url)

print("After login, copy the ENTIRE URL from browser")
auth_code = input("\n📥 Paste auth_code from URL: ").strip()

if "auth_code=" in auth_code:
    auth_code = auth_code.split("auth_code=")[1].split("&")[0]

session.set_token(auth_code)
response = session.generate_token()

if response['s'] == 'ok':
    token = response['access_token']
    print("\n" + "=" * 60)
    print("✅ ACCESS TOKEN GENERATED")
    print("=" * 60)
    print(f"\n{token}\n")
    print("📝 Update in .env file:")
    print(f"FYERS_ACCESS_TOKEN={token}")
    print("\n💾 Saving to token.txt...")
    
    with open('token.txt', 'w') as f:
        f.write(token)
    
    print("✅ Saved to token.txt")
    print("\n⚠️  This token expires at 3:30 PM today")
    print("Run this script daily before 9:15 AM")
    print("=" * 60)
else:
    print(f"\n❌ Error: {response}")
    print("Please try again")