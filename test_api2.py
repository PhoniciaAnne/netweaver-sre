import requests

res = requests.post("http://127.0.0.1:8000/reset", json={})
data = res.json()
print("RESET KEYS:", data.keys())
print("session_id in reset?", "session_id" in data)

# Let's test passing session_id to step
if "session_id" in data:
    sid = data["session_id"]
    print("GOT SID:", sid)
    # Extract the faulty node if we can from log
    # Just to see if step with session_id works
    import re
    log = data["observation"]["hardware_logs"][1]
    match = re.search(r'node_\d+', log)
    node = match.group(0) if match else "node_0"
    print("Guessed node:", node)
    res2 = requests.post("http://127.0.0.1:8000/step", json={"action": {"command": "DRAIN_TRAFFIC", "target": node}, "session_id": sid})
    print("STEP RESPONSE:", res2.json())
