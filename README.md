Generating auth tokens
---

**Python**
```python
>>> import hmac, hashlib
>>> hmac.HMAC("examplesecret", '{"url": "http://example.com/longlonglongcat"}', hashlib.sha1).hexdigest()
```

Submitting a URL with curl
---

```shell
$ cat > request
{"url": "http://example.com/longlonglongcat"}
^D
$ curl -v -H "Content-Type: application/json" --data-binary @request -H "X-authtoken: $(openssl dgst -sha1 -hmac examplesecret < request)" http://your.url.shortener.example.com/add/
{"url": "http://your.url.shortener.example.com/06caafed-e743-4ae9-a40a-17e015668373"}
```
