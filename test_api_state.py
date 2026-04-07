import requests
import re

print("Testing direct sequence:")
res = requests.post("http://127.0.0.1:8000/set_level", json={"task_level": "easy"})
res = requests.post("http://127.0.0.1:8000/reset", json={})
data = res.json()
log = data["observation"]["hardware_logs"][-1]
print("Log:", log)
match = re.search(r'node_\d+', log)
node = match.group(0) if match else "node_0"
print("Extracted Node:", node)

res2 = requests.post("http://127.0.0.1:8000/step", json={"action": {"command": "DRAIN_TRAFFIC", "target": node}})
print("Step Result:", res2.json())
