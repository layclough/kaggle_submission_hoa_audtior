# app/agent.py
import os
import json
import hashlib
import time
import yaml
from google import genai
from google.genai import types

# Default mock-data fallback text string representing a complex condo disclosure package
DEFAULT_MOCK_DATA_FALLBACK = """
=== FILE: ccrs.txt ===
Section 7.1: Rental leasing cap is set at 15% of all units. Current occupancy is at 14.8%.
Section 8.5: Homeowners are limited to two domestic pets with a weight limit of 35 lbs each.

=== FILE: bylaws.txt ===
Article VI Section 2: Weight limit of domestic pets is restricted to 35 lbs.

=== FILE: financials.txt ===
Roofing assessment of $5,000.00 per unit is pending due to roof leaks.

=== FILE: resale_cert.txt ===
Special assessment of $5,000.00 for roofing repairs will be active next month.
Current monthly maintenance dues are $450.00.
The reserve fund has $120,000.00 but needs $400,000.00 based on the reserve study. It is 30% funded.
"""

def sanitize_json_newlines(json_str: str) -> str:
    """
    State-machine parser that scans raw response text.
    If it detects literal, physical line breaks inside active JSON string quotes,
    it converts them to safe escaped string literals (\\n) before decoding.
    """
    result = []
    in_string = False
    escaped = False
    for char in json_str:
        if char == '"' and not escaped:
            in_string = not in_string
        
        if char == '\\' and not escaped:
            escaped = True
        else:
            escaped = False
            
        if in_string and char in ('\n', '\r'):
            result.append('\\n')
        else:
            result.append(char)
    return "".join(result)

def repair_json_unterminated_strings(raw_text: str) -> str:
    """
    Standardizes output strings, strips potential markdown block wrapping
    (such as ```json or ```), and attempts to append missing close-quotes
    on unclosed string attributes to guarantee robust JSON evaluation.
    """
    # 1. Strip potential markdown blocks
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        newline_idx = raw_text.find("\n")
        if newline_idx != -1:
            raw_text = raw_text[newline_idx:].strip()
        else:
            raw_text = raw_text[3:].strip()
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()
    raw_text = raw_text.strip()

    # 2. Repair unterminated quotes line-by-line
    lines = raw_text.splitlines()
    repaired_lines = []
    for line in lines:
        unescaped_quotes_count = 0
        in_escape = False
        for char in line:
            if char == '\\':
                in_escape = not in_escape
            elif char == '"':
                if not in_escape:
                    unescaped_quotes_count += 1
                in_escape = False
            else:
                in_escape = False

        if unescaped_quotes_count % 2 != 0:
            right_trimmed = line.rstrip()
            suffix_chars = []
            while right_trimmed and right_trimmed[-1] in (',', ']', '}', ' '):
                suffix_chars.append(right_trimmed[-1])
                right_trimmed = right_trimmed[:-1]
            suffix = "".join(reversed(suffix_chars))
            line = right_trimmed + '"' + suffix
        repaired_lines.append(line)

    return "\n".join(repaired_lines)

def escape_unescaped_quotes_in_json(json_str: str) -> str:
    """
    Scans a flattened JSON string line-by-line and escapes any raw,
    unescaped double quotes found inside string property values.
    """
    import re
    lines = json_str.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r'^(\s*"[a-zA-Z0-9_-]+"\s*:\s*")(.*)("\s*,?\s*)$', line)
        if match:
            prefix, value, suffix = match.groups()
            escaped_value = []
            escaped = False
            for char in value:
                if char == '\\':
                    escaped = not escaped
                    escaped_value.append(char)
                elif char == '"':
                    if not escaped:
                        escaped_value.append('\\"')
                    else:
                        escaped_value.append(char)
                    escaped = False
                else:
                    escaped = False
                    escaped_value.append(char)
            lines[i] = prefix + "".join(escaped_value) + suffix
    return "\n".join(lines)

