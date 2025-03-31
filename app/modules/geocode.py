import requests

class GoogleGeocodingAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def geocode_address(self, address):
        """
        Converts an address into latitude and longitude.
        
        Args:
            address (str): The address to geocode.
        
        Returns:
            dict: Contains latitude, longitude, and full response.
        """
        params = {
            "address": address,
            "key": self.api_key
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] == "OK":
                location = data["results"][0]["geometry"]["location"]
                return {
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "raw": data
                }
            else:
                print(f"[ERROR] Geocoding failed: {data['status']}")
                return None
        except requests.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return None
