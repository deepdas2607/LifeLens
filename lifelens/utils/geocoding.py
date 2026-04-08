from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re

def search_location(query):
    """
    Search for a location by name/address and return coordinates.
    Uses OpenStreetMap's Nominatim geocoder with improved query handling.
    
    Args:
        query: Location name or address (e.g., "CRC, IIT Madras, Chennai" or "New York")
    
    Returns:
        dict with 'lat', 'lon', 'display_name' or None if not found
    """
    if not query or len(query) < 3:
        return None
    
    try:
        # Initialize geocoder with a user agent
        geolocator = Nominatim(user_agent="lifelens_memory_app", timeout=10)
        
        # Try multiple search strategies for better results
        strategies = [
            query,  # Original query
            _enhance_indian_location(query),  # Enhanced for Indian addresses
            _simplify_query(query)  # Simplified query
        ]
        
        for search_query in strategies:
            if not search_query:
                continue
                
            # Search for location with address details
            location = geolocator.geocode(
                search_query, 
                timeout=10,
                addressdetails=True,
                language='en'
            )
            
            if location:
                return {
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "display_name": location.address,
                    "search_query": search_query  # Store which query worked
                }
        
        # If all strategies failed, return None
        return None
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def _enhance_indian_location(query):
    """
    Enhance location queries for Indian addresses.
    Handles abbreviations like CRC, IIT, etc.
    """
    if not query:
        return query
    
    # Common Indian location expansions
    expansions = {
        r'\bCRC\b': 'Computer Research Centre',
        r'\bIIT\b': 'Indian Institute of Technology',
        r'\bIISc\b': 'Indian Institute of Science',
        r'\bNIT\b': 'National Institute of Technology',
        r'\bIIM\b': 'Indian Institute of Management',
        r'\bAIIMS\b': 'All India Institute of Medical Sciences'
    }
    
    enhanced = query
    for abbr, full in expansions.items():
        enhanced = re.sub(abbr, full, enhanced, flags=re.IGNORECASE)
    
    # Ensure India is mentioned for Indian institutions
    if any(inst in query.upper() for inst in ['IIT', 'CRC', 'IISc', 'NIT', 'IIM', 'AIIMS']):
        if 'India' not in enhanced and 'india' not in enhanced:
            enhanced += ', India'
    
    return enhanced if enhanced != query else None


def _simplify_query(query):
    """
    Simplify complex queries to major landmarks.
    Example: "CRC, IIT Madras, Chennai" -> "IIT Madras, Chennai, India"
    """
    if not query:
        return None
    
    # Split by comma and take last 2-3 parts (usually city/state/country)
    parts = [p.strip() for p in query.split(',')]
    
    if len(parts) >= 3:
        # Keep the major location parts (skip building/department names)
        simplified = ', '.join(parts[-3:])
        if 'India' not in simplified:
            simplified += ', India'
        return simplified
    
    return None
