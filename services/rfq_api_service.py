import requests

# ----------------------------------
# RFQ API
# ----------------------------------

RFQ_CLIENT_API_URL = (
    "https://p2pv1servicesdev-etfrcte5fhdvfrd4.centralindia-01.azurewebsites.net/rest/gmt/createRFQByClient"
)

RFQ_AUTOMATE_API_URL = (
    "https://p2pv1servicesdev-etfrcte5fhdvfrd4.centralindia-01.azurewebsites.net/automate/raiseRfq"
)


def create_rfq_api(rfq_object, token=None):

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # If a JWT session token is present, use the Client API endpoint
        if token:
            headers["Authorization"] = f"Bearer {token}"
            print(f"\nSending RFQ To Client API ({RFQ_CLIENT_API_URL})...")

            response = requests.post(
                RFQ_CLIENT_API_URL,
                json=rfq_object,
                headers=headers,
                timeout=60
            )

            print(f"HTTP Status : {response.status_code}")

            try:
                data = response.json()
            except Exception:
                data = response.text

            print("\nRFQ API RESPONSE")
            print(data)

            if response.status_code == 200:
                return data

            print(f"Client API returned status {response.status_code}, falling back to automated endpoint...")

        # Automated RFQ creation endpoint (designed for email bot without user JWT session)
        print(f"\nSending RFQ To Automated API ({RFQ_AUTOMATE_API_URL})...")
        response = requests.post(
            RFQ_AUTOMATE_API_URL,
            json=rfq_object,
            headers=headers,
            timeout=60
        )

        print(f"HTTP Status : {response.status_code}")
        try:
            data = response.json()
        except Exception:
            data = response.text

        print("\nRFQ API RESPONSE")
        print(data)

        return data

    except requests.exceptions.RequestException as e:

        print(f"RFQ API Error: {e}")

        return {
            "status": False,
            "code": "REQUEST_ERROR",
            "description": str(e)
        }

    except Exception as e:

        print(f"Unexpected Error: {e}")

        return {
            "status": False,
            "code": "UNKNOWN_ERROR",
            "description": str(e)
        }