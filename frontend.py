import streamlit as st
st.set_page_config(
    page_title="Jurisol - AI Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(
    """
    <p style='text-align: center; font-size: 0.95em; margin-bottom: 0.5em;'>
        <i>For best results, use specific queries and avoid ambiguous or vague searches.</i>
    </p>
    """,
    unsafe_allow_html=True
)
import requests
import time
import json
import logging
import os
from typing import Optional
from logging.handlers import RotatingFileHandler
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
FASTAPI_BASE_URL = "http://localhost:8000"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
BACKEND_CONFIG = {
    "retry": {
        "total": MAX_RETRIES,
        "backoff_factor": 0.3,
        "status_forcelist": [500, 502, 503, 504]
    },
    "connection": {
        "pool_connections": 10,
        "pool_maxsize": 10
    },
    "timeouts": {
        "connect": 5,
        "read": REQUEST_TIMEOUT
    }
}

def setup_logging():
    """Configure comprehensive logging for the frontend"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
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
    
    loggers = {
        'ui': logging.getLogger('frontend.ui'),
        'network': logging.getLogger('frontend.network'),
        'error': logging.getLogger('frontend.error')
    }
    
    for name, logger in loggers.items():
        logger.setLevel(logging.DEBUG)
        logger.handlers = []
        logger.propagate = False
        logger.addHandler(console_handler)
        logger.addHandler(handlers[name])
    
    return loggers

loggers = setup_logging()
ui_logger = loggers['ui']
network_logger = loggers['network']
error_logger = loggers['error']

def create_requests_session() -> requests.Session:
    """Create an optimized requests session with connection pooling"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=BACKEND_CONFIG["retry"]["total"],
        backoff_factor=BACKEND_CONFIG["retry"]["backoff_factor"],
        status_forcelist=BACKEND_CONFIG["retry"]["status_forcelist"],
        allowed_methods=["HEAD", "GET", "POST"]
    )
    
    adapter = HTTPAdapter(
        pool_connections=BACKEND_CONFIG["connection"]["pool_connections"],
        pool_maxsize=BACKEND_CONFIG["connection"]["pool_maxsize"],
        max_retries=retry_strategy
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    return session



def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "messages": [],  # Chat history
        "is_processing": False,  # Request processing status
        "error_count": 0,  # Total error count
        "processing_logs": [],  # Processing logs for debugging
        "requests_session": create_requests_session(),  # Persistent HTTP session
        "backend_available": True,  # Backend health status
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def update_processing_log(message: str, level: str = "INFO"):
    """Update the processing log with a new entry"""
    timestamp = time.strftime("%H:%M:%S")
    colors = {
        "ERROR": "#FF6B6B",
        "WARNING": "#FFD93D", 
        "SUCCESS": "#6BCF7F",
        "PROCESSING": "#4ECDC4",
        "INFO": "#74C0FC"
    }
    icons = {
        "ERROR": "❌",
        "WARNING": "⚠️",
        "SUCCESS": "✅", 
        "PROCESSING": "🔄",
        "INFO": "ℹ️"
    }
    
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        "level": level,
        "color": colors.get(level, "#74C0FC"),
        "icon": icons.get(level, "ℹ️")
    }
    
    st.session_state.processing_logs.append(log_entry)
    if len(st.session_state.processing_logs) > 50:
        st.session_state.processing_logs.pop(0)
    
    # Also log to file
    logger_map = {
        "ERROR": error_logger.error,
        "WARNING": ui_logger.warning,
        "SUCCESS": ui_logger.info,
        "PROCESSING": ui_logger.info,
        "INFO": ui_logger.info
    }
    logger_map.get(level, ui_logger.info)(message)

def check_backend_health():
    """Check if the backend is available"""
    try:
        response = st.session_state.requests_session.get(
            f"{FASTAPI_BASE_URL}/health", 
            timeout=3
        )
        if response.status_code == 200:
            st.session_state.backend_available = True
            try:
                return response.json()
            except:
                return {"status": "healthy"}
        else:
            st.session_state.backend_available = False
            return None
    except:
        st.session_state.backend_available = False
        return None



def show_waiting_message(message_placeholder):
    """Show a waiting message with information about the AI processing"""
    message_placeholder.markdown("""
        🔄 **Processing your request...**
        
        > Note: The AI Agent is working, please keep patience. It is searching databases, doing online searches and summarization contents.
        🤔 Formulating response
    """)

