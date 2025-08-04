from tavily import TavilyClient
from config import TAVILY_API_KEY

# initialize the tavily client with the api key
client = TavilyClient(api_key=TAVILY_API_KEY)

def webcrawl(url):
    try:
        # Use the extract method with urls parameter (expects a list)
        response = client.extract(urls=[url])
        
        # Based on the GitHub docs, response has a "results" key with extracted content
        if isinstance(response, dict) and "results" in response:
            results = response["results"]
            if results and len(results) > 0:
                # Get the first result (since we only passed one URL)
                first_result = results[0]
                # Extract the raw_content from the result
                content = first_result.get("raw_content", "")
                return content if content else None
        
        # Fallback: try to get content directly if structure is different
        elif isinstance(response, str):
            return response
        
        return None
        
    except Exception as e:
        print(f"An error occurred while crawling the URL {url}: {e}")
        return None