# Test Report — `test_llm`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 4 total — **4 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `AnthropicLLM rejects empty credentials`

**Result**: ✅ PASS
**Purpose**: Constructor must raise ValueError if no api_key and no ANTHROPIC_API_KEY env var.

**Inputs**:
```
{
  "api_key": null,
  "ANTHROPIC_API_KEY": "unset"
}
```

**Expected**:
```
{
  "raises": true,
  "mentions_api_key": true
}
```

**Actual**:
```
{
  "raises": true,
  "message": "No API key provided. Set ANTHROPIC_API_KEY or pass api_key=."
}
```

**Conclusion**: Fail-fast avoids silent no-op calls when credentials are missing.

---

## Case 2: `AnthropicLLM default model and max_tokens`

**Result**: ✅ PASS
**Purpose**: Defaults should be DEFAULT_MODEL and max_tokens=16384.

**Inputs**:
```
{
  "api_key": "sk-ant-test-not-real (env)"
}
```

**Expected**:
```
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 16384
}
```

**Actual**:
```
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 16384
}
```

**Conclusion**: Sensible defaults so callers just need an API key.

---

## Case 3: `make_llm falls back to AnthropicLLM when no llmutils config exists`

**Result**: ✅ PASS
**Purpose**: A missing config file should not raise; the factory should fall back to Anthropic directly.

**Inputs**:
```
{
  "config": "nonexistent.yaml"
}
```

**Expected**:
```
{
  "is_anthropic_llm": true,
  "model": "claude-sonnet-4-20250514"
}
```

**Actual**:
```
{
  "is_anthropic_llm": true,
  "model": "claude-sonnet-4-20250514"
}
```

**Conclusion**: Graceful fallback keeps production paths resilient to missing configs.

---

## Case 4: `claude-cli haiku smoke (skipped)`

**Result**: ✅ PASS
**Purpose**: Optional live test — skipped because ALPHA_RESEARCH_SKIP_LIVE_LLM=1.

**Inputs**:
```
{
  "model": "claude-haiku-4-5-20251001",
  "skipped_reason": "env var"
}
```

**Expected**:
```
skipped
```

**Actual**:
```
skipped
```

**Conclusion**: Live LLM test intentionally skipped in this environment.

---

## Summary

- **Total tests**: 4
- **Passed**: 4
- **Failed**: 0
- **Pass rate**: 100.0%
