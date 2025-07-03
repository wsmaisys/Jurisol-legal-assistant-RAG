from fastapi import logger
import streamlit as st
import requests
import time
import json
import logging
import os
import asyncio
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Configuration - Optimized for lower latency
FASTAPI_BASE_URL = "http://localhost:8000"
MAX_RETRIES = 3
CHECK_INTERVAL = 0.1  # Faster polling
MAX_POLLING_TIME = 300  # 5 minutes max
REQUEST_TIMEOUT = 30
STATUS_TIMEOUT = 2

def setup_logging():
    """Configure comprehensive logging for the frontend"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - '
        '%(message)s - session_id: %(session_id)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # File handlers
    handlers = {
        'ui': RotatingFileHandler(
            'logs/frontend_ui.log',
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        ),
        'network': RotatingFileHandler(
            'logs/frontend_network.log',
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        ),
        'error': RotatingFileHandler(
            'logs/frontend_error.log',
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
    }
    
    for handler in handlers.values():
        handler.setFormatter(file_formatter)
    
    # Create loggers
    loggers = {
        'ui': logging.getLogger('frontend.ui'),
        'network': logging.getLogger('frontend.network'),
        'error': logging.getLogger('frontend.error')
    }
    
    # Configure loggers
    for name, logger in loggers.items():
        logger.setLevel(logging.DEBUG)
        logger.handlers = []
        logger.propagate = False
        logger.addHandler(console_handler)
        logger.addHandler(handlers[name])
        if name == 'error':
            logger.addHandler(handlers['error'])
    
    return loggers

# Initialize loggers
loggers = setup_logging()
ui_logger = loggers['ui']
network_logger = loggers['network']
error_logger = loggers['error']

# Logging context manager
class LogContext:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.old_context = {}
    
    def __enter__(self):
        # Store old context
        for logger in loggers.values():
            self.old_context[logger.name] = logger.filters
            # Add session filter
            logger.addFilter(lambda record: setattr(record, 'session_id', self.session_id) or True)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        for logger in loggers.values():
            logger.filters = self.old_context[logger.name]
        if exc_type:
            error_logger.exception(f"Error in session {self.session_id}: {str(exc_val)}")

# Initialize logging context
if 'log_context' not in st.session_state:
    st.session_state.log_context = LogContext(f"session_{int(time.time())}")


# --- Session State Management ---
def create_requests_session() -> requests.Session:
    """Create an optimized requests session with connection pooling"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = requests.adapters.Retry(
        total=MAX_RETRIES,
        backoff_factor=0.1,  # Faster retry backoff
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    # Configure connection pooling
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,  # Increased pool size
        pool_maxsize=20,
        max_retries=retry_strategy,
        pool_block=False  # Non-blocking pool
    )
    
    # Mount adapter for both HTTP and HTTPS
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "messages": [],
        "is_processing": False,
        "session_id": f"streamlit_session_{int(time.time())}",
        "last_update": time.time(),
        "error_count": 0,
        "consecutive_errors": 0,
        "processing_logs": [],
        "requests_session": create_requests_session()
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

init_session_state()


# --- Log Utility ---
def update_processing_log(new_log: str, log_level: str = "INFO"):
    timestamp = time.strftime("%H:%M:%S")
    color, icon = {
        "ERROR": ("#FF6B6B", "❌"),
        "WARNING": ("#FFD93D", "⚠️"),
        "SUCCESS": ("#6BCF7F", "✅"),
        "PROCESSING": ("#4ECDC4", "🔄")
    }.get(log_level, ("#74C0FC", "ℹ️"))
    log_entry = {
        "timestamp": timestamp,
        "message": new_log,
        "level": log_level,
        "color": color,
        "icon": icon
    }
    st.session_state.processing_logs.append(log_entry)
    if len(st.session_state.processing_logs) > 50:
        st.session_state.processing_logs.pop(0)
    st.session_state.last_update = time.time()


