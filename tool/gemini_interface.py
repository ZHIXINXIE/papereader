import os
import time
import json
from pathlib import Path
from typing import List, Optional, Any, Dict, Union
import datetime
from google import genai
from google.genai import types
from google.genai.types import CachedContent

class Gemini_interface:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = "gemini-3-flash-preview"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set in GEMINI_API_KEY environment variable.")
        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})
        # Fixed model names: gemini-3-pro-preview, gemini-3-flash-preview
        self.model_name = model_name 
    
    def _create_pdf_cache(self, file_path: str, ttl: str = "600s", system_instruction: Optional[str] = None) -> CachedContent:
        """Creates a cache entry for a PDF file with a specified TTL."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported for caching.")
        file_list = self.client.files.list()
        for file in file_list:
            if file.display_name == str(Path(file_path).absolute()):
                uploaded_file = file
                break
        else:
            uploaded_file = self.client.files.upload(file=path, config={"mime_type": "application/pdf", "display_name": str(Path(file_path).absolute())})
        cache = self.client.caches.create(
            model=self.model_name,
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
                contents=[uploaded_file],
                display_name=str(path),
                ttl=ttl,
            )
        )
        return cache

    def _calculate_cost(self, usage_metadata: Any, model_name: str, is_cache_creation: bool = False) -> float:
        """
        Calculates cost based on token usage and model pricing.
        Includes Context Caching pricing.
        
        - Cached Input (Cache Hit) = Sum of 'IMAGE' tokens in `prompt_tokens_details`.
        - Non-Cached Input (Query) = Sum of 'TEXT' tokens in `prompt_tokens_details`.
        - Storage Cost = Ignored.
        
        Args:
            usage_metadata: The usage metadata from the response.
            model_name: The model name.
            is_cache_creation: If True, treats the cached tokens (IMAGE) as Standard Input (creation cost),
                               and ignores the Cache Hit cost for this turn.
        """
        if not usage_metadata:
            return 0.0
            
        cached_count = 0
        non_cached_prompt_count = 0
        
        # Parse prompt_tokens_details to distinguish Cache (IMAGE) vs Query (TEXT)
        if hasattr(usage_metadata, 'prompt_tokens_details'):
            for detail in usage_metadata.prompt_tokens_details:
                if detail.modality == 'IMAGE':
                    # User instruction: IMAGE tokens represent the cached content
                    cached_count += detail.token_count
                elif detail.modality == 'TEXT':
                    # TEXT tokens represent the user query/input
                    non_cached_prompt_count += detail.token_count
        else:
            # Fallback if details are missing
            raise ValueError("prompt_tokens_details missing in usage_metadata.")
 
        output_count = usage_metadata.candidates_token_count 
        
        cost = 0.0
        
        # Pricing Logic
        if "gemini-3-pro-preview" in model_name:
            # Pro Pricing
            
            # 1. Non-Cached Input (TEXT) -> Always Standard Price
            if non_cached_prompt_count <= 200000:
                cost += (non_cached_prompt_count / 1_000_000) * 2.00
            else:
                cost += (non_cached_prompt_count / 1_000_000) * 4.00
            
            # 2. Cached Input (IMAGE from Prompt Details)
            if cached_count > 0:
                if is_cache_creation:
                    # Treat as Standard Input (Creation Cost)
                    if cached_count <= 200000:
                        cost += (cached_count / 1_000_000) * 2.00
                    else:
                        cost += (cached_count / 1_000_000) * 4.00
                else:
                    # Treat as Cache Hit
                    if cached_count <= 200000:
                        cost += (cached_count / 1_000_000) * 0.20
                    else:
                        cost += (cached_count / 1_000_000) * 0.40
                    
                # 3. Storage Cost -> Ignored

            # 4. Output
            if output_count is not None:
                if output_count <= 200000:
                    cost += (output_count / 1_000_000) * 12.00
                else:
                    cost += (output_count / 1_000_000) * 18.00
                
        elif "gemini-3-flash-preview" in model_name:
            # Flash Pricing
            
            # 1. Cached Input (IMAGE from Prompt Details)
            if cached_count > 0:
                if is_cache_creation:
                    # Treat as Standard Input (Creation Cost)
                    # Note: Flash Standard Input is $0.50
                    cost += (cached_count / 1_000_000) * 0.50
                else:
                    # Treat as Cache Hit
                    cost += (cached_count / 1_000_000) * 0.05
                
                # 2. Storage Cost -> Ignored
            
            # 3. Non-Cached Input (TEXT only) -> Standard Price
            cost += (non_cached_prompt_count / 1_000_000) * 0.50
            
            # 4. Output
            if output_count is not None:
                cost += (output_count / 1_000_000) * 3.00
            
        return cost

    def chat(self, pdf: Union[str, List[str], None], text: str, max_tokens: int = 4096, history: Dict = None) -> tuple[str, Dict, float, float]:
        """
        Interacts with the Gemini model, managing PDF caching and chat history.
        
        Args:
            pdf: Path to a PDF file to cache and use as context. 
                 Only allowed if no cache exists in history.
            text: The user's message.
            max_tokens: Maximum output tokens.
            history: Chat history (dict with 'cache' and 'turns' keys, or empty list).

        Returns:
            Tuple of (response_text, updated_history, cost, time_cost).
        """
        # 0. Normalize History Structure
        t0 = time.time()
        if not history:
            history = {"cache": None, "turns": []}
        
        # Ensure active_cache attribute exists/refreshed
        active_cache_list = list(self.client.caches.list()) # Convert generator to list
        active_cache_displayname_list = [cache.display_name for cache in active_cache_list]
        active_cache_name_list = [cache.name for cache in active_cache_list]
        
        # Flag to track if we created a cache in this turn
        cache_created_this_turn = False
        
        # 1. Handle PDF and Cache Strategy
        cache_item = history.get("cache")
        
        if pdf:
            if cache_item.get('display_name') != "":
                raise ValueError("Cannot add a new PDF to an existing cached session. Please start a new conversation.")
            
            pdf_path = str(Path(pdf).absolute())
            # Check if we need to create a new cache or use existing one
            # Try to find existing cache first
            found_cache = None
            for cache in active_cache_list:
                if cache.display_name == pdf_path:
                    found_cache = cache
                    print(f"Using existing cache for: {pdf_path}")
                    break
            
            if found_cache:
                cache_item = {
                    "cache_name": found_cache.name,
                    "display_name": found_cache.display_name
                }
            else:
                # Create new cache
                print(f"Caching PDF: {pdf_path}")
                new_cache = self._create_pdf_cache(pdf_path)
                cache_created_this_turn = True # Mark as created
                cache_item = {
                    "cache_name": new_cache.name,
                    "display_name": new_cache.display_name
                }
                # Update local lists
                active_cache_name_list.append(new_cache.name)
            
            # Update history with the selected cache
            history["cache"] = cache_item
            
        # 2. Validate and Reload History Caches (if no new PDF provided, check existing history cache)
        elif cache_item:
            his_name = cache_item.get('cache_name')
            his_display_name = cache_item.get('display_name')
            
            if his_name and his_name not in active_cache_name_list:
                # Cache expired or missing
                if his_display_name and os.path.exists(his_display_name):
                    print(f"Reloading expired cache for: {his_display_name}")
                    try:
                        new_cache = self._create_pdf_cache(his_display_name)
                        cache_created_this_turn = True # Mark as created (reloaded)
                        cache_item['cache_name'] = new_cache.name
                        # Update the set of active caches (local var only)
                        active_cache_name_list.append(new_cache.name)
                    except Exception as e:
                        print(f"Failed to reload cache for {his_display_name}: {e}")
                else:
                    print(f"Warning: Cache {his_name} expired and file {his_display_name} not found or not provided.")

        # 3. Prepare Chat Contents (Flatten turns to API format)
        chat_contents = []
        if history.get("turns"):
            for turn in history["turns"]:
                # Process user part
                user_item = turn.get("user")
                if user_item:
                    # Filter keys to only those accepted by API
                    content_item = {k: v for k, v in user_item.items() if k in ['role', 'parts']}
                    # Convert parts to compatible format
                    new_parts = []
                    for part in content_item.get('parts', []):
                        if isinstance(part, str):
                            new_parts.append({'text': part})
                        else:
                            new_parts.append(part)
                    content_item['parts'] = new_parts
                    chat_contents.append(content_item)

                # Process model part
                model_item = turn.get("model")
                if model_item:
                    # Filter keys to only those accepted by API
                    content_item = {k: v for k, v in model_item.items() if k in ['role', 'parts']}
                    # Convert parts to compatible format
                    new_parts = []
                    for part in content_item.get('parts', []):
                        if isinstance(part, str):
                            new_parts.append({'text': part})
                        else:
                            new_parts.append(part)
                    content_item['parts'] = new_parts
                    chat_contents.append(content_item)
            
        user_msg_api = {'role': 'user', 'parts': [{'text': text}]}
        chat_contents.append(user_msg_api)
        
        # 4. Generate Content
        config_params = {}
        if cache_item and cache_item.get('cache_name'):
            config_params['cached_content'] = cache_item['cache_name']
            
        # Add max_tokens
        # config_params['response_mime_type'] = 'text/plain' # Default
        
        # Create generation config
        gen_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            **config_params
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=chat_contents,
            config=gen_config
        )
        
        # 5. Process Response and Update History
        response_text = response.text
        
        cost = self._calculate_cost(response.usage_metadata, self.model_name, is_cache_creation=cache_created_this_turn)
        time_cost = time.time() - t0
        
        # Construct Turn Data
        user_msg = {'role': 'user', 'parts': [{'text': text}]}
        model_msg = {'role': 'model', 'parts': [{'text': response_text}]}
        
        turn_meta = {
            "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "cost": cost,
            "time_cost": time_cost,
            "model_name": self.model_name
        }
        
        new_turn = {
            "user": user_msg,
            "model": model_msg,
            "meta": turn_meta
        }
        
        # Append new turn to history
        history["turns"].append(new_turn)
        
        # Ensure cache state is preserved
        history["cache"] = cache_item
        
        return response_text, history, cost, time_cost

    def save_history(self, history: Dict, file_path: str):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
            print(f"History saved to {file_path}")
        except Exception as e:
            print(f"Failed to save history: {e}")

    def load_history(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            print(f"History loaded from {file_path}")
            return history
        except Exception as e:
            print(f"Failed to load history: {e}")
            return None

if __name__ == "__main__":
    # Simple Test
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("Please set GEMINI_API_KEY environment variable to run tests.")
    else:
        print("Testing Gemini_interface...")
        gemini = Gemini_interface(key)
        
        # 1. Test basic chat
        print("\n--- Test 1: Basic Chat ---")
        hist = {}
        try:
            res, hist, cost, time_cost = gemini.chat(pdf=None, text="Hello, who are you?")
            print(f"Response: {res}")
            print(f"Cost: ${cost:.6f}")
            print(f"Time: {time_cost:.2f}s")
        except Exception as e:
            print(f"Basic chat failed: {e}")

        # 2. Test PDF Chat
        # Update path to a real PDF for actual testing
        # pdf_path = r"e:\Project\paperreader\code2\test\Security26_SFake.pdf" 
        pdf_path = r"E:\Path\To\Your\Test.pdf" 
        if os.path.exists(pdf_path):
            print("\n--- Test 2: PDF Chat ---")
            try:
                # Note: hist from Test 1 has no cache, so we can upgrade it to PDF chat
                res, hist, cost, time_cost = gemini.chat(pdf=pdf_path, text="Summarize this document.", history=hist)
                print(f"Response: {res}")
                print(f"Cost: ${cost:.6f}")
            except Exception as e:
                print(f"PDF chat failed: {e}")
                
            # 2.1 Test PDF Switch Restriction
            print("\n--- Test 2.1: PDF Switch Restriction (Should Fail) ---")
            try:
                # Try to pass a different PDF (or same one) to an existing cached session
                res, hist, cost, time_cost = gemini.chat(pdf=pdf_path, text="Another doc?", history=hist)
                print("Error: Should have raised ValueError!")
            except ValueError as e:
                print(f"Success: Caught expected error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
        
        # 3. Test History Saving
        print("\n--- Test 3: Save History ---")
        test_dir = r"E:\Project\paperreader\code2\test\temp_gemini_history"
        gemini.save_history(hist, test_dir)
        
        # 4. Test Resume from History (Cache Reloading)
        print("\n--- Test 4: Resume from History ---")
        # Simulate a fresh start by creating a new instance (or just using existing one with same hist)
        # We want to verify it uses the cache from history without us passing 'pdf'
        try:
            # Pass hist which has cache info. pdf=None.
            res, hist, cost, time_cost = gemini.chat(pdf=None, text="What was the summary again?", history=hist)
            print(f"Response: {res}")
            print(f"Cost: ${cost:.6f}")
        except Exception as e:
            print(f"Resume chat failed: {e}")