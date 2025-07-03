import os
from langchain_tavily import TavilySearch
import hashlib
import json
import time

class OnlineSearchTool:
    """
    Tool for performing domain-restricted web search (Indian gov sites via Tavily) and returning a list of URLs.
    """
    def __init__(self, llm):
        self.llm = llm
        self.search_tool = TavilySearch(
            api_key=os.getenv("TAVILY_API_KEY"),
            model=llm,
            include_domains=["gov.in", "nic.in"],
            k=3  # Limit to 3 results
        )
        self.cache_dir = os.path.join(os.path.dirname(__file__), '.cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_results(self, query: str):
        """Get cached search results if they exist and are not expired"""
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"search_{cache_key}.json")
        try:
            if os.path.exists(cache_file):
                stats = os.stat(cache_file)
                if time.time() - stats.st_mtime < 3600:  # 1 hour cache
                    with open(cache_file, 'r') as f:
                        return json.load(f)
        except:
            pass
        return None

    def cache_results(self, query: str, results):
        """Cache search results"""
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"search_{cache_key}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(results, f)
        except:
            pass

    def process_results(self, results):
        """Process and filter search results"""
        result_list = results.get('results') if isinstance(results, dict) and 'results' in results else results
        urls = []
        if isinstance(result_list, list):
            for result in result_list:
                if isinstance(result, dict) and "url" in result:
                    url = result["url"]
                    # Only include .gov.in and .nic.in domains
                    if any(domain in url.lower() for domain in ['.gov.in', '.nic.in']):
                        urls.append(url)
        return list(dict.fromkeys(url for url in urls if url))

    def __call__(self, query: str):
        try:
            print(f"Searching for: {query}")
            
            # Check cache first
            cached_results = self.get_cached_results(query)
            if cached_results is not None:
                return cached_results

            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            
            for attempt in range(3):
                try:
                    # Run search with timeout
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(self.search_tool.invoke, query)
                        try:
                            results = future.result(timeout=30)  # 30-second timeout
                        except TimeoutError:
                            if attempt == 2:  # Last attempt
                                raise Exception("Search timed out after multiple attempts")
                            time.sleep(1)
                            continue
                    
                    print(f"Raw TavilySearch results: {results}")
                    urls = self.process_results(results)
                    
                    if urls:
                        final_results = [{"url": url} for url in urls[:3]]
                        self.cache_results(query, final_results)
                        return final_results
                    
                    # Try with alternative query if no results
                    if attempt == 0:
                        query = f"site:gov.in OR site:nic.in {query}"
                        continue
                    elif attempt == 1:
                        # Try more general search
                        query = " ".join(query.split()[:3]) + " site:gov.in"
                        continue
                    
                    return [{"error": "No relevant legal documents found. Would you like to provide more details about your situation?"}]
                
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        raise
                    time.sleep(1)  # Wait before retry
            
            return [{"error": "No relevant legal documents found. Would you like to provide more details about your situation?"}]
        
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return [{"error": f"I encountered an issue while searching. Could you please rephrase your question or provide more details?"}]
