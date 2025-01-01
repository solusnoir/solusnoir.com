from google.oauth2 import service_account

# Path to your service account credentials file
SERVICE_ACCOUNT_FILE = '/Users/arnostyns/Desktop/solus_aiV2/solus-noir/solusnoir-446321-79801a466e30.json'

# Load the credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)

# Test the credentials by printing the email associated with the service account
print(f"Credentials are valid. Service account email: {credentials.service_account_email}")

