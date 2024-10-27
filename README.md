# Requests WinHTTP Adapter

```python
import requests
from requests_winhttp_adapter import WinHttpAdapter

with requests.Session() as session:
    session.mount("http://", WinHttpAdapter())
    session.mount("https://", WinHttpAdapter())
    response = session.get("http://www.google.com/")
    print(response.text)
```
