# -- Run this on google colab an dmake sure to add client_secret.json in the  colab --
!pip install --quiet google-auth-oauthlib google-auth-httplib2 google-api-python-client

import os
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_token_headless():
    if not os.path.exists("/content/client_secret.json"): # -- change the path -- 
        print("❌ Error: 'client_secrets.json' not found in your Colab files! Please upload it.")
        return

    # Use out-of-band / manual flow compatible with cloud notebooks
    flow = Flow.from_client_secrets_file(
        "/content/client_secret.json", # -- change here as well --
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )

    auth_url, _ = flow.authorization_url(prompt='consent')

    print("🚀 Click the link below, authorize the app with your YouTube account, and copy the code provided:\n")
    print(auth_url)

    code = input("\n🔑 Paste the authorization code here and press Enter: ").strip()

    flow.fetch_token(code=code)
    creds = flow.credentials

    with open("token.json", "w") as token_file:
        token_file.write(creds.to_json())

    print("\n✅ Success! 'token.json' has been generated.")
    print("📥 Download 'token.json' from your Colab files and place it in your GitHub repository root folder.")

generate_token_headless()
