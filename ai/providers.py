"""
AI provider management with automatic failover
Groq → HuggingFace → OpenRouter → Mistral → Cycle back
"""

import logging
from huggingface_hub import InferenceClient
from config.api_keys import (
     GROQ_KEYS, HUGGINGFACE_KEYS,
    OPENROUTER_KEYS, MISTRAL_KEYS
)

logger = logging.getLogger(__name__)

# Track current provider
current_provider = "groq"
current_key_indices = {
    'groq': 0,
    'huggingface': 0,
    'openrouter': 0,
    'mistral': 0
}

# Global Client Instances
groq_client_instance = None
huggingface_client_instance = None
openrouter_client_instance = None
mistral_client_instance = None

def setup_ai_providers(startup_ui=None):
    global groq_client_instance, huggingface_client_instance
    
    if startup_ui:
        startup_ui.update_status("Setting up AI...")
    
    # Setup Groq (Primary)
    client = setup_groq_model()
    
    if client is None:
        logger.warning("⚠️ Groq initialization failed. Trying HuggingFace...")
        
        # Try HuggingFace immediately
        huggingface_client_instance = setup_huggingface_client()
        if huggingface_client_instance:
            logger.info("✅ Using HuggingFace as primary provider")
            global current_provider
            current_provider = "huggingface"
            return huggingface_client_instance
        else:
            logger.error("❌ All providers failed!")
            return None
    
    # Pre-initialize backup providers in background
    import threading
    def init_backups():
        global huggingface_client_instance
        if startup_ui:
            startup_ui.update_status("Pre-loading backup AI providers...")
        
        if huggingface_client_instance is None:
            setup_huggingface_client()
        setup_openrouter_client()
        setup_mistral_client()
        
    threading.Thread(target=init_backups, daemon=True).start()
    
    return client


# ============= GROQ =============

def setup_groq_model():
    """Initialize Groq with first available key"""
    global groq_client_instance
    from groq import Groq
    
    for i, entry in enumerate(GROQ_KEYS):
        try:
            client = Groq(api_key=entry["key"])
            
            # Test the key
            client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            logger.info(f"✅ Using {entry['name']} key")
            current_key_indices['groq'] = i
            groq_client_instance = client  # Store globally
            return client
        except Exception as e:
            logger.error(f"❌ Failed with {entry['name']}: {e}")
    
    logger.error("❌ All Groq API keys failed!")
    groq_client_instance = None
    return None

def switch_to_next_groq_key():
    """Switch to next available Groq API key"""
    global groq_client_instance
    from groq import Groq
    
    for _ in range(len(GROQ_KEYS) - 1):
        current_key_indices['groq'] = (current_key_indices['groq'] + 1) % len(GROQ_KEYS)
        entry = GROQ_KEYS[current_key_indices['groq']]
        
        try:
            client = Groq(api_key=entry["key"])
            
            # Test the key
            client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            logger.info(f"🔄 Switched to {entry['name']} key")
            groq_client_instance = client
            return client
        except Exception as e:
            logger.error(f"❌ {entry['name']} key also failed: {e}")
    
    logger.error("❌ All Groq backup keys exhausted!")
    return None

def _call_groq(prompt, client, system_prompt=None):
    """Internal Groq API caller with system prompt support"""
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0,
            max_tokens=8192
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq call error: {e}")
        raise

# ============= HUGGINGFACE =============

def setup_huggingface_client():
    """Initialize HuggingFace with first available key"""
    global huggingface_client_instance
    for i, entry in enumerate(HUGGINGFACE_KEYS):
        if entry["key"]:
            logger.info(f"✅ Using {entry['name']} key")
            current_key_indices['huggingface'] = i
            huggingface_client_instance = entry["key"] # Just the key string for HF
            return entry["key"]
    
    logger.error("❌ All HuggingFace API keys failed!")
    return None

def switch_to_next_hf_key():
    """Switch to next available HuggingFace API key"""
    global huggingface_client_instance
    for _ in range(len(HUGGINGFACE_KEYS) - 1):
        current_key_indices['huggingface'] = (current_key_indices['huggingface'] + 1) % len(HUGGINGFACE_KEYS)
        entry = HUGGINGFACE_KEYS[current_key_indices['huggingface']]
        
        if entry["key"]:
            logger.info(f"🔄 Switched to {entry['name']} key")
            huggingface_client_instance = entry["key"]
            return entry["key"]
    
    logger.error("❌ All HuggingFace backup keys exhausted!")
    return None


def _call_huggingface(prompt, key):
    """Internal HuggingFace API caller"""
    try:
        client = InferenceClient(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            token=key
        )
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=8192
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"HuggingFace error: {e}")
        raise

