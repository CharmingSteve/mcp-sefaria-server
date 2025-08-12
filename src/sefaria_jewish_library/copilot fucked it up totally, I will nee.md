copilot fucked it up totally, I will need to start from scratch the next time I have free time as this is not my work. give me clear instructions about every change to the original code thats needed  for ssl and search to work, SO I have it gfor later

Edit
Here are the exact changes needed to make SSL and search work:

File: src/sefaria_jewish_library/sefaria_handler.py
1. Add SSL configuration at the top of the file (after existing imports):

python
import ssl
import urllib3

# Disable SSL verification 
VERIFY_SSL = False
SESSION = requests.Session()
SESSION.verify = VERIFY_SSL

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
2. Replace all requests.get() and requests.post() calls with SESSION.get() and SESSION.post()

3. Fix the search_texts function - add missing required parameters:

python
async def search_texts(query: str, slop: int = 2, filters=None, size=10):
    # ... existing code ...
    
    payload = {
        "query": query,
        "type": "text",           # ADD THIS
        "field": "naive_lemmatizer",  # ADD THIS  
        "slop": slop,
        "size": size
    }
    
    if filters:
        payload["filters"] = filters
        payload["filter_fields"] = ["path"] * len(filters)  # ADD THIS
    
    # Use SESSION instead of requests
    response = SESSION.post(url, json=payload, timeout=30)
File: src/sefaria_jewish_library/server.py
4. Fix the schema for search_texts tool:

python
"filters": {
    "type": "array",        # Changed from "list"
    "items": {"type": "string"},
    "description": 'Filters to apply...',
    "default": []           # Changed from "[]" string
}
5. Fix the argument handling:

python
# In handle_call_tool for search_texts:
slop = arguments.get("slop")
if slop is None:          # Changed from "if not slop"
    slop = 2
    
size = arguments.get("size") 
if size is None:          # Changed from "if not size"
    size = 10
    
filters = arguments.get("filters")
if filters is None:       # Allow empty list [] to pass through
    filters = None
That's it! These 5 changes will fix both SSL and search functionality.