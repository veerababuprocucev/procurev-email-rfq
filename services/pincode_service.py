import requests


def get_location_from_pincode(pincode):

    try:

        print(f"Searching Pincode: {pincode}")

        response = requests.get(
            f"https://api.postalpincode.in/pincode/{pincode}",
            timeout=10
        )

        data = response.json()

        print("API Response:")
        print(data)

        if (
            data
            and data[0]["Status"] == "Success"
            and data[0]["PostOffice"]
        ):

            post_office = data[0]["PostOffice"][0]

            district = post_office.get(
                "District",
                ""
            )

            state = post_office.get(
                "State",
                ""
            )

            location = (
                f"{district}, {state}"
            )

            print(
                f"Mapped Location: {location}"
            )

            return location

        print(
            "Pincode not found in API"
        )

    except Exception as e:

        print(
            f"Pincode Lookup Error: {e}"
        )

    return ""


if __name__ == "__main__":

    result = get_location_from_pincode(
        "517419"
    )

    print(
        f"Final Result: {result}"
    )