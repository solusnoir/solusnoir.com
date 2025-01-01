from google.oauth2 import service_account

# Path to your service account credentials JSON file
credentials = service_account.Credentials.from_service_account_file(
    '/Users/arnostyns/Desktop/solus_aiV2/solus-noir/solusnoir-446321-79801a466e30.json'
)

# Print a confirmation message if credentials are loaded successfully
print("Credentials loaded successfully!")
é