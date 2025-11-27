# BrowserControL01 - Quick Start Guide

## Overview

BrowserControL01 is a stealth web automation framework that provides:
- ✅ Undetected browser automation (anti-bot detection)
- ✅ Human behavior emulation
- ✅ Site-specific modules (Google, Amazon, eBay, Wikipedia, ChatGPT, Generic)
- ✅ Intelligent element finding with multiple strategies
- ✅ Content extraction and article parsing
- ✅ Session persistence and profile management

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/browserControl.git
cd browserControl

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

### 1. Google Search

```bash
python src/main.py site google "python automation"
```

Or with explicit operation:

```bash
python src/main.py site google --operation search --query "python automation"
```

### 2. Wikipedia Article Extraction

```bash
# Basic article extraction
python src/main.py wikipedia "Python programming language"

# With image download and link exploration
python src/main.py wikipedia "Artificial Intelligence" \
    --image-min-width 800 \
    --depth 1 \
    --max-pages 3 \
    --follow-keywords machine learning neural networks
```

### 3. Amazon Product Search

```bash
python src/main.py site amazon "laptop" --operation search
```

### 4. Generic Site Interaction

```bash
python src/main.py generic \
    --url "https://example.com" \
    --input-text "search query" \
    --input-selectors "input[name='q']" \
    --click-selectors "button[type='submit']" \
    --extraction-type article
```

## Configuration

### Using Custom Config File

Create a JSON configuration file:

```json
{
    "headless_mode": true,
    "enable_basic_stealth": true,
    "log_file": "custom-log.log",
    "user_agent_override": "Mozilla/5.0 ..."
}
```

Use it:

```bash
python src/main.py --config my_config.json site google "test"
```

### Browser Profiles

```bash
# Use a specific profile
python src/main.py --profile my_profile site google "test"

# Import external Chrome profile
python src/main.py admin import-session \
    --source "/path/to/chrome/profile" \
    --target my_bot_profile
```

## Execution Flow

```
main.py
  ├─ Load configuration (with validation)
  ├─ Initialize BrowserControlSystem
  │   ├─ Register site modules
  │   └─ Setup security manager (if enabled)
  ├─ Execute site workflow
  │   ├─ Get/create browser driver
  │   ├─ Load site configuration
  │   ├─ Instantiate site module
  │   └─ Run operation (search, interact, etc.)
  └─ Cleanup resources
      ├─ Close browser driver
      └─ Cleanup security manager
```

## Testing

### Run Core Component Tests

```bash
python test_core.py
```

Expected output:
```
======================================================================
BrowserControL01 - Core Component Tests
======================================================================

TEST SUMMARY: 12 passed, 0 failed
======================================================================
```

### Run End-to-End Smoke Tests

```bash
python test_e2e_smoke.py
```

Validates:
- System initialization
- Site module registration
- Selector file integrity
- Configuration loading
- Execution flow components

## Site Modules

| Module | Operations | Description |
|--------|-----------|-------------|
| **google** | search | Google search with result extraction |
| **amazon** | search | Amazon product search |
| **ebay** | search | eBay item search |
| **wikipedia** | get_data, search | Article extraction with links/images |
| **chatgpt** | search (prompt) | ChatGPT interaction |
| **generic** | interact | Universal site interaction |

## Parameter Normalization

The system automatically normalizes parameter aliases:

| Alias | Maps To |
|-------|---------|
| `q` | `query` |
| `url` | `query_or_url` |
| `search` | `query` |
| `term` | `query` |

This allows flexible command invocation:

```bash
# All equivalent:
python src/main.py site google "test"
python src/main.py site google --query "test"
python src/main.py site google --params '{"q": "test"}'
```

## Output

Results are returned as JSON:

```json
{
    "success": true,
    "data": {
        "results": [...],
        "url": "https://...",
        "timestamp": "..."
    },
    "execution_time": 2.5,
    "errors": []
}
```

## Error Handling

The system implements fail-fast validation:

- ❌ **Missing config file** → `FileNotFoundError` (immediate)
- ❌ **Invalid JSON** → `ValueError` with line number
- ❌ **Type mismatch** → `TypeError` with expected/actual types
- ❌ **Missing parameters** → Validation error before execution

## Debug Logging

All debug output is written to `debug-log.txt`:

```bash
# View debug log
tail -f debug-log.txt

# Enable verbose console output
python src/main.py --verbose site google "test"
```

## Manual Intervention Mode

For complex workflows requiring human interaction:

```bash
python src/main.py --manual-intervention site google "test"
```

This will pause at key points and prompt for manual actions.

## Architecture

### Core Components

- **BrowserControlSystem**: Main orchestrator
- **StealthBrowserManager**: Browser lifecycle management
- **HumanBehaviorEngine**: Human-like actions (typing, scrolling, pauses)
- **AdaptiveDOMInteractor**: Multi-strategy element finding
- **BaseSiteModule**: Abstract base for site-specific modules
- **BaseWorkflow**: Workflow execution framework

### Design Principles

✅ **Fail-Fast**: Validate early, catch errors immediately
✅ **Type Safety**: Strict configuration validation
✅ **Resource Management**: Proper cleanup with try-finally
✅ **Separation of Concerns**: Clear module boundaries
✅ **Extensibility**: Easy to add new site modules

## Troubleshooting

### Browser Won't Start

```bash
# Check Chrome/Chromium installed
which google-chrome
which chromium-browser

# Try headless mode
python src/main.py --config <(echo '{"headless_mode": true}') ...
```

### Elements Not Found

1. Check selector file: `src/sites/selectors/{site}_selectors.json`
2. Enable debug logging: Check `debug-log.txt`
3. Try manual intervention mode to inspect page

### Import Errors

```bash
# Verify dependencies
pip install -r requirements.txt

# Check Python version (3.8+)
python --version
```

## Next Steps

1. **Explore Examples**: See `examples/` directory
2. **Read Architecture Docs**: See `docs/ARCHITECTURE.md`
3. **Create Custom Module**: Extend `BaseSiteModule`
4. **Contribute**: Submit pull requests

## Support

- **Issues**: https://github.com/yourusername/browserControl/issues
- **Documentation**: https://github.com/yourusername/browserControl/wiki
- **Tests**: Run `python test_core.py` and `python test_e2e_smoke.py`
