# apis/ Directory

**Domain:** XiaoHongShu API Clients
**Files:** 3 Python modules

## OVERVIEW
API layer for XiaoHongShu platform. Separates PC web APIs from Creator platform APIs.

## STRUCTURE
```
apis/
├── xhs_pc_apis.py       # Main PC API client (~1000 lines, 30+ methods)
├── xhs_creator_apis.py  # Creator platform APIs
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add PC endpoint | `xhs_pc_apis.py` | Extend `XHS_Apis` class |
| Add Creator endpoint | `xhs_creator_apis.py` | Extend `XHS_Creator_Apis` class |
| Fix auth headers | Use `generate_request_params()` | From `xhs_utils.xhs_util` |

## CONVENTIONS

### Return Pattern (MANDATORY)
```python
return success, msg, res_json
# success: bool
# msg: str
# res_json: dict or None
```

### Method Structure
```python
def get_something(self, cookies_str: str, proxies: dict = None):
    res_json = None
    try:
        api = "/api/..."
        headers, cookies, data = generate_request_params(cookies_str, api, '', 'GET')
        response = requests.get(self.base_url + api, headers=headers, cookies=cookies, proxies=proxies)
        res_json = response.json()
        success, msg = res_json["success"], res_json["msg"]
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, res_json
```

### Pagination Pattern
```python
cursor = ''
results = []
while True:
    success, msg, res_json = self.get_page(cursor, cookies_str)
    if not success:
        raise Exception(msg)
    results.extend(res_json["data"]["items"])
    if not res_json["data"]["has_more"]:
        break
    cursor = res_json["data"]["cursor"]
```

## ANTI-PATTERNS
- **Never** change the `(success, msg, data)` return signature
- **Never** remove `verify=False` in requests (required for XHS SSL)
- **Never** skip exception handling - always wrap API calls
