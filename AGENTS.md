# Spider_XHS Knowledge Base

**Generated:** 2026-01-31
**Project:** XiaoHongShu (小红书) Web Scraper
**Stack:** Python 3.7+ / Node.js 18+ (Hybrid)

## OVERVIEW
XiaoHongShu data collection solution. Scrapes notes (posts), user profiles, comments, supports Excel/JSON/media output. Uses Python for orchestration + Node.js for signature generation via PyExecJS.

## STRUCTURE
```
.
├── apis/               # API clients (XHS PC + Creator platform)
├── xhs_utils/          # Utilities (data handling, audio processing, auth)
├── static/             # JS files for X-S token/X-Ray signature generation
├── datas/              # Output directory (media + excel)
├── main.py             # Entry point
└── postprocess_audio.py # VAD-based video filtering
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add new API endpoint | `apis/xhs_pc_apis.py` | Follow `(success, msg, data)` return pattern |
| Modify data extraction | `xhs_utils/data_util.py` | `handle_note_info()`, `handle_user_info()` |
| Fix auth/signature issues | `static/*.js` + `xhs_utils/xhs_util.py` | X-S tokens generated via JS |
| Add download logic | `xhs_utils/data_util.py` | `download_note()`, `download_media()` |
| Audio post-processing | `xhs_utils/audio_filter.py` | webrtcvad-based speech detection |
| Creator platform APIs | `apis/xhs_creator_apis.py` | Separate from PC APIs |

## CODE MAP

### Main Classes
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `Data_Spider` | Class | `main.py:9` | Main orchestrator |
| `XHS_Apis` | Class | `apis/xhs_pc_apis.py:13` | PC API client (30+ methods) |
| `XHS_Creator_Apis` | Class | `apis/xhs_creator_apis.py:7` | Creator platform APIs |

### Key Functions
| Symbol | Location | Purpose |
|--------|----------|---------|
| `generate_request_params` | `xhs_utils/xhs_util.py:90` | Builds authenticated headers |
| `handle_note_info` | `xhs_utils/data_util.py:65` | Transforms raw note data |
| `download_note` | `xhs_utils/data_util.py:296` | Downloads media + metadata |
| `init` | `xhs_utils/common_util.py:10` | Setup paths, load env |

## CONVENTIONS

### Return Pattern (CRITICAL)
All API methods return 3-tuple: `(success: bool, msg: str, data: any)`
```python
try:
    res_json = response.json()
    success, msg = res_json["success"], res_json["msg"]
except Exception as e:
    success, msg = False, str(e)
return success, msg, res_json
```

### Import Order
1. Standard lib (`json`, `os`, `re`)
2. Third-party (`requests`, `loguru`)
3. Local (`from xhs_utils.xhs_util import ...`)

### Naming
- Classes: `PascalCase` (`XHS_Apis`, `Data_Spider`)
- Functions: `snake_case` (`spider_note`, `handle_user_info`)
- Constants: `UPPER_CASE` (`VALID_FRAME_MS`)

### Documentation
- Chinese docstrings required for consistency
- Parameter docs: `:param name: description`
- Return docs: `返回...`

## ANTI-PATTERNS (THIS PROJECT)
- **Never** hardcode credentials - use `.env` + `python-dotenv`
- **Never** change return pattern from `(success, msg, data)`
- **Never** delete `info.json` files - they contain metadata
- **Never** skip `norm_str()` when creating file paths (Windows path issues)
- **Never** remove `verify=False` in requests (required for XHS SSL)

## UNIQUE STYLES

### Hybrid Python/JS Architecture
Python calls Node.js via `PyExecJS` for X-S signature generation:
```python
js = execjs.compile(open('static/xhs_xs_xsc_56.js').read())
ret = js.call('get_xs', api, data, a1)
```

### Retry Decorator
Network operations use `@retry`:
```python
from retry import retry

@retry(tries=3, delay=1)
def download_media(...):
```

### Path Handling
Always use absolute paths with parent traversal:
```python
os.path.abspath(os.path.join(os.path.dirname(__file__), '../datas/media_datas'))
```

## COMMANDS
```bash
# Setup
pip install -r requirements.txt
npm install

# Run
python main.py

# Audio post-processing
python postprocess_audio.py --action mark
python postprocess_audio.py --action delete

# Docker
docker build -t spider_xhs .
docker run -p 5000:5000 spider_xhs
```

## NOTES
- **No tests** - This project has no test suite
- **No CI/CD** - No GitHub Actions or automation
- **No linting configs** - No black/flake8/eslint configured
- **Cookie dependency** - Must set `COOKIES` in `.env` file (login required)
- **Proxy support** - All API methods accept optional `proxies` dict
- **Rate limiting** - Built-in retry via `@retry` decorator
- **Legal warning** - "任何涉及数据注入的操作都是不被允许的" (data injection prohibited)
