import requests

def is_in_game():
    # print("[LCA] Checking if in-game via Live Client API…")
    urls = [
        "http://127.0.0.1:2999/liveclientdata/gamestats",
        "https://127.0.0.1:2999/liveclientdata/gamestats",
    ]
    for url in urls:
        try:
            # try HTTP first (no cert issues), then HTTPS with verify=False if needed
            verify = False if url.startswith("https://") else True
            # use separate connect/read timeouts so local endpoint has enough time to respond
            timeout = (0.5, 2.0)  # (connect, read)
            if not verify:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            r = requests.get(url, timeout=timeout, verify=verify)
            # print("[LCA] Tried", url, "->", getattr(r, "status_code", "no-response"))
            if r.ok:
                # ensure we can parse JSON (browser showed JSON body)
                # try:
                #     _ = r.json()
                # except Exception as je:
                    # print("[LCA] Warning: response not JSON:", je)
                return True
        except:
            pass
        # except requests.ReadTimeout:
            #print(f"[LCA] Read timed out for {url}")
        # except requests.RequestException as exc:
            #print(f"[LCA] Request to {url} failed: {exc}")
            # try next URL
    # print("[LCA] No reachable Live Client API endpoint, assuming not in-game.")
    return False