# --- Optimized HTTP Session Management ---
def create_requests_session() -> requests.Session:
    """Create an optimized requests session with connection pooling"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = requests.adapters.Retry(
        total=MAX_RETRIES,
        backoff_factor=0.1,  # Faster retry backoff
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    # Configure connection pooling
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,  # Increased pool size
        pool_maxsize=20,
        max_retries=retry_strategy,
        pool_block=False  # Non-blocking pool
    )
    
    # Mount adapter for both HTTP and HTTPS
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

if "http_session" not in st.session_state:
    st.session_state.http_session = create_requests_session()


st.set_page_config(
    page_title="Jurisol - AI Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- Header ---
st.title("⚖️ Jurisol")
st.header("Your Intelligent AI Legal Assistant")
st.caption("Empowering you with comprehensive insights into Indian Law")





# --- Optimized Chat Interface ---
def render_chat_interface():
    """Render the chat interface with optimized message display"""
    chat_container = st.container()
    
    with chat_container:
        # Display message history with improved formatting
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    st.markdown(
                        message["content"],
                        help="Legal assistant response"
                    )
                else:
                    st.markdown(
                        message["content"],
                        help="Your query"
                    )

render_chat_interface()


# --- Optimized API Communication ---
async def process_chat_request(prompt: str, message_placeholder) -> Optional[Dict[str, Any]]:
    """Process chat request with optimized error handling and status updates"""
    try:
        st.session_state.is_processing = True
        message_placeholder.info("Connecting to Jurisol...")
        response = st.session_state.requests_session.post(
            f"{FASTAPI_BASE_URL}/chat",
            json={"message": prompt, "session_id": st.session_state.session_id},
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            update_processing_log(f"API returned status code: {response.status_code}", "ERROR")
            return None
        try:
            initial_response = response.json()
            update_processing_log("📨 Initial response received", "SUCCESS")
        except json.JSONDecodeError:
            update_processing_log("Invalid JSON response from API", "ERROR")
            return None

        # Always poll for the real answer, regardless of initial response
        update_processing_log("🔄 Waiting for backend to process and return the answer...", "PROCESSING")
        message_placeholder.markdown("🔄 **Processing your legal query...**")
        return poll_with_ui_updates(message_placeholder)
    except requests.exceptions.Timeout:
        update_processing_log("⏰ Request timed out - checking if process is still running...", "WARNING")
        message_placeholder.markdown("⏰ **Request timed out - checking server status...**")
        return poll_with_ui_updates(message_placeholder)
    except requests.exceptions.ConnectionError:
        update_processing_log("🔌 Cannot connect to Jurisol server", "ERROR")
        return None
    except Exception as e:
        update_processing_log(f"Unexpected error: {str(e)}", "ERROR")
        return None


# --- Polling for Long-running Tasks ---
def poll_with_ui_updates(message_placeholder):
    start_time = time.time()
    poll_count = 0
    last_status = None
    processing_messages = [
        "🧠 Analyzing your legal query...",
        "📚 Searching through legal databases...",
        "⚖️ Reviewing relevant case laws...",
        "📖 Consulting legal precedents...",
        "✍️ Preparing comprehensive response...",
        "🔍 Cross-referencing legal provisions...",
        "📋 Formatting legal analysis..."
    ]
    update_processing_log("🔍 Starting status monitoring...", "PROCESSING")
    while (time.time() - start_time) < MAX_POLLING_TIME:
        poll_count += 1
        elapsed_time = time.time() - start_time
        minutes_elapsed = int(elapsed_time // 60)
        seconds_elapsed = int(elapsed_time % 60)
        if poll_count % 4 == 0:
            message_index = (poll_count // 4) % len(processing_messages)
            current_message = processing_messages[message_index]
            time_display = f"({minutes_elapsed}m {seconds_elapsed}s)" if minutes_elapsed > 0 else f"({seconds_elapsed}s)"
            message_placeholder.markdown(f"🔄 **Processing your legal query...** {time_display}\n\n*{current_message}*")
        try:
            response = st.session_state.requests_session.get(
                f"{FASTAPI_BASE_URL}/status/{st.session_state.session_id}",
                timeout=STATUS_TIMEOUT
            )
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    current_status = status_data.get("status", "unknown")
                    if current_status != last_status:
                        if current_status == "processing":
                            update_processing_log("🔄 Backend is actively processing your request...", "PROCESSING")
                        elif current_status == "analyzing":
                            update_processing_log("🧠 Analyzing legal documents and precedents...", "PROCESSING")
                        elif current_status == "searching":
                            update_processing_log("🔍 Searching legal databases...", "PROCESSING")
                        elif current_status == "generating":
                            update_processing_log("✍️ Generating comprehensive response...", "PROCESSING")
                        last_status = current_status
                    if "processing_info" in status_data:
                        backend_log = status_data["processing_info"]
                        update_processing_log(f"🖥️ Backend: {backend_log}", "INFO")
                    if status_data.get("status") == "completed":
                        response_content = status_data.get("response", "No response content")
                        update_processing_log("🎉 Processing completed successfully!", "SUCCESS")
                        return {"response": response_content}
                    elif status_data.get("status") == "failed":
                        error_msg = status_data.get("error", "Unknown error occurred")
                        update_processing_log(f"💥 Processing failed: {error_msg}", "ERROR")
                        return None
                    elif "progress" in status_data:
                        progress = status_data["progress"]
                        update_processing_log(f"📊 Progress: {progress}%", "PROCESSING")
                except json.JSONDecodeError:
                    if poll_count % 20 == 0:
                        update_processing_log("⚠️ Invalid status response format", "WARNING")
            elif response.status_code == 404:
                update_processing_log("❓ Session not found on server", "ERROR")
                return None
            else:
                if poll_count % 20 == 0:
                    update_processing_log(f"⚠️ Status check returned: {response.status_code}", "WARNING")
        except requests.exceptions.Timeout:
            if poll_count % 30 == 0:
                update_processing_log("⏱️ Status check timeout (server busy, continuing...)", "WARNING")
        except requests.exceptions.RequestException as e:
            if poll_count % 20 == 0:
                update_processing_log(f"⚠️ Status check error: {str(e)}", "WARNING")
        # Use shorter sleep for faster UI updates
        time.sleep(CHECK_INTERVAL)
    update_processing_log(f"⏰ Stopped monitoring after {MAX_POLLING_TIME//60} minutes", "WARNING")
    update_processing_log("💡 Your request might still be processing on the server", "INFO")
    return None




# --- Main Chat Processing ---
async def process_chat_request(prompt: str, message_placeholder) -> Optional[str]:
    """Process a chat request and handle responses with comprehensive logging"""
    request_id = f"req_{int(time.time()*1000)}"
    
    with st.session_state.log_context:
        try:
            # Log request initiation
            network_logger.info(f"[{request_id}] Initiating chat request")
            network_logger.debug(f"[{request_id}] Request payload: {prompt[:100]}...")
            
            # Initial request
            response = st.session_state.http_session.post(
                f"{FASTAPI_BASE_URL}/chat",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            network_logger.info(f"[{request_id}] Initial request successful")
            
            # Poll for completion
            start_time = time.time()
            poll_count = 0
            
            while time.time() - start_time < MAX_POLLING_TIME:
                poll_count += 1
                network_logger.debug(f"[{request_id}] Polling attempt {poll_count}")
                
                try:
                    status_resp = st.session_state.http_session.get(
                        f"{FASTAPI_BASE_URL}/status/{st.session_state.session_id}",
                        timeout=STATUS_TIMEOUT
                    )
                    
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        status = status_data.get("status")
                        network_logger.debug(f"[{request_id}] Status: {status}")
                        
                        if status == "completed":
                            network_logger.info(f"[{request_id}] Request completed successfully")
                            return status_data.get("response")
                        elif status == "failed":
                            error_msg = status_data.get("error", "Processing failed")
                            error_logger.error(f"[{request_id}] Processing failed: {error_msg}")
                            raise Exception(error_msg)
                        
                        # Update UI with status
                        elapsed = int(time.time() - start_time)
                        ui_logger.debug(f"[{request_id}] Updating UI with status: {status}")
                        message_placeholder.info(
                            f"Processing your query... ({elapsed}s)\n\n"
                            f"Status: {status}"
                        )
                    else:
                        network_logger.warning(
                            f"[{request_id}] Unexpected status code: {status_resp.status_code}"
                        )
                
                except requests.exceptions.Timeout:
                    network_logger.warning(f"[{request_id}] Status check timeout")
                except requests.exceptions.RequestException as e:
                    network_logger.error(f"[{request_id}] Status check failed: {str(e)}")
                
                time.sleep(CHECK_INTERVAL)
            
            error_logger.error(f"[{request_id}] Request timed out after {MAX_POLLING_TIME}s")
            raise TimeoutError("Request processing timed out")
            
        except Exception as e:
            error_logger.exception(f"[{request_id}] Error processing request:")
            return None

# --- Chat Interface with Enhanced Logging ---
async def handle_chat_input():
    if prompt := st.chat_input("Ask about Indian law..."):
        with st.session_state.log_context:
            interaction_id = f"chat_{int(time.time()*1000)}"
        ui_logger.info(f"[{interaction_id}] New user input received")
        
        try:
            # Add user message
            ui_logger.debug(f"[{interaction_id}] Adding user message to session")
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Process assistant response
            ui_logger.info(f"[{interaction_id}] Processing assistant response")
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.info("Processing your query...")
                
                ui_logger.debug(f"[{interaction_id}] Initiating chat request")
                response = await process_chat_request(prompt, message_placeholder)
                
                if response:
                    ui_logger.info(f"[{interaction_id}] Received valid response")
                    message_placeholder.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    st.session_state.consecutive_errors = 0
                    ui_logger.info(f"[{interaction_id}] Response displayed successfully")
                else:
                    error_logger.warning(f"[{interaction_id}] Failed to get valid response")
                    error_message = ("I apologize, but I couldn't process your request at the moment. "
                                   "Please try again or rephrase your question.")
                    message_placeholder.error(error_message)
                    st.session_state.consecutive_errors += 1
                    
                    # Reset session if too many consecutive errors
                    if st.session_state.consecutive_errors >= 3:
                        ui_logger.warning(f"[{interaction_id}] Multiple errors detected, refreshing session")
                        st.warning("Multiple errors detected. Refreshing session...")
                        st.session_state.session_id = f"streamlit_session_{int(time.time())}"
                        st.session_state.consecutive_errors = 0
                
                st.session_state.is_processing = False
            
            ui_logger.info(f"[{interaction_id}] Chat interaction completed")
            
        except Exception as e:
            error_logger.exception(f"[{interaction_id}] Unexpected error in chat interface:")
            st.error("An unexpected error occurred. Please try again.")
            
# Run the async chat handler
asyncio.run(handle_chat_input())


# --- Footer ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<div style='text-align: center;'>Created by Waseem M Ansari with ❤️</div>", unsafe_allow_html=True)


# --- Sidebar: Connection Status & Session Info ---
with st.sidebar:
    st.markdown("---")
    st.markdown("**🔗 Connection Status**")
    try:
        response = st.session_state.requests_session.get(f"{FASTAPI_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            st.success("🟢 Jurisol Backend Online")
            try:
                health_data = response.json()
                if "uptime" in health_data:
                    st.caption(f"⏱️ Uptime: {health_data['uptime']}")
                if "active_sessions" in health_data:
                    st.caption(f"👥 Active sessions: {health_data['active_sessions']}")
            except Exception:
                pass
        else:
            st.warning("🟡 Server responded with issues")
    except requests.exceptions.Timeout:
        st.error("🔴 Server timeout (may be busy)")
    except Exception:
        st.error("🔴 Cannot connect to backend")
    st.markdown("**📋 Session Info**")
    st.caption(f"ID: {st.session_state.session_id[-8:]}")
    if st.session_state.messages:
        st.caption(f"Messages: {len(st.session_state.messages)}")
    if st.session_state.processing_logs:
        st.caption(f"Log entries: {len(st.session_state.processing_logs)}")