# Daily Forecast AI Integration - Root Cause Analysis

## 🔍 Problem
When `use_ai=true` is set in the daily forecast request, the system is **NOT** hitting the OpenAI LLM and instead always using the fallback template.

## 🎯 Root Cause

### Missing OpenAI API Key
The **primary issue** is that the `OPENAI_API_KEY` environment variable is not configured in your development environment.

**Evidence:**
- No `.env` file exists in the project root
- Running `docker-compose exec api printenv | grep OPENAI` returns nothing
- No OpenAI-related environment variables are set in the container

### Code Flow Analysis

#### 1. **Request Flow** (`api/routers/forecasts.py:49-89`)
```python
# Line 76: Reads use_ai from options (default False)
use_ai = options.get("use_ai", False)

# Line 77: Passes it to generate_daily_template
result = generate_daily_template(base_json, request.headers, use_ai=use_ai)
```

#### 2. **Template Generation** (`api/services/daily_template.py:812-831`)
```python
# Line 822-830: IGNORES the parameter and reads from meta instead!
meta = daily_payload.get("meta", {})
use_ai_pref = meta.get("use_ai")  # This will be None if not set

if use_ai_pref is None:
    use_ai = True  # Defaults to True when not specified!
else:
    use_ai = bool(use_ai_pref)
```

**Issue #1**: The function parameter is ignored and overridden by reading from `meta.use_ai`.

#### 3. **OpenAI Client Initialization** (`api/services/daily_template.py:148-175`)
```python
def _get_openai_client() -> Optional["OpenAI"]:
    api_key = os.getenv("OPENAI_API_KEY")  # Line 153
    
    if not api_key or OpenAI is None:
        if not api_key:
            logger.info("daily_template_openai_key_missing")  # Line 158
        _openai_client = None
        return None  # Returns None if key is missing!
```

**Issue #2**: Without `OPENAI_API_KEY`, this returns `None`.

#### 4. **LLM Call Logic** (`api/services/daily_template.py:923-994`)
```python
# Line 923: Gets OpenAI client (returns None if no API key)
llm_client = _get_openai_client() if use_ai else None

# Line 929: Checks BOTH conditions
if llm_client is not None and use_ai:
    # Call OpenAI LLM
    parsed, raw_response, llm_tokens = _render_with_llm(llm_client, daily_payload)
    # ... validation ...

# Line 984: Falls back when llm_client is None OR LLM fails
if generated_payload is None:
    fallback = _build_fallback(daily_payload)  # Always uses fallback!
    generated_payload = fallback.model_dump(mode="json")
```

**Issue #3**: Even with `use_ai=True`, if `llm_client is None` (due to missing API key), it **skips the LLM entirely** and goes straight to the fallback template.

## 📊 Current Behavior

### What Happens Now:
1. Request comes in with `"use_ai": true`
2. Router extracts `use_ai` from options ✅
3. `generate_daily_template()` is called ✅
4. Function overrides parameter with `meta.use_ai` (which is `None`) ⚠️
5. Defaults to `use_ai = True` ✅
6. Calls `_get_openai_client()` ✅
7. **Returns `None` because `OPENAI_API_KEY` is not set** ❌
8. Skips LLM call because `llm_client is None` ❌
9. Uses fallback template immediately ⚠️
10. No error is raised, no warning logged (silent fallback)

## 🔧 Solutions

### Solution 1: Add OpenAI API Key (Recommended)

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_ORG_ID=org-your-org-id  # Optional

# Other environment variables
DATABASE_URL=postgresql://ephem:ephem@postgres:5432/ephemeris
REDIS_URL=redis://localhost:6379/0  # Optional for caching
```

Then restart the containers:
```bash
docker-compose down
docker-compose up -d --build
```

### Solution 2: Fix Parameter Override Issue

The `use_ai` parameter is being ignored. This should be fixed in `daily_template.py`:

**Current code (Lines 822-830):**
```python
meta = daily_payload.get("meta", {})
use_ai_pref = meta.get("use_ai")  # Ignores function parameter!
if isinstance(use_ai_pref, str):
    normalized = use_ai_pref.strip().lower()
    use_ai = normalized in {"1", "true", "yes", "on"}
elif use_ai_pref is None:
    use_ai = True  # Defaults to True
else:
    use_ai = bool(use_ai_pref)
```

**Suggested fix:**
```python
# Respect the function parameter first, then check meta
meta = daily_payload.get("meta", {})
use_ai_pref = meta.get("use_ai")

# Only override if explicitly set in meta
if use_ai_pref is not None:
    if isinstance(use_ai_pref, str):
        normalized = use_ai_pref.strip().lower()
        use_ai = normalized in {"1", "true", "yes", "on"}
    else:
        use_ai = bool(use_ai_pref)
# Otherwise, use the function parameter (already set)
```

### Solution 3: Better Error Handling

Add explicit logging when falling back due to missing API key:

```python
# Line 923
llm_client = _get_openai_client() if use_ai else None

if use_ai and llm_client is None:
    logger.warning(
        "daily_template_openai_unavailable",
        extra={
            "reason": "Missing OPENAI_API_KEY or OpenAI SDK not available",
            "falling_back": True
        }
    )
```

## ✅ Verification Steps

After adding the OpenAI API key:

1. **Check environment variables:**
   ```bash
   docker-compose exec api printenv | grep OPENAI
   ```

2. **Test with use_ai=true:**
   ```bash
   curl -X POST http://localhost:8081/v1/forecasts/daily/forecast \
     -H "Content-Type: application/json" \
     -d '{
       "chart_input": {...},
       "options": {
         "date": "2025-10-26",
         "profile_name": "TestUser",
         "use_ai": true,
         "areas": ["career", "love"]
       }
     }'
   ```

3. **Check logs for OpenAI calls:**
   ```bash
   docker-compose logs api | grep -i openai
   docker-compose logs api | grep "daily_template"
   ```

4. **Look for these log messages:**
   - ✅ `daily_template_llm_call_started` - LLM is being called
   - ✅ Token count in response
   - ❌ `daily_template_openai_key_missing` - API key is missing
   - ❌ `daily_template_fallback_used` - Fallback is being used

## 📝 Additional Notes

### Dependencies Already Installed
- ✅ `redis==5.0.1` (in requirements.prod.txt)
- ✅ `jsonschema==4.22.0` (in requirements.prod.txt)
- ✅ `openai==1.35.10` (in requirements.prod.txt)
- ✅ All dependencies are in development Dockerfile

### Why No Error is Raised
The code is designed to **silently fall back** to the template-based approach when:
- OpenAI API key is missing
- OpenAI SDK is not installed
- API calls fail
- Response validation fails

This is intentional for **graceful degradation**, but it makes debugging harder because there's no obvious error message to the client.

## 🎯 Recommended Action

**Immediate fix:**
1. Create `.env` file with `OPENAI_API_KEY`
2. Restart containers: `docker-compose down && docker-compose up -d`
3. Test with `use_ai=true`
4. Verify logs show OpenAI calls

**Long-term improvements:**
1. Fix the parameter override issue in `generate_daily_template()`
2. Add explicit warning logs when falling back due to missing API key
3. Consider returning metadata in the response indicating whether AI was used
4. Document the required environment variables clearly

