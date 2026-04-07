import requests

res = requests.post("http://127.0.0.1:8000/reset", json={})
print("reset:", res.json())

res2 = requests.post("http://127.0.0.1:8000/step", json={"command": "DRAIN_TRAFFIC", "target": "node_97"})
print("step:", res2.json())
