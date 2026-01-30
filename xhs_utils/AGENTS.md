# xhs_utils/ Directory

**Domain:** Utility Modules
**Files:** 7 Python modules

## OVERVIEW
Core utilities for data processing, authentication, downloads, and audio filtering.

## STRUCTURE
```
xhs_utils/
├── data_util.py         # Data transformation & downloads (~320 lines)
├── audio_filter.py      # VAD-based speech detection (~260 lines)
├── xhs_util.py          # X-S token generation & headers (~100 lines)
├── xhs_creator_util.py  # Creator platform auth (~50 lines)
├── common_util.py       # Path setup & env loading (~20 lines)
├── cookie_util.py       # Cookie parsing (~10 lines)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Transform note data | `data_util.py:handle_note_info()` | Extracts fields from API response |
| Transform user data | `data_util.py:handle_user_info()` | Extracts user profile fields |
| Download media | `data_util.py:download_note()` | Saves images/videos + metadata |
| Generate X-S token | `xhs_util.py:generate_xs()` | Calls JS via PyExecJS |
| Build headers | `xhs_util.py:generate_request_params()` | Returns (headers, cookies, data) |
| Filter silent videos | `audio_filter.py` | webrtcvad-based detection |

## CONVENTIONS

### Path Normalization
Always use `norm_str()` for file paths:
```python
from xhs_utils.data_util import norm_str
safe_title = norm_str(title)[:40]  # Remove illegal chars, limit length
```

### Retry Decorator
Network operations must use retry:
```python
from retry import retry

@retry(tries=3, delay=1)
def download_media(...):
```

### JSON Serialization
Use compact format for API payloads:
```python
json.dumps(data, separators=(',', ':'), ensure_ascii=False)
```

### Absolute Paths
Always resolve to absolute paths:
```python
os.path.abspath(os.path.join(os.path.dirname(__file__), '../datas/media_datas'))
```

## ANTI-PATTERNS
- **Never** skip `norm_str()` when creating file paths
- **Never** delete `info.json` files after download (contain metadata)
- **Never** hardcode credentials - use `load_env()` from `common_util.py`
