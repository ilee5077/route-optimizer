from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

# Initialize OpenStreetMap's free geocoder with a custom user_agent
geolocator = Nominatim(user_agent="sydney_fleet_optimizer", timeout=10)
# upgrade later going production, consider using Google Maps API for more reliable geocoding
# geolocator = GoogleV3(api_key="YOUR_GOOGLE_MAPS_API_KEY")

geocode_with_delay = RateLimiter(geolocator.geocode, min_delay_seconds=2)


def geocode_address(address: str) -> dict:
    """
    Converts a Sydney street address into (latitude, longitude).
    Appends ', Sydney, NSW, Australia' to enforce local search accuracy.
    """
    full_search_string = f"{address}, Sydney, NSW, Australia"
    print(f"-> Geocoding: '{full_search_string}'...")

    location = geocode_with_delay(full_search_string)
    if location:
        return {"latitude": location.latitude, "longitude": location.longitude}
    else:
        raise ValueError(f"Could not geocode address: '{address}'")
