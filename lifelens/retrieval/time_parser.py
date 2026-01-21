import datetime

def parse_time_filter(query: str):
    """
    Heuristic parser to extract time filters from a query.
    Returns a dictionary suitable for Qdrant range filter or None.
    
    Supported phrases:
    - "yesterday"
    - "today"
    - "last week" (last 7 days)
    """
    query_lower = query.lower()
    
    now = datetime.datetime.now()
    today_start = datetime.datetime(now.year, now.month, now.day).timestamp()
    
    if "today" in query_lower:
        return {
            "timestamp": {
                "gte": int(today_start)
            }
        }
        
    if "yesterday" in query_lower:
        yesterday_start = today_start - 86400
        return {
            "timestamp": {
                "gte": int(yesterday_start),
                "lt": int(today_start)
            }
        }
        
    if "last week" in query_lower:
        week_start = today_start - (86400 * 7)
        return {
            "timestamp": {
                "gte": int(week_start)
            }
        }
        
    return None
