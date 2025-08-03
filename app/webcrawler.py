from tavily import TavilyClient
from config import TAVILY_API_KEY

# initialize the tavily client witht he api key
client = TavilyClient(api_key=TAVILY_API_KEY)

def webcrawl(url):
  
  try:
    # the response holds the web page content
    response = client.website_content(url)
    # extract the content from the response
    content = response.get("content", "")
    # return the content
    return content
  except Exception as e:
    print(f"An error occurred while crawling the URL {url}: {e}")
    return None
  