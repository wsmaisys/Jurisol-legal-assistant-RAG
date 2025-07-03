from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from io import BytesIO
import functools
import hashlib
import os
import json
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def cache_result(func):
    cache_dir = os.path.join(os.path.dirname(__file__), '.cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    @functools.wraps(func)
    def wrapper(self, url: str, *args, **kwargs):
        # Create a unique cache key based on URL and function name
        cache_key = hashlib.md5(f"{func.__name__}:{url}".encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        # Check if we have a valid cache (less than 24 hours old)
        try:
            if os.path.exists(cache_file):
                stats = os.stat(cache_file)
                if time.time() - stats.st_mtime < 86400:  # 24 hours
                    with open(cache_file, 'r') as f:
                        return json.load(f)
        except:
            pass
            
        # If no cache or expired, call the original function
        result = func(self, url, *args, **kwargs)
        
        # Cache the result
        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f)
        except:
            pass
            
        return result
    return wrapper

class SummarizationTool:

    def summarize_urls(self, urls, max_workers=4):
        """
        Summarize multiple URLs in parallel for speedup.
        Returns a list of results in the same order as input URLs.
        """
        results = [None] * len(urls)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(self, url): idx for idx, url in enumerate(urls)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {"url": urls[idx], "error": str(e)}
        return results
    """
    Tool for summarizing the content of a given URL (PDF or HTML) using a provided LLM.
    """
    def __init__(self, llm):
        self.llm = llm
        self.session = requests.Session()  # Reuse connection for better performance
        self.executor = ThreadPoolExecutor(max_workers=8)  # Increased from 4

    @cache_result
    def fetch_content(self, url: str) -> dict:
        try:
            if not url.startswith(('http://', 'https://')):
                return {"url": url, "error": "Invalid URL format"}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            # Use session for connection pooling and added retry logic
            for attempt in range(3):  # Retry up to 3 times
                try:
                    response = self.session.get(url, timeout=15, headers=headers, verify=False)  # Increased timeout
                    response.raise_for_status()
                    break
                except (requests.exceptions.RequestException) as e:
                    if attempt == 2:  # Last attempt
                        raise
                    time.sleep(1)  # Wait before retry
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                pdf = PdfReader(BytesIO(response.content))
                text = "\n".join(
                    page.extract_text() for page in pdf.pages if page.extract_text()
                )
                content_type_label = "PDF"
            elif "text/html" in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
                text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
                content_type_label = "HTML"
            else:
                return {"url": url, "error": "Unsupported content type"}
            return {"url": url, "text": text[:12000], "content_type": content_type_label}
        except Exception as e:
            return {"url": url, "error": str(e)}

    def summarize(self, text: str) -> str:
        summary_prompt = f"""
        Please provide a clear and empathetic summary of this legal document. The summary should be helpful for someone seeking legal information who may be under stress.

        Focus on:
        1. Main legal principles and their practical implications
        2. Key points that might help someone understand their rights
        3. Important dates, courts, and judges involved
        4. The human aspects of the case and its impact
        5. Any protective measures or rights discussed
        6. Provide an official case citation if available

        Make the summary:
        - Relevant to common situations
        - Balanced and objective
        - Supportive in tone

        Content to summarize:
        {text}

        Remember: Many readers may be in difficult situations, so maintain a supportive tone while being accurate.
        """
        return self.llm.invoke(summary_prompt).content

    def extract_context(self, text: str) -> str:
        context_prompt = f"""
        Based on the legal document, please identify:
        1. Court Level: Supreme Court/High Court/Other
        2. Key Legal Principles: Main legal concepts discussed
        3. Relevance: How this might apply to similar cases
        4. Important Considerations: Key factors that influenced the decision

        Document:
        {text[:3000]}
        """
        return self.llm.invoke(context_prompt).content

    def __call__(self, url: str):
        content_info = self.fetch_content(url)
        if "error" in content_info:
            return content_info
        summary = self.summarize(content_info["text"])
        context = self.extract_context(content_info["text"])
        return {
            "url": url,
            "summary": summary,
            "context": context,
            "content_type": content_info["content_type"]
        }
