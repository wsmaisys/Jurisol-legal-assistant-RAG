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
        """Process and filter search results, fetch content from URLs."""
        import requests
        from bs4 import BeautifulSoup
        result_list = results.get('results') if isinstance(results, dict) and 'results' in results else results
        processed = []
        if isinstance(result_list, list):
            for result in result_list:
                if isinstance(result, dict) and "url" in result:
                    url = result["url"]
                    # Only include .gov.in and .nic.in domains
                    if any(domain in url.lower() for domain in ['.gov.in', '.nic.in']):
                        # Try to fetch and extract main content
                        try:
                            resp = requests.get(url, timeout=10)
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            # Try to extract main content heuristically
                            article = soup.find('article')
                            if article:
                                text = article.get_text(separator=' ', strip=True)
                            else:
                                # Fallback: get all paragraphs
                                paragraphs = soup.find_all('p')
                                text = ' '.join(p.get_text(separator=' ', strip=True) for p in paragraphs)
                            # Truncate if too long
                            if len(text) > 4000:
                                text = text[:4000] + '... [truncated]'
                        except Exception as e:
                            text = f"[Could not fetch content: {e}]"
                        processed.append({"url": url, "content": text})
        return processed

    def __call__(self, query: str):
        import logging
        try:
            logging.info(f"[OnlineSearch] Searching for: {query}")
            # Check cache first
            cached_results = self.get_cached_results(query)
            if cached_results is not None:
                logging.info(f"[OnlineSearch] Returning cached results for: {query}")
                return cached_results
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            for attempt in range(3):
                try:
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(self.search_tool.invoke, query)
                        try:
                            results = future.result(timeout=30)
                        except TimeoutError:
                            logging.warning(f"[OnlineSearch] Timeout on attempt {attempt+1} for query: {query}")
                            if attempt == 2:
                                raise Exception("Search timed out after multiple attempts")
                            time.sleep(1)
                            continue
                    logging.info(f"[OnlineSearch] Raw TavilySearch results: {results}")
                    urls = self.process_results(results)
                    logging.info(f"[OnlineSearch] Processed URLs: {urls}")
                    if urls:
                        final_results = [{"url": url} for url in urls[:3]]
                        self.cache_results(query, final_results)
                        logging.info(f"[OnlineSearch] Returning final results for: {query}")
                        return final_results
                    if attempt == 0:
                        query = f"site:gov.in OR site:nic.in {query}"
                        continue
                    elif attempt == 1:
                        query = " ".join(query.split()[:3]) + " site:gov.in"
                        continue
                    logging.warning(f"[OnlineSearch] No relevant legal documents found for query: {query}")
                    return [{"error": "No relevant legal documents found. Would you like to provide more details about your situation?"}]
                except Exception as e:
                    logging.exception(f"[OnlineSearch] Exception on attempt {attempt+1} for query: {query}")
                    if attempt == 2:
                        raise
                    time.sleep(1)
            logging.warning(f"[OnlineSearch] No relevant legal documents found after retries for query: {query}")
            return [{"error": "No relevant legal documents found. Would you like to provide more details about your situation?"}]
        except Exception as e:
            logging.exception(f"[OnlineSearch] Search failed for query: {query}")
            return [{"error": f"I encountered an issue while searching. Could you please rephrase your question or provide more details?"}]
