from datetime import datetime, timedelta

def find_related_memories(memories, current_memory):
    """
    Find memories related to the current one based on:
    - Same day
    - Same people tagged
    - Similar timestamps (within 1 hour)
    """
    if not memories or not current_memory:
        return []
    
    related = []
    current_ts = current_memory.get("timestamp", 0)
    current_date = datetime.fromtimestamp(current_ts).date()
    current_people_str = current_memory.get("person_tags") or ""
    current_people = set(current_people_str.split(",")) if current_people_str else set()
    
    for mem in memories:
        if mem.get("timestamp") == current_ts:
            continue  # Skip self
        
        mem_ts = mem.get("timestamp", 0)
        mem_date = datetime.fromtimestamp(mem_ts).date()
        mem_people_str = mem.get("person_tags") or ""
        mem_people = set(mem_people_str.split(",")) if mem_people_str else set()
        
        # Same day
        if mem_date == current_date:
            related.append({"reason": "Same day", "memory": mem})
            continue
        
        # Same people
        if current_people & mem_people:  # Intersection
            related.append({"reason": f"Same person: {', '.join(current_people & mem_people)}", "memory": mem})
            continue
        
        # Within 1 hour
        if abs(current_ts - mem_ts) < 3600:
            related.append({"reason": "Around the same time", "memory": mem})
    
    return related[:5]  # Limit to 5 related memories
