import sys
import subprocess
from os import path

from docusign_esign import ApiClient
from docusign_esign.client.api_exception import ApiException
from docusign_esign.apis import EnvelopesApi  # Import EnvelopesApi correctly
from app.jwt_helpers import get_jwt_token, get_private_key
from app.jwt_config import DS_JWT

# pip install DocuSign SDK
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'docusign_esign'])

SCOPES = [
    "signature", "impersonation"
]

def get_consent_url():
    url_scopes = "+".join(SCOPES)
    redirect_uri = "https://developers.docusign.com/platform/auth/consent"
    consent_url = f"https://{DS_JWT['authorization_server']}/oauth/auth?response_type=code&" \
                  f"scope={url_scopes}&client_id={DS_JWT['ds_client_id']}&redirect_uri={redirect_uri}"
    return consent_url

def get_token(private_key, api_client):
    token_response = get_jwt_token(private_key, SCOPES, DS_JWT["authorization_server"], DS_JWT["ds_client_id"],
                                   DS_JWT["ds_impersonated_user_id"])
    access_token = token_response.access_token
    user_info = api_client.get_user_info(access_token)
    accounts = user_info.get_accounts()
    api_account_id = accounts[0].account_id
    base_path = accounts[0].base_uri + "/restapi"
    return {"access_token": access_token, "api_account_id": api_account_id, "base_path": base_path}

def get_args(api_account_id, access_token, base_path):
    envelope_id = input("Please enter the envelope ID: ")

    args = {
        "account_id": api_account_id,
        "base_path": base_path,
        "access_token": access_token,
        "envelope_id": envelope_id
    }

    return args

def fetch_envelope_data(api_client, args):
    envelopes_api = EnvelopesApi(api_client)  # Correctly instantiate EnvelopesApi
    try:
        envelope = envelopes_api.get_envelope(args["account_id"], args["envelope_id"])
        envelope_documents = envelopes_api.list_documents(args["account_id"], args["envelope_id"])
        print("Envelope status:", envelope.status)
        for document in envelope_documents.envelope_documents:
            print("Document ID:", document.document_id)
            print("Document Name:", document.name)
    except ApiException as e:
        print("Error while retrieving envelope data:", e)
        print("Reason:", e.reason)
        print("HTTP response headers:", e.headers)
        print("HTTP response body:", e.body.decode('utf8'))

def run_example(private_key, api_client):
    jwt_values = get_token(private_key, api_client)
    args = get_args(jwt_values["api_account_id"], jwt_values["access_token"], jwt_values["base_path"])
    fetch_envelope_data(api_client, args)

def main():
    api_client = ApiClient()
    api_client.set_base_path(DS_JWT["base_uri"])
    api_client.set_oauth_host_name(DS_JWT["authorization_server"])

    private_key = get_private_key(DS_JWT["private_key_file"]).encode("ascii").decode("utf-8")

    try:
        run_example(private_key, api_client)
    except ApiException as err:
        body = err.body.decode('utf8')
        if "consent_required" in body:
            consent_url = get_consent_url()
            print("Open the following URL in your browser to grant consent to the application:")
            print(consent_url)
            consent_granted = input("Consent granted? Select one of the following: \n 1)Yes \n 2)No \n")
            if consent_granted == "1":
                run_example(private_key, api_client)
            else:
                sys.exit("Please grant consent")

main()


# 61c54ffd-703f-4b49-9cf8-3375a5ab4c59