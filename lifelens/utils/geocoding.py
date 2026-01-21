from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def search_location(query):
    """
    Search for a location by name/address and return coordinates.
    Uses OpenStreetMap's Nominatim geocoder (free, no API key needed).
    
    Args:
        query: Location name or address (e.g., "Eiffel Tower, Paris" or "New York")
    
    Returns:
        dict with 'lat', 'lon', 'display_name' or None if not found
    """
    if not query or len(query) < 3:
        return None
    
    try:
        # Initialize geocoder with a user agent
        geolocator = Nominatim(user_agent="lifelens_memory_app")
        
        # Search for location
        location = geolocator.geocode(query, timeout=10)
        
        if location:
            return {
                "lat": location.latitude,
                "lon": location.longitude,
                "display_name": location.address
            }
        else:
            return None
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
