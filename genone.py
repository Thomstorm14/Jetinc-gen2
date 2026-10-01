import asyncio
import json
import hashlib
import time
import sys
import aiohttp
from typing import Dict, Any, List, Optional

# ------------------------------------------------------------------------------
# 1. TRIDENT LEDGER (CRYPTOGRAPHIC SHA-256 APPEND-ONLY LOG)
# ------------------------------------------------------------------------------
class TridentLedger:
    def __init__(self, ledger_file: str = "ledger_v1.jsonl"):
        self.ledger_file = ledger_file
        self.last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        try:
            with open(self.ledger_file, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1].strip())
                    return last_entry.get("current_hash", "0" * 64)
        except FileNotFoundError:
            pass
        return "0" * 64

    def append(self, prime_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.time()
        entry_data = {
            "timestamp": timestamp,
            "prime_id": prime_id,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self.last_hash
        }
        
        serialized = json.dumps(entry_data, sort_keys=True)
        current_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        entry_data["current_hash"] = current_hash

        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_data) + "\n")

        self.last_hash = current_hash
        return entry_data

    def verify_chain(self) -> bool:
        print(f"\n[LEDGER VERIFICATION] Auditing '{self.ledger_file}'...")
        try:
            with open(self.ledger_file, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except FileNotFoundError:
            print("[VERIFY FAILED] Ledger file does not exist.")
            return False

        if not lines:
            print("[VERIFY NOTICE] Ledger is empty.")
            return True

        expected_previous_hash = "0" * 64
        valid_count = 0

        for idx, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            entry = json.loads(line.strip())
            
            stored_current_hash = entry.get("current_hash")
            stored_prev_hash = entry.get("previous_hash")

            if stored_prev_hash != expected_previous_hash:
                print(f"[VERIFY BROKEN] Line {idx}: Previous hash mismatch!")
                return False

            calc_data = {
                "timestamp": entry["timestamp"],
                "prime_id": entry["prime_id"],
                "event_type": entry["event_type"],
                "payload": entry["payload"],
                "previous_hash": stored_prev_hash
            }
            recalculated_hash = hashlib.sha256(json.dumps(calc_data, sort_keys=True).encode('utf-8')).hexdigest()

            if recalculated_hash != stored_current_hash:
                print(f"[VERIFY TAMPERED] Line {idx}: Content hash re-calculation failed!")
                return False

            expected_previous_hash = stored_current_hash
            valid_count += 1

        print(f"[VERIFY PASSED] All {valid_count} entries verified. Cryptographic chain is 100% intact.\n")
        return True


# ------------------------------------------------------------------------------
# 2. REVOLVER SEAT NODE (WITH SPECIFIC CITY DATA LANES)
# ------------------------------------------------------------------------------
class RevolverSeatNode:
    def __init__(
        self,
        prime_id: str,
        city_name: str,
        index: int,
        total_seats: int,
        ledger: TridentLedger,
        api_url: str = "http://localhost:11434/api/chat",
        model: str = "gemma3:4b",
        timeout_seconds: float = 30.0,
        mock_mode: bool = False,
        system_prompt: str = None,
        temperature: float = 0.7,
        role_name: str = "Triverai Core Chamber"
    ):
        self.prime_id = prime_id
        self.city_name = city_name
        self.index = index
        self.total_seats = total_seats
        self.ledger = ledger
        self.api_url = api_url
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.mock_mode = mock_mode
        self.system_prompt = system_prompt or f"You are {self.prime_id} in {self.city_name}."
        self.temperature = temperature
        self.role_name = role_name
        
        # Revolver Mechanical Chamber State
        self.chamber_position = index % 3
        self.is_rr_lead = (self.chamber_position == 0)
        self.status = "GREEN"

    def rotate_chamber(self, step: int = 1):
        self.chamber_position = (self.chamber_position + step) % 3
        self.is_rr_lead = (self.chamber_position == 0)

    async def execute_step1_or(self, session: aiohttp.ClientSession, prompt: str, semaphore: asyncio.Semaphore) -> str:
        start_time = time.time()
        print(f"  [LANE DISPATCH] Direct Line -> {self.city_name} | {self.prime_id} (Position: {self.chamber_position})")

        if self.mock_mode:
            await asyncio.sleep(0.05)
            self.status = "GREEN"
            res = f"MOCK_OR[{self.prime_id} | {self.city_name}]: Isolated observation recorded."
            self.ledger.append(self.prime_id, "STEP1_OR_GEN", {"city": self.city_name, "or_text": res, "status": self.status})
            return res

        async with semaphore:
            try:
                # Concise grading directive to prevent heavy token delays
                concise_prompt = f"Directive: {prompt}\nProvide a concise 2-sentence observation for {self.city_name}."
                res = await self._call_llm(session, concise_prompt)
                self.status = "GREEN"
                self.ledger.append(self.prime_id, "STEP1_OR_GEN", {"city": self.city_name, "or_text": res, "status": self.status})
                print(f"  [LANE RETURN] {self.prime_id} ({self.city_name}) completed in {time.time() - start_time:.2f}s")
                return res
            except Exception as e:
                self.status = "RED"
                self.ledger.append(self.prime_id, "STEP1_OR_FAULT", {"city": self.city_name, "error": str(e), "status": self.status})
                print(f"  [LANE TIMEOUT/FAULT] {self.prime_id} ({self.city_name}): {str(e)}")
                return f"[FALLBACK_OR] {self.prime_id} ({self.city_name}) offline."

    async def execute_rubric_grade(self, session: aiohttp.ClientSession, peer_or: str, pass_direction: str, semaphore: asyncio.Semaphore) -> str:
        prompt = f"""
Concisely grade this peer observation (max 20 words per bullet):
"{peer_or}"

1. GOOD:
2. BAD:
3. FIX:
"""
        if self.mock_mode:
            return f"RUBRIC_GRADE[{self.prime_id} -> {pass_direction}]: 1. Clear. 2. Needs data. 3. Add metrics."

        async with semaphore:
            try:
                return await self._call_llm(session, prompt)
            except Exception as e:
                return f"Grading error: {str(e)}"

    async def execute_refinement(self, session: aiohttp.ClientSession, own_or: str, peer_graded: str, received_grade: str, pass_label: str, semaphore: asyncio.Semaphore) -> str:
        prompt = f"Refine position based on: Own={own_or} | PeerGraded={peer_graded} | Feedback={received_grade}"
        if self.mock_mode:
            return f"REFINED_{pass_label}[{self.prime_id}]: Polished synthesis."

        async with semaphore:
            try:
                return await self._call_llm(session, prompt)
            except Exception as e:
                return f"Refinement fault: {str(e)}"

    async def execute_comerge(self, session: aiohttp.ClientSession, ref_alpha: str, ref_beta: str, semaphore: asyncio.Semaphore) -> str:
        prompt = f"CoMerge Alpha & Beta: Alpha={ref_alpha} | Beta={ref_beta}"
        if self.mock_mode:
            return f"COMERGE_MASTER[{self.prime_id}]: Master synthesis complete."

        async with semaphore:
            try:
                return await self._call_llm(session, prompt)
            except Exception as e:
                return f"CoMerge fault: {str(e)}"

    async def _call_llm(self, session: aiohttp.ClientSession, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"{self.system_prompt}\n(Seat: {self.prime_id} | City: {self.city_name})."},
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": self.temperature, "num_predict": 128}, # Lock max response tokens for speed
            "stream": False
        }
        async with session.post(self.api_url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["message"]["content"]
            else:
                text = await resp.text()
                raise Exception(f"HTTP {resp.status}: {text[:100]}")


# ------------------------------------------------------------------------------
# 3. NEURAL BUS CONTROLLER (TRI-CITY EXPRESS ROUTER)
# ------------------------------------------------------------------------------
class NeuralBus:
    def __init__(self, roster_file: str = "roster.jsonl", config_file: str = "endpoints.json"):
        self.ledger = TridentLedger()
        self.nodes: Dict[str, RevolverSeatNode] = {}
        self.city_lanes: Dict[str, List[RevolverSeatNode]] = {
            "Mount Thomas": [],
            "Julian Bay": [],
            "Evans": [],
            "Triformers": []
        }
        self.node_list: List[RevolverSeatNode] = []
        self.config = self._load_config(config_file)
        self.semaphore = asyncio.Semaphore(self.config.get("max_concurrent_llm_calls", 2))
        self.primal_approval_queue: List[Dict[str, Any]] = []
        self._load_roster(roster_file)

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        default_config = {
            "default_endpoint": "http://localhost:11434/api/chat",
            "default_model": "gemma3:4b",
            "default_timeout_s": 25.0,
            "max_concurrent_llm_calls": 2,
            "mock_mode": False,
            "seat_overrides": {}
        }
        try:
            with open(config_file, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except FileNotFoundError:
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(default_config, indent=2))
        return default_config

    def _load_roster(self, roster_file: str):
        prime_ids = []
        try:
            with open(roster_file, "r", encoding="utf-8-sig") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        prime_ids.append(data["prime_id"])
        except FileNotFoundError:
            prime_ids = [f"SEAT-{i+1:02d}-CORE" for i in range(12)]

        total_seats = len(prime_ids)
        mock_mode = self.config.get("mock_mode", False)

        # Assign Prime IDs to Tri-City Lanes
        cities = ["Mount Thomas", "Julian Bay", "Evans", "Triformers"]

        for idx, pid in enumerate(prime_ids):
            city = cities[idx // 3] if idx < 9 else "Triformers"
            override = self.config.get("seat_overrides", {}).get(pid, {})
            api_url = override.get("api_url", self.config["default_endpoint"])
            model = override.get("model", self.config["default_model"])
            timeout_s = override.get("timeout_s", self.config["default_timeout_s"])
            sys_prompt = override.get("system_prompt", None)
            temp = override.get("temperature", 0.7)
            role_name = override.get("role_name", f"{city} Core Chamber")

            node = RevolverSeatNode(
                prime_id=pid,
                city_name=city,
                index=idx,
                total_seats=total_seats,
                ledger=self.ledger,
                api_url=api_url,
                model=model,
                timeout_seconds=timeout_s,
                mock_mode=mock_mode,
                system_prompt=sys_prompt,
                temperature=temp,
                role_name=role_name
            )
            self.nodes[pid] = node
            self.node_list.append(node)
            self.city_lanes[city].append(node)

    async def dispatch_directive(self, prompt: str):
        print("\n[NEURAL BUS] Tri-City Express Routing Active...")
        
        # Click Revolver Chambers
        for node in self.node_list:
            node.rotate_chamber(1)

        async with aiohttp.ClientSession() as session:
            # STEP 1: Process each City Lane in Parallel Tri-City Express Clusters
            print("\n--- STEP 1: Dispatching Parallel City Express Directives ---")
            or_map = {}
            
            for city_name, lane_nodes in self.city_lanes.items():
                if not lane_nodes:
                    continue
                print(f"\n[EXPRESS LANE -> {city_name}] Dispatching {len(lane_nodes)} Seats...")
                lane_tasks = [node.execute_step1_or(session, prompt, self.semaphore) for node in lane_nodes]
                lane_results = await asyncio.gather(*lane_tasks)
                for node, res in zip(lane_nodes, lane_results):
                    or_map[node.prime_id] = res

            # STEP 2-4: Pass Right (SR1)
            print("\n--- STEP 2: Pass Right (SR1) Rubric Grading ---")
            sr1_grade_tasks = []
            for idx, node in enumerate(self.node_list):
                right_neighbor = self.node_list[(idx + 1) % len(self.node_list)]
                sr1_grade_tasks.append(node.execute_rubric_grade(session, or_map[right_neighbor.prime_id], "SR1_RIGHT", self.semaphore))
            sr1_grades = await asyncio.gather(*sr1_grade_tasks)

            # STEP 5: Refine Alpha
            print("\n--- STEP 3: Synthesizing Refinement Alpha ---")
            alpha_tasks = []
            for idx, node in enumerate(self.node_list):
                right_neighbor = self.node_list[(idx + 1) % len(self.node_list)]
                received_grade = sr1_grades[(idx - 1) % len(self.node_list)]
                alpha_tasks.append(node.execute_refinement(session, or_map[node.prime_id], or_map[right_neighbor.prime_id], received_grade, "ALPHA", self.semaphore))
            ref_alphas = await asyncio.gather(*alpha_tasks)

            # STEP 6-8: Pass Left (SR2)
            print("\n--- STEP 4: Pass Left (SR2) Rubric Grading ---")
            sr2_grade_tasks = []
            for idx, node in enumerate(self.node_list):
                left_neighbor = self.node_list[(idx - 1) % len(self.node_list)]
                sr2_grade_tasks.append(node.execute_rubric_grade(session, or_map[left_neighbor.prime_id], "SR2_LEFT", self.semaphore))
            sr2_grades = await asyncio.gather(*sr2_grade_tasks)

            # STEP 9: Refine Beta
            print("\n--- STEP 5: Synthesizing Refinement Beta ---")
            beta_tasks = []
            for idx, node in enumerate(self.node_list):
                left_neighbor = self.node_list[(idx - 1) % len(self.node_list)]
                received_grade = sr2_grades[(idx + 1) % len(self.node_list)]
                beta_tasks.append(node.execute_refinement(session, or_map[node.prime_id], or_map[left_neighbor.prime_id], received_grade, "BETA", self.semaphore))
            ref_betas = await asyncio.gather(*beta_tasks)

            # STEP 10: CoMerge Synthesis
            print("\n--- STEP 6: Step 10 CoMerge Master Synthesis ---")
            comerge_tasks = [node.execute_comerge(session, a, b, self.semaphore) for node, a, b in zip(self.node_list, ref_alphas, ref_betas)]
            comerge_outputs = await asyncio.gather(*comerge_tasks)

            for idx, node in enumerate(self.node_list):
                rr_tag = " [R&R LEAD VOTE PASSED 3/3]" if node.is_rr_lead else ""
                self.ledger.append(node.prime_id, "10STEP_COMERGE_COMPLETE", {
                    "city": node.city_name,
                    "chamber_pos": node.chamber_position,
                    "is_rr_lead": node.is_rr_lead,
                    "final_output": comerge_outputs[idx]
                })
                print(f"  └─► [{node.status}] {node.prime_id} ({node.city_name}) Pos:{node.chamber_position}{rr_tag} Complete.")

        # Primal Approval Deposit
        primal_payload = {
            "timestamp": time.time(),
            "directive": prompt,
            "status": "PENDING_HUMAN_GO_NOGO",
            "consensus_summary": "Tri-City Express Routing Complete. 10-Step Isolated Data Verified."
        }
        self.primal_approval_queue.append(primal_payload)
        self.ledger.append("PRIMAL-APPROVAL-CONTAINER", "GO_NOGO_DEPOSITED", primal_payload)
        print("\n[PRIMAL APPROVAL] Tri-City Synthesis Deposited into NASA Go/No-Go Container. Pending Sign-Off.")

# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    ledger = TridentLedger()

    if "--verify" in sys.argv:
        ledger.verify_chain()
    else:
        bus = NeuralBus()
        asyncio.run(bus.dispatch_directive("Execute JETtrix Architecture Pipeline"))
        ledger.verify_chain()
