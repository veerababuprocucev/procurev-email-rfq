import requests

# ----------------------------------
# BUYER API
# ----------------------------------

BUYER_API_URL = (
    "https://p2pv1servicesdev-etfrcte5fhdvfrd4.centralindia-01.azurewebsites.net/automate/validateEmail"
)


def verify_buyer(email):

    try:

        response = requests.post(
            BUYER_API_URL,
            params={
                "email": email
            },
            timeout=30
        )

        data = response.json()

        if data.get("code") == "00":

            print(
                "Buyer API Success"
            )

            return data

        # Fallback to QUA backend if not found on DEV
        fallback_url = "https://qua-backend-prod-hsfthrgxfmhkdgav.eastasia-01.azurewebsites.net/procucev/rest/users/getBuyerByEmail"
        fb_response = requests.post(
            fallback_url,
            json={
                "username": email
            },
            timeout=30
        )
        fb_data = fb_response.json()
        if fb_data.get("code") == "00":
            print("Buyer API Success (Fallback)")
            return fb_data

        print(
            f"Buyer API Failed: {data.get('description')}"
        )

        return None

    except Exception as e:

        print(
            f"Buyer API Error: {e}"
        )

        return None