class HOAAuditorLivePipeline:
    def __init__(self):
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    clean_line = line.strip()
                    if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                        continue
                    key, val = clean_line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        # Fallback support if API key is a placeholder or not provided
        if not api_key or api_key.startswith("your_"):
            print("WARNING: GEMINI_API_KEY missing or placeholder in app/.env")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
        
        self.model_name = "gemini-2.5-flash"

    def run_agent_analysis(self) -> tuple[dict, bool]:
        """
        Token-Saving Agent Flow: Hashes document inventory text.
        Applies caching strategies (Supabase cloud & local JSON fallback),
        and falls back to live Gemini generation on cache miss.
        """
        # 1. Ingest all target workspace text files dynamically
        combined_package_text = ""
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mock_data"))
        
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            try:
                txt_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".txt")])
                for filename in txt_files:
                    file_path = os.path.join(data_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        combined_package_text += f"\n\n=== FILE: {filename} ===\n{content}"
            except Exception as e:
                print(f"[INGESTION ERROR] Failed to read from mock_data folder: {e}")

        if not combined_package_text.strip():
            print("[INGESTION CAUTION] Ingest directory empty or missing. Triggering default mock-data fallback...")
            combined_package_text = DEFAULT_MOCK_DATA_FALLBACK

        # 2. Ingest YAML governance schemas
        manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "system", "schemas", "report_manifest.yaml"))
        governance_rules = ""
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    governance_rules = yaml.dump(yaml.safe_load(f), default_flow_style=False)
            except Exception as e:
                print(f"[MANIFEST WARNING] Failed to read manifest: {e}")

        # 3. Generate cryptographic signature of combined package
        doc_hash = hashlib.md5(combined_package_text.encode('utf-8')).hexdigest()

        # 4. Level 1 Cache: Cloud Cache (Supabase)
        supabase_connected = False
        supabase_client = None
        
        supabase_url = os.environ.get("SUPABASE_URL", "").strip()
        supabase_key = os.environ.get("SUPABASE_KEY", "").strip() or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        
        def is_placeholder(val: str) -> bool:
            if not val:
                return True
            v = val.lower()
            return any(p in v for p in ["your_", "placeholder", "key_here", "url_here"])

        if not is_placeholder(supabase_url) and not is_placeholder(supabase_key):
            try:
                from supabase import create_client
                supabase_client = create_client(supabase_url, supabase_key)
                cached_query = supabase_client.table("hoa_reports").select("payload").eq("document_hash", doc_hash).execute()
                supabase_connected = True
                if cached_query.data:
                    print("🎯 [CACHE HIT] Identical document set detected! Retrieving from Supabase Cache...")
                    payload = cached_query.data[0]["payload"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    return payload, True
            except Exception as e:
                print(f"[CACHE CAUTION] Supabase lookup bypassed/failed: {e}")

        # 5. Level 2 Cache: Local Sandbox Cache (JSON Fallback)
        local_cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.local_cache.json'))
        if os.path.exists(local_cache_path):
            try:
                with open(local_cache_path, 'r', encoding='utf-8') as f:
                    local_cache = json.load(f)
                    if isinstance(local_cache, dict) and doc_hash in local_cache:
                        print("🎯 [CACHE HIT] Identical document set detected! Retrieving from Local JSON Cache...")
                        payload = local_cache[doc_hash]
                        if isinstance(payload, str):
                            payload = json.loads(payload)
                        return payload, True
            except Exception as e:
                print(f"[CACHE CAUTION] Local cache lookup bypassed/failed: {e}")

        # 6. API Execution (if caches miss)
        if not self.client:
            return {"error": "Simulation Mode: API key missing."}, False

        regulations_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'wucia_regulations.json'))
        wucioa_framework = ""
        if os.path.exists(regulations_path):
            try:
                with open(regulations_path, 'r', encoding='utf-8') as f:
                    wucioa_framework = f.read()
            except Exception as e:
                print(f"[REGULATION WARNING] Failed to read regulations: {e}")

        governance_prompt = f"""
You are an expert real estate compliance risk system. Analyze the data and return a structured JSON object fitting the schema requirements perfectly.

CRITICAL GOVERNANCE MANIFEST CONSTRAINTS:
{governance_rules}

STATE COMPLIANCE MANDATE CHECKLIST (WASHINGTON STATE RCW 64.90.640):
{wucioa_framework}

SIMPLE ENGLISH TRANSLATION INSTRUCTION:
1. Identify and return ONLY the top 4 most critical financial or legal risks. Ignore minor issues.
2. The 'buyer_note' property MUST be a single short sentence explaining the direct out-of-pocket cost impact.
3. Cross-reference your findings by setting 'risk_id' to match the rules specified in the manifest (e.g. 'XR-1-1').
4. Include the exact citation anchors provided in the raw files using the formatting '[source: X]'.

HOA PACKAGE TEXT DATA TO AUDIT:
{combined_package_text}
"""

        # Import target response schema dynamically if available
        import app.schema
        target_schema = getattr(app.schema, 'TARGET_RESPONSE_SCHEMA', getattr(app.schema, 'HOAAuditReport', None))

        print(f"💸 [TOKEN EXPENSE] Triggering {self.model_name} Call...")
        
        # Retry with exponential backoff: 1s, 2s, 4s, 8s, 16s
        backoff_delays = [1, 2, 4, 8, 16]
        response = None
        
        for attempt, delay in enumerate(backoff_delays):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=governance_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=target_schema,
                        max_output_tokens=8192,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=0
                        )
                    )
                )
                break
            except Exception as e:
                if attempt == len(backoff_delays) - 1:
                    return {"error": f"Live generation failed after backoff retries: {e}"}, False
                time.sleep(delay)

        if response:
            try:
                report_text = response.text.strip()
                
                # Write to debug file
                try:
                    debug_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'debug_output.txt'))
                    with open(debug_path, 'w', encoding='utf-8') as df:
                        df.write("--- RAW RESPONSE START ---\n")
                        df.write(report_text)
                        df.write("\n--- RAW RESPONSE END ---\n")
                except Exception as de:
                    print(f"[DEBUG WRITE ERROR] {de}")
                
                # Apply parsing guardrails
                sanitized_text = repair_json_unterminated_strings(report_text)
                sanitized_text = sanitize_json_newlines(sanitized_text)
                sanitized_text = escape_unescaped_quotes_in_json(sanitized_text)
                
                report_json = json.loads(sanitized_text, strict=False)
                report_json["document_hash"] = doc_hash

                # Write back to local cache sandbox
                try:
                    local_cache = {}
                    if os.path.exists(local_cache_path):
                        try:
                            with open(local_cache_path, 'r', encoding='utf-8') as f:
                                local_cache = json.load(f)
                                if not isinstance(local_cache, dict):
                                    local_cache = {}
                        except Exception:
                            local_cache = {}
                    
                    local_cache[doc_hash] = report_json
                    with open(local_cache_path, 'w', encoding='utf-8') as f:
                        json.dump(local_cache, f, indent=2)
                    print("Successfully saved report to Local JSON Cache.")
                except Exception as le:
                    print(f"[CACHE ERROR] Failed to write to local cache: {le}")

                # Write back to Supabase if connected
                if supabase_connected and supabase_client:
                    try:
                        supabase_client.table("hoa_reports").upsert({
                            "document_hash": doc_hash,
                            "payload": report_json
                        }, on_conflict="document_hash").execute()
                        print("Successfully synced report to Supabase cache.")
                    except Exception as se:
                        print(f"[DATABASE ERROR] Failed to write back to Supabase: {se}")

                return report_json, False
            except Exception as e:
                return {"error": f"Failed to parse model structure: {e}"}, False
        else:
            return {"error": "No response returned from the model tier."}, False