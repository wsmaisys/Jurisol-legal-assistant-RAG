from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3
import logging
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
                    response = self.session.get(url, timeout=20, headers=headers, verify=False)
                    response.raise_for_status()
                    break
                except (requests.exceptions.RequestException) as e:
                    if attempt == 2:  # Last attempt
                        return {"url": url, "error": f"Request failed after retries: {str(e)}"}
                    time.sleep(1)
            content_type = response.headers.get("Content-Type", "").lower()
            # --- PDF Handling ---
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                try:
                    pdf = PdfReader(BytesIO(response.content))
                    text_chunks = []
                    for i, page in enumerate(pdf.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_chunks.append(page_text)
                        except Exception as pe:
                            logging.warning(f"PDF page {i} extraction failed: {pe}")
                    text = "\n".join(text_chunks)
                    if not text.strip():
                        return {"url": url, "error": "PDF contains no extractable text (may be scanned or image-based)."}
                    content_type_label = "PDF"
                except Exception as pdf_e:
                    return {"url": url, "error": f"PDF extraction failed: {str(pdf_e)}"}
            # --- HTML Handling ---
            elif "text/html" in content_type:
                try:
                    soup = BeautifulSoup(response.text, "html.parser")
                    # Remove unwanted tags
                    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside", "form", "svg", "iframe"]):
                        tag.decompose()
                    # Try to extract main content heuristically
                    main = soup.find('main')
                    article = soup.find('article')
                    if article and len(article.get_text(strip=True)) > 200:
                        text = article.get_text(separator="\n", strip=True)
                    elif main and len(main.get_text(strip=True)) > 200:
                        text = main.get_text(separator="\n", strip=True)
                    else:
                        # Fallback: get all paragraphs
                        paragraphs = soup.find_all('p')
                        text = '\n'.join(p.get_text(separator=' ', strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
                        if not text.strip():
                            # Fallback: get all text
                            text = soup.get_text(separator="\n")
                    # Clean up excessive whitespace
                    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
                    if not text.strip():
                        return {"url": url, "error": "No extractable text found in HTML."}
                    content_type_label = "HTML"
                except Exception as html_e:
                    return {"url": url, "error": f"HTML extraction failed: {str(html_e)}"}
            else:
                return {"url": url, "error": f"Unsupported content type: {content_type}"}
            # Truncate to 12000 chars for LLM
            return {"url": url, "text": text[:12000], "content_type": content_type_label}
        except Exception as e:
            logging.exception(f"[SummarizationTool] fetch_content error for {url}")
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

    def __call__(self, text: str) -> str:
        """Process text input and return a summary"""
        try:
            # Check if this is a text that starts with "Summarize:" or "Summarize this paragraph:"
            if ":" in text:
                prefix, content = text.split(":", 1)
                if prefix.lower().strip() in ["summarize", "summarize this paragraph"]:
                    text = content.strip()

            # If it's a URL, fetch the content
            if text.strip().startswith(('http://', 'https://')):
                content_info = self.fetch_content(text.strip())
                if "error" in content_info:
                    return f"Error: Unable to process URL - {content_info['error']}"
                if "text" in content_info:
                    text = content_info["text"]
            
            # Generate the summary using the LLM
            return self.summarize(text)
        except Exception as e:
            logging.exception("Error in summarization")
            return f"Error: Unable to generate summary - {str(e)}"