def process_chat_request(prompt: str, message_placeholder) -> Optional[str]:
    """Process a chat request with improved error handling"""
    try:
        st.session_state.is_processing = True
        history = st.session_state.messages[-4:] if st.session_state.messages else []
        
        # Show waiting message with AI processing information
        show_waiting_message(message_placeholder)
        
        # Prepare request data
        request_data = {
            "message": prompt,
            "history": history
        }
        
        # Make request to chat endpoint
        response = st.session_state.requests_session.post(
            f"{FASTAPI_BASE_URL}/chat",
            json=request_data,
            timeout=BACKEND_CONFIG["timeouts"]["read"]
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                if "response" in result:
                    update_processing_log("✅ Response received successfully", "SUCCESS")
                    return result["response"]
            except json.JSONDecodeError:
                update_processing_log("Invalid JSON response from API", "ERROR")
        
        update_processing_log(f"API error: {response.status_code}", "ERROR")
        return None
            
    except requests.exceptions.Timeout:
        update_processing_log("⏰ Request timed out", "WARNING")
        return None
    except requests.exceptions.ConnectionError:
        update_processing_log("🔌 Cannot connect to Jurisol server", "ERROR")
        st.session_state.backend_available = False
        return None
    except Exception as e:
        update_processing_log(f"Unexpected error: {str(e)}", "ERROR")
        error_logger.exception("Error in process_chat_request")
        return None
    finally:
        st.session_state.is_processing = False

# Streamlit Configuration

# Initialize session state
init_session_state()

# Header with centered content
st.markdown("<h1 style='text-align: center;'>⚖️ Jurisol</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;'>Your Intelligent AI Legal Assistant</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-style: italic;'>Empowering you with comprehensive insights into Indian Law</p>", unsafe_allow_html=True)

# Check backend availability
if not st.session_state.backend_available:
    health_data = check_backend_health()
    if not health_data:
        st.error("🔴 **Backend server is not available**")
        st.info("Please ensure the FastAPI backend is running on http://localhost:8000")
        st.stop()

# Chat Interface
def render_chat_interface():
    """Render the chat interface"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

render_chat_interface()

# Handle chat input
if prompt := st.chat_input("Ask about Indian law...", disabled=st.session_state.is_processing):
    ui_logger.info(f"New user input: {prompt[:100]}...")
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Process the request
            response = process_chat_request(prompt, message_placeholder)
            
            if response:
                # Display successful response
                message_placeholder.markdown(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                st.session_state.error_count = 0
                ui_logger.info("Response displayed successfully")
            else:
                # Handle failed response
                error_message = (
                    "⚠️ I apologize, but I couldn't process your request. "
                    "Please try rephrasing your query or try again in a moment."
                )
                message_placeholder.error(error_message)
                st.session_state.error_count += 1
                
                if st.session_state.error_count >= 3:
                    st.warning("🔄 Multiple errors detected - Refreshing session...")
                    st.session_state.messages = []
                    st.session_state.error_count = 0
                    st.session_state.requests_session = create_requests_session()
                    st.rerun()
        
        except Exception as e:
            error_logger.exception("Chat processing error")
            message_placeholder.error("💥 An unexpected error occurred. Please try again.")
        
        finally:
            st.session_state.is_processing = False

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### � System Status")
    
    # Backend health check
    health_data = check_backend_health()
    if health_data:
        st.success("✅ System Online")
    else:
        st.error("❌ System Offline")
        st.info("Please ensure the backend server is running.")
        st.stop()
    
    # Session info
    st.markdown("### 📊 Session Stats")
    if st.session_state.messages:
        st.caption(f"Messages: {len(st.session_state.messages)}")
    
    # Show recent logs
    if st.session_state.processing_logs:
        st.markdown("### 📝 Recent Activity")
        for log in st.session_state.processing_logs[-3:]:
            st.caption(f"{log['icon']} {log['message']}")
    
    # Control buttons
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh"):
            st.session_state.messages = []
            st.session_state.processing_logs = []
            st.session_state.requests_session = create_requests_session()
            st.rerun()
    with col2:
        if st.button("🗑️ Clear"):
            st.session_state.messages = []
            st.session_state.processing_logs = []
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center;'>
    <p>Created by Waseem M Ansari and CoPilot with ❤️</p>
    <p style='font-size: 0.8em; color: #888;'>
        AI-powered legal research assistant for Indian law
    </p>
</div>
""", unsafe_allow_html=True)