# ============= OPENROUTER =============

def setup_openrouter_client():
    """Initialize OpenRouter with first available key"""
    global openrouter_client_instance
    for i, entry in enumerate(OPENROUTER_KEYS):
        if entry["key"]:
            logger.info(f"✅ Using {entry['name']} key")
            current_key_indices['openrouter'] = i
            openrouter_client_instance = entry["key"]
            return entry["key"]
    
    logger.error("❌ All OpenRouter API keys failed!")
    return None

def switch_to_next_or_key():
    """Switch to next available OpenRouter API key"""
    global openrouter_client_instance
    for _ in range(len(OPENROUTER_KEYS) - 1):
        current_key_indices['openrouter'] = (current_key_indices['openrouter'] + 1) % len(OPENROUTER_KEYS)
        entry = OPENROUTER_KEYS[current_key_indices['openrouter']]
        
        if entry["key"]:
            logger.info(f"🔄 Switched to {entry['name']} key")
            openrouter_client_instance = entry["key"]
            return entry["key"]
    
    logger.error("❌ All OpenRouter backup keys exhausted!")
    return None

def _call_openrouter(prompt, key):
    """Internal OpenRouter API caller"""
    try:
        import requests
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"    
        }
        
        data = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 8192
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        raise

# ============= MISTRAL =============

def setup_mistral_client():
    """Initialize Mistral with first available key"""
    global mistral_client_instance
    for i, entry in enumerate(MISTRAL_KEYS):
        if entry["key"]:
            logger.info(f"✅ Using {entry['name']} key")
            current_key_indices['mistral'] = i
            mistral_client_instance = entry["key"]
            return entry["key"]
    
    logger.error("❌ All Mistral API keys failed!")
    return None

def switch_to_next_mistral_key():
    """Switch to next available Mistral API key"""
    global mistral_client_instance
    for _ in range(len(MISTRAL_KEYS) - 1):
        current_key_indices['mistral'] = (current_key_indices['mistral'] + 1) % len(MISTRAL_KEYS)
        entry = MISTRAL_KEYS[current_key_indices['mistral']]
        
        if entry["key"]:
            logger.info(f"🔄 Switched to {entry['name']} key")
            mistral_client_instance = entry["key"]
            return entry["key"]
    
    logger.error("❌ All Mistral backup keys exhausted!")
    return None

def _call_mistral(prompt, key):
    """Internal Mistral API caller"""
    try:
        import requests
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "codestral-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 8192
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        logger.error(f"Mistral error: {e}")
        raise

# ============= OLLAMA (LOCAL FALLBACK) =============

def _call_ollama(prompt):
    """Internal Local Ollama API caller"""
    try:
        import requests
        
        url = "http://localhost:11434/api/chat"
        data = {
            "model": "qwen2.5-coder:3b", # Change to "qwen2.5-coder:3b" or "qwen2.5-coder:7b"
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 1024 # Prevent it from rambling
            }
        }
        
        # Fast 2-second timeout to connect, 120 seconds to generate the code
        response = requests.post(url, json=data, timeout=(2.0, 120.0))
        response.raise_for_status()
        
        result = response.json()
        return result["message"]["content"].strip()
    
    except Exception as e:
        logger.error(f"Local Ollama error: {e}")
        raise
    
# ============= MAIN CALLER =============

def _is_rate_limit_error(error_msg):
    """Check if error is rate limit related"""
    error_lower = error_msg.lower()
    return any(keyword in error_lower for keyword in[
        'rate limit', 'too many requests', '429', 'quota exceeded',
        'resource_exhausted', 'quota', 'limit exceeded'
    ])

def _show_provider_toast(provider_name):
    """Show toast notification when switching providers"""
    toast_msg = f"🔄 Switched to {provider_name} API"
    logger.info(toast_msg)
    
    try:
        if hasattr(call_ai_model, '_gui_handler') and call_ai_model._gui_handler:
            call_ai_model._gui_handler.show_terminal_output(toast_msg, color="cyan")
    except:
        pass

def _check_internet_fast():
    """Lightning-fast check to see if we have internet access"""
    import socket
    try:
        # Connect to Cloudflare's fast DNS server
        socket.create_connection(("1.1.1.1", 53), timeout=1.0)
        return True
    except OSError:
        pass
    return False

