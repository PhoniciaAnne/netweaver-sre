# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
Netweaver SRE Environment Implementation.
Advanced fault simulation for GPU clusters with incremental reward signals.
"""

import random
import os
from uuid import uuid4
from typing import Dict, List, Optional, Any

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import NetweaverSreAction, NetweaverSreObservation
except ImportError:
    from models import NetweaverSreAction, NetweaverSreObservation

# Module-level control for task leveling
_FORCED_TASK_LEVEL: str = ""

def set_task_level(level: str) -> None:
    global _FORCED_TASK_LEVEL
    _FORCED_TASK_LEVEL = level.lower().strip()

class NetweaverSreEnvironment(Environment):
    """
    Simulates a high-scale GPU cluster SRE scenario.
    Provides incremental rewards for progressive fault isolation.
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = False
    MAX_ATTEMPTS: int = 15

    def __init__(self):
        self._cache = {
            "state": State(episode_id=str(uuid4()), step_count=0),
            "queue_depths": {"spine_1": 10.0, "spine_2": 10.0},
            "gradient_vars": [0.01] * 16,
            "logs": [],
            "faulty_node_id": "",
            "active_task": "easy",
            "target_pfc": 0.0,
            "drained_nodes": set(),
            "last_dist": 100.0,
            "search_range": 16,
            "grading_info": {}
        }

    def reset(self, **kwargs) -> NetweaverSreObservation:
        global _FORCED_TASK_LEVEL
        
        self._cache["state"] = State(episode_id=str(uuid4()), step_count=0)
        self._cache["drained_nodes"] = set()
        self._cache["grading_info"] = {"status": "started", "score": 0.0, "bonuses": 0, "penalties": 0}
        
        forced = _FORCED_TASK_LEVEL or os.getenv("FORCE_TASK_LEVEL", "")
        self._cache["active_task"] = forced if forced else kwargs.get("task_level", random.choice(["easy", "medium", "hard"]))
        
        self._cache["faulty_node_id"] = f"node_{random.randint(10, 99)}"
        self._cache["target_pfc"] = float(random.randint(40, 80))
        self._cache["last_dist"] = 100.0
        self._cache["search_range"] = 16
        
        self._cache["queue_depths"] = {"spine_1": 8.5, "spine_2": 9.2}
        self._cache["gradient_vars"] = [round(random.uniform(0.01, 0.03), 3) for _ in range(16)]
        self._cache["logs"] = [
            f"SYSTEM: Cluster initialization complete. Mode: {self._cache['active_task'].upper()}"
        ]
        
        task = self._cache["active_task"]
        fnode = self._cache["faulty_node_id"]
        
        if task == "easy":
            self._cache["logs"].append(f"ALERT: Heartbeat lost for {fnode}. Isolate via DRAIN_TRAFFIC.")
        elif task == "medium":
            self._cache["queue_depths"]["spine_1"] = 99.5
            self._cache["logs"].append(f"WARN: PFC Buffer Congestion on spine_1 (99.5%). Target optimization threshold: {self._cache['target_pfc']}")
        elif task == "hard":
            fault_idx = int(fnode.split("_")[1]) % 16
            self._cache["gradient_vars"][fault_idx] = 888.88
            self._cache["logs"].append("INCIDENT: Global gradient corruption detected. Triage via binary search using RUN_MINI_ITERATION.")

        return self._get_obs(done=False, reward=0.0)

    def step(self, action: NetweaverSreAction) -> NetweaverSreObservation:  # type: ignore[override]
        self._cache["state"].step_count += 1
        
        cmd = action.command.upper()
        tgt = action.target
        val = action.value
        
        done = False
        reward = 0.0
        grading = self._cache["grading_info"]
        grading["status"] = "in_progress"
        
        task = self._cache["active_task"]
        fnode = self._cache["faulty_node_id"]
        logs = self._cache["logs"]
        
        # Incremental logic
        if cmd == "DRAIN_TRAFFIC":
            if tgt == fnode:
                logs.append(f"SUCCESS: {tgt} isolated. Cluster stabilizing.")
                # Final reward based on steps
                reward = round(1.0 - (self._cache['state'].step_count * 0.03), 2)
                reward = max(0.5, reward)
                grading["score"] += reward
                grading["status"] = "success"
                done = True
            else:
                logs.append(f"ERROR: Incorrect isolation of {tgt}. Destructive action penalty.")
                reward = -0.3
                grading["score"] += reward
                grading["penalties"] += 1
                self._cache["drained_nodes"].add(tgt)

        elif cmd == "TUNE_PFC_THRESHOLD":
            if task == "medium" and val is not None:
                new_dist = abs(self._cache["target_pfc"] - float(val))
                if new_dist < self._cache["last_dist"]:
                    # Positive feedback for closing in
                    reward = 0.1
                    grading["bonuses"] += 1
                    grading["score"] += reward
                    self._cache["last_dist"] = new_dist
                    logs.append(f"EXEC: Threshold adjustment successful. Progress detected.")
                
                if new_dist <= 2.0:
                    logs.append("SUCCESS: Congestion cleared. Optimal parameters applied.")
                    final_bonus = round(1.0 - (self._cache['state'].step_count * 0.03), 2)
                    reward += max(0.4, final_bonus)
                    grading["score"] += reward
                    grading["status"] = "success"
                    done = True
                    self._cache["queue_depths"]["spine_1"] = 12.0
                else:
                    self._cache["queue_depths"]["spine_1"] = round(12.0 + (new_dist * 1.5), 1)
            else:
                logs.append("INVALID: Tuning irrelevant to current fault or missing 'value'.")
                reward = -0.1
                grading["score"] += reward
                grading["penalties"] += 1

        elif cmd == "RUN_MINI_ITERATION":
            if task == "hard":
                try:
                    start, end = map(int, tgt.split("-"))
                    fault_idx = int(fnode.split("_")[1]) % 16
                    new_range = end - start + 1
                    if start <= fault_idx <= end:
                        if new_range < self._cache["search_range"]:
                            # Reward for narrowing search space
                            reward = 0.15
                            grading["score"] += reward
                            grading["bonuses"] += 1
                            self._cache["search_range"] = new_range
                            logs.append(f"TRIAGE: Range {tgt} contains fault. Search space halved.")
                        
                        if start == end:
                            logs.append(f"TRIAGE_HIT: Fault confirmed on node under index {start}. Ready for DRAIN_TRAFFIC.")
                            reward += 0.2
                            grading["score"] += reward
                    else:
                        logs.append(f"TRIAGE: Range {tgt} is healthy. Source is elsewhere.")
                        # Still reward for ruling out half the space
                        if new_range < self._cache["search_range"]:
                             reward = 0.05
                             grading["score"] += reward
                             grading["bonuses"] += 1
                             self._cache["search_range"] = 16 - new_range # Implicit narrowing
                except Exception:
                    logs.append("INVALID: RUN_MINI_ITERATION requires 'start-end' target.")
                    reward = -0.1
                    grading["score"] += reward
                    grading["penalties"] += 1
            else:
                logs.append("INVALID: Diagnostic iteration irrelevant for this task.")
                reward = -0.1
                grading["score"] += reward
                grading["penalties"] += 1
        else:
            reward = -0.05 # Minor penalty for unknown/bad commands
            grading["score"] += reward
            grading["penalties"] += 1

        if self._cache["state"].step_count >= self.MAX_ATTEMPTS and not done:
            logs.append("SLA_BREACH: Timeout limit reached.")
            grading["status"] = "failed"
            done = True
            reward = -0.5
            grading["score"] += reward

        # Prevent negative total score theoretically, but standard RL handles negatives
        return self._get_obs(done, round(reward, 2))

    @property
    def state(self) -> State:
        return self._cache["state"]

    def _get_obs(self, done: bool, reward: float) -> NetweaverSreObservation:
        info_copy = self._cache["grading_info"].copy()
        info_copy["score"] = round(info_copy["score"], 2)
        
        return NetweaverSreObservation(
            done=done,
            reward=reward,
            queue_depths=self._cache["queue_depths"].copy(),
            gradient_variances=self._cache["gradient_vars"].copy(),
            hardware_logs=self._cache["logs"][-6:],
            system_health=max(0.0, 1.0 - (len(self._cache["drained_nodes"]) * 0.1)),
            grading_info=info_copy
        )
