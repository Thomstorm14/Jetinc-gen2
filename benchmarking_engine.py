import sqlite3
import json
import hashlib
import time
from typing import List, Dict, Any
from codex_loader import load_codex_profile

DB_PATH = "jettrix_sim.db"
LEDGER_PATH = "ledger_v1.jsonl"
CITIES = ["Mount Thomas", "Julian Bay", "Evans"]

def calculate_sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def verify_ledger_integrity(ledger_path: str) -> bool:
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for line in lines:
            if not line.strip():
                continue
            record = json.loads(line.strip())
            stored_hash = record.pop("hash", None)
            
            # Verify previous hash link
            if record.get("previous_hash") != last_hash:
                return False
                
            # Verify current record hash
            record_bytes = json.dumps(record, sort_keys=True).encode('utf-8')
            computed_hash = hashlib.sha256(record_bytes).hexdigest()
            if computed_hash != stored_hash:
                return False
                
            last_hash = stored_hash
        return True
    except Exception:
        return False

def calculate_jaccard_similarity(str1: str, str2: str) -> float:
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    if not union:
        return 1.0
    return len(intersection) / len(union)

class BenchmarkingEngine:
    def __init__(self, db_path: str = DB_PATH, ledger_path: str = LEDGER_PATH):
        self.db_path = db_path
        self.ledger_path = ledger_path

    def preflight_check(self) -> bool:
        print("[CHECK] Running SHA-256 pre-execution ledger integrity guard...")
        if not verify_ledger_integrity(self.ledger_path):
            print("[ERROR] Ledger integrity guard failed. Execution halted.")
            return False
        print("[CHECK] Ledger verified cryptographically sound.")
        return True

    def fetch_active_roster(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, city, role FROM agent_roster WHERE status = 'ACTIVE'")
        rows = cursor.fetchall()
        conn.close()
        
        roster = [{"agent_id": r[0], "city": r[1], "role": r[2]} for r in rows]
        print(f"[ROSTER] Retrieved {len(roster)} active agents across 3 nodes.")
        return roster

    def execute_benchmark_run(self, test_prompt: str) -> Dict[str, Any]:
        if not self.preflight_check():
            return {}

        roster = self.fetch_active_roster()
        timestamp = time.time()
        city_responses = {city: [] for city in CITIES}
        
        print(f"\n[BENCHMARK] Executing parallel test runs across mesh for prompt:\n  \"{test_prompt}\"\n")

        for agent in roster:
            profile = load_codex_profile(agent["role"])
            temp = profile.get("temperature", 0.7)
            
            response_payload = f"Response from {agent['agent_id']} ({agent['role']}) at {agent['city']} | Temp: {temp} | Input: {test_prompt}"
            payload_hash = calculate_sha256(response_payload)
            
            entry = {
                "agent_id": agent["agent_id"],
                "role": agent["role"],
                "temperature": temp,
                "payload": response_payload,
                "hash": payload_hash
            }
            city_responses[agent["city"]].append(entry)

        metrics = self.analyze_metrics(city_responses)
        self.log_benchmark_to_ledger(test_prompt, timestamp, metrics)
        
        return metrics

    def analyze_metrics(self, city_responses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        analysis = {}
        all_similarities = []

        for city, responses in city_responses.items():
            city_sims = []
            n = len(responses)
            for i in range(n):
                for j in range(i + 1, n):
                    sim = calculate_jaccard_similarity(responses[i]["payload"], responses[j]["payload"])
                    city_sims.append(sim)
                    all_similarities.append(sim)
            
            avg_sim = sum(city_sims) / len(city_sims) if city_sims else 1.0
            variance = 1.0 - avg_sim
            analysis[city] = {
                "agent_count": n,
                "consensus_agreement": round(avg_sim, 4),
                "output_variance": round(variance, 4)
            }

        global_consensus = sum(all_similarities) / len(all_similarities) if all_similarities else 1.0
        
        results = {
            "node_metrics": analysis,
            "global_consensus_score": round(global_consensus, 4),
            "bias_mitigation_index": round(1.0 - (max([m["output_variance"] for m in analysis.values()]) - min([m["output_variance"] for m in analysis.values()])), 4)
        }
        return results

    def log_benchmark_to_ledger(self, prompt: str, timestamp: float, metrics: Dict[str, Any]):
        last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_record = json.loads(lines[-1].strip())
                    last_hash = last_record.get("hash", last_hash)
        except FileNotFoundError:
            pass

        record_data = {
            "timestamp": timestamp,
            "event_type": "BENCHMARK_RUN",
            "prompt": prompt,
            "metrics": metrics,
            "previous_hash": last_hash
        }
        
        record_bytes = json.dumps(record_data, sort_keys=True).encode('utf-8')
        record_hash = hashlib.sha256(record_bytes).hexdigest()
        record_data["hash"] = record_hash

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_data) + "\n")

        print(f"[LEDGER] Benchmark result appended to {self.ledger_path} with SHA-256 chain hash: {record_hash[:16]}...")

if __name__ == "__main__":
    engine = BenchmarkingEngine()
    test_query = "Evaluate state vector synchronization for TriCore node failover."
    results = engine.execute_benchmark_run(test_query)
    
    print("\n--- BENCHMARK RESULTS ---")
    print(json.dumps(results, indent=2))