def call_ai_model(prompt, client):
    """
    Universal AI caller with Smart Offline Fallback
    """
    global current_provider
    global groq_client_instance, huggingface_client_instance
    global openrouter_client_instance, mistral_client_instance
    
    # Initialize globals if they are None
    if current_provider == "groq" and groq_client_instance is None and client:
        groq_client_instance = client

    # SMART OFFLINE ROUTING
    has_internet = _check_internet_fast()
    if not has_internet:
        if current_provider != "ollama":
            current_provider = "ollama"
            _show_provider_toast("Local Offline Model (Ollama)")
            
        try:
            return _call_ollama(prompt)
        except Exception as e:
            raise Exception(f"❌ Offline and Local Model failed: {e}")

    max_cycles = 2
    attempt = 0
    
    # ADDED 'ollama' to the end of the provider chain
    providers =['groq', 'huggingface', 'openrouter', 'mistral', 'ollama']
    
    if current_provider not in providers:
        current_provider = "groq"
    
    provider_index = providers.index(current_provider)
    
    while attempt < max_cycles:
        try:
            # === GROQ ===
            if current_provider == "groq":
                try:
                    if not groq_client_instance:
                        groq_client_instance = setup_groq_model()
                        if not groq_client_instance: raise Exception("Groq init failed")
                        
                    return _call_groq(prompt, groq_client_instance)
                except Exception as e:
                    logger.error(f"❌ Groq error: {type(e).__name__}: {e}")
                    if _is_rate_limit_error(str(e)) and switch_to_next_groq_key():
                        try: return _call_groq(prompt, groq_client_instance)
                        except: pass
                    logger.warning("🔄 Groq exhausted! Switching to HuggingFace...")
                    current_provider = "huggingface"
                    _show_provider_toast("HuggingFace")
                    continue
            
            # === HUGGINGFACE ===
            elif current_provider == "huggingface":
                try:
                    if not huggingface_client_instance:
                        setup_huggingface_client()
                    if huggingface_client_instance:
                        return _call_huggingface(prompt, huggingface_client_instance)
                    else: raise Exception("No HF key available")
                except Exception as e:
                    logger.error(f"❌ HuggingFace error: {type(e).__name__}: {e}")
                    if _is_rate_limit_error(str(e)) and switch_to_next_hf_key():
                        try: return _call_huggingface(prompt, huggingface_client_instance)
                        except: pass
                    logger.warning("🔄 HuggingFace exhausted! Switching to OpenRouter...")
                    current_provider = "openrouter"
                    _show_provider_toast("OpenRouter")
                    continue
            
            # === OPENROUTER ===
            elif current_provider == "openrouter":
                try:
                    if not openrouter_client_instance:
                        setup_openrouter_client()
                    if openrouter_client_instance:
                        return _call_openrouter(prompt, openrouter_client_instance)
                    else: raise Exception("No OpenRouter key available")
                except Exception as e:
                    logger.error(f"❌ OpenRouter error: {type(e).__name__}: {e}")
                    if _is_rate_limit_error(str(e)) and switch_to_next_or_key():
                        try: return _call_openrouter(prompt, openrouter_client_instance)
                        except: pass
                    logger.warning("🔄 OpenRouter exhausted! Switching to Mistral...")
                    current_provider = "mistral"
                    _show_provider_toast("Mistral")
                    continue
            
            # === MISTRAL ===
            elif current_provider == "mistral":
                try:
                    if not mistral_client_instance:
                        setup_mistral_client()
                    if mistral_client_instance:
                        return _call_mistral(prompt, mistral_client_instance)
                    else: raise Exception("No Mistral key available")
                except Exception as e:
                    logger.error(f"❌ Mistral error: {type(e).__name__}: {e}")
                    if _is_rate_limit_error(str(e)) and switch_to_next_mistral_key():
                        try: return _call_mistral(prompt, mistral_client_instance)
                        except: pass
                    logger.warning("🔄 Mistral exhausted! Switching to Local Ollama...")
                    current_provider = "ollama"
                    _show_provider_toast("Local Model (Ollama)")
                    continue
            
            # === OLLAMA (LOCAL FALLBACK) ===
            elif current_provider == "ollama":
                try:
                    return _call_ollama(prompt)
                except Exception as e:
                    logger.error(f"❌ Local Ollama error: {type(e).__name__}: {e}")
                    logger.warning("🔄 Local Model failed! Cycling back to Groq...")
                    current_provider = "groq"
                    _show_provider_toast("Groq (retry)")
                    attempt += 1
                    continue
        
        except Exception as e:
            logger.error(f"❌ {current_provider} general error: {e}")
            provider_index = (provider_index + 1) % len(providers)
            current_provider = providers[provider_index]
            attempt += 1
            if attempt >= max_cycles:
                raise Exception(f"❌ All API providers (including Local) exhausted!")
    
    raise Exception("❌ Failed to get response from any AI provider!")