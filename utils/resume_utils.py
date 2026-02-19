import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_total_experience(exp_list):
    """
    Calculates total experience in years using interval merging.
    This ensures that overlapping employment periods are not double-counted.
    """
    if not exp_list or not isinstance(exp_list, list):
        return "0.0"

    intervals = []
    
    for exp in exp_list:
        if not isinstance(exp, dict): continue
        
        # Capture Start/End
        start_str = exp.get("employment_start_date") or exp.get("dates", {}).get("start")
        end_str = exp.get("employment_end_date") or exp.get("dates", {}).get("end")
        
        if not start_str: continue

        try:
            start_date = parse_date(start_str)
            if not end_str or any(x in str(end_str).lower() for x in ["present", "current", "till date", "on going"]):
                end_date = datetime.now()
            else:
                end_date = parse_date(end_str)
                
            if start_date and end_date and end_date >= start_date:
                intervals.append((start_date, end_date))
        except Exception:
            continue

    if not intervals:
        return "0.0"

    # Merge Overlapping Intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    if intervals:
        curr_start, curr_end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start <= curr_end:  # Overlap or contiguous
                curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))

    # Calculate Summed Duration
    total_months = 0
    for start, end in merged:
        delta = relativedelta(end, start)
        months = (delta.years * 12) + delta.months
        # Add 1 month to include the start month boundary if common in resume counting
        total_months += max(0, months + 1) 

    years = round(total_months / 12, 1)
    return str(years)

def parse_date(date_str):
    """Helper to parse a date string into a datetime object."""
    if not date_str or not isinstance(date_str, str):
        return None
        
    date_str = date_str.strip().lower()
    
    # Try different formats
    formats = [
        "%B %Y", "%b %Y", "%m/%Y", "%Y-%m-%d", "%Y-%m", "%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    # Try Regex for "MM/YYYY" or "YYYY"
    match = re.search(r'(\d{1,2})[/-](\d{4})', date_str)
    if match:
        return datetime(int(match.group(2)), int(match.group(1)), 1)
        
    match = re.search(r'(\d{4})', date_str)
    if match:
        return datetime(int(match.group(1)), 1, 1)
        
    return None

def extract_tokens_from_response(llm_msg):
    """
    Extremely robust token extractor for LangChain messages.
    """
    try:
        # Debug: Print the raw type and content to console
        print(f"DEBUG: Processing message type: {type(llm_msg)}")
        
        # 1. Try standard LangChain usage_metadata attribute (Top-Level)
        if hasattr(llm_msg, "usage_metadata") and llm_msg.usage_metadata:
            usage = llm_msg.usage_metadata
            print(f"DEBUG: Found top-level usage_metadata: {usage}")
            return {
                "input": usage.get("prompt_token_count", usage.get("input_tokens", 0)),
                "output": usage.get("candidates_token_count", usage.get("output_tokens", 0))
            }

        # 2. Try response_metadata (Dict inside message)
        meta = getattr(llm_msg, "response_metadata", {})
        print(f"DEBUG: Response Metadata: {meta}")

        # Check for usage_metadata inside response_metadata
        usage = meta.get("usage_metadata")
        if usage:
            return {
                "input": usage.get("prompt_token_count", usage.get("input_tokens", 0)),
                "output": usage.get("candidates_token_count", usage.get("output_tokens", 0))
            }

        # Check for token_usage (OpenAI style)
        token_usage = meta.get("token_usage")
        if token_usage:
            return {
                "input": token_usage.get("prompt_tokens", 0),
                "output": token_usage.get("completion_tokens", 0)
            }

        # Check for raw Gemini keys
        if "prompt_token_count" in meta:
            return {
                "input": meta.get("prompt_token_count", 0),
                "output": meta.get("candidates_token_count", 0)
            }

    except Exception as e:
        print(f"CRITICAL: Failed to extract tokens: {e}")
    
    return {"input": 0, "output": 0}
