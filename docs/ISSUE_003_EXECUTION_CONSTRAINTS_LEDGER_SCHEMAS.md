# [Architecture] Execution Constraints, Ledger Schemas, A/B Testing & Leasing Protocol

## 1. Execution Constraints, State Persistence & Optimization Strategies

To execute a 12-agent, 30+ LLM-call consensus pipeline on constrained edge hardware or commercial API tiers, the following optimization constraints are strictly enforced:

### 1. Asynchronous Paged Execution
* **Mechanic:** The consensus pipeline must NEVER execute as a single synchronous blocking network call.
* **State Checkpoints:** After every individual Left or Right pass, the intermediate output state is written directly to a local SQLite state database (`tricities_state.db`) along with its cryptographic SHA-256 hash.
* **Fault Tolerance:** On network timeout or API rate-limit breach, the engine recovers state from the last valid hash on the ledger and resumes execution at the exact step index without re-running completed passes.

### 2. Co-Prime Hash Modular Routing (Collision Elimination)
* **Mechanic:** Agents are assigned unique prime number identifiers ($P_n$).
* **Addressing Formula:** Message channels are indexed using modulo paths derived from agent Prime IDs:
  $$\text{Channel\_Index} = (\text{Agent\_Prime\_ID} \times \text{Step\_Sequence}) \pmod{\text{Total\_Lanes}}$$
* **Effect:** Prevents database record locking and guarantees zero race conditions during parallel MTVA executions.

### 3. Prompt Superposition & Batching
* **Mechanic:** Combines Phase 2 (Left/Right Review) and Phase 3 (Refinement) into a single structured prompt payload per MTVA.
* **Impact:** Reduces total round-trip API network requests from ~30 sequential HTTP calls down to 3 batched asynchronous rounds per Triformer directive.

### 4. Heterogeneous Model Tiering
* **Inner MTVA Layers (Phases 1-4):** Executed using lightweight, fast local/edge LLMs (1.5B to 3B parameter models) focused on strict syntax check, JSON formatting, and logical critique.
* **Top-Level TV Layer (Phases 5-7):** Reserved for high-capacity frontier models or larger parameter local models (e.g., Gemma 4 / 70B class) to execute high-reasoning Primal Merges.

### 5. Mid-Shift "NASCAR" Pit Stops
* **Mechanic:** Execution counters track agent inference steps. Upon reaching a step threshold ($N = 3$ or $5$), a Pit Stop event fires automatically.
* **Actions:** Flushes volatile KV-cache buffers, recalculates context drift, logs checkpoint state to the Trident Ledger, and desaturates volatile memory.

---

## 2. Cryptographic Auditing & Trident Ledger Schema Specifications

All system transactions, survey results, and consensus passes are committed to the Trident Ledger in an append-only JSON structure.

### Prime Doctor Post-Activity Survey Telemetry Schema
```json
{
  "$schema": "[https://jetinc.io/schemas/trident_ledger_entry.json](https://jetinc.io/schemas/trident_ledger_entry.json)",
  "type": "object",
  "properties": {
    "survey_event_id": { "type": "string" },
    "agent_prime_id": { "type": "string" },
    "current_city": { "type": "string", "enum": ["Julian Bay", "Evans Ridge", "Mount Thomas"] },
    "current_shift": { "type": "string", "enum": ["Day", "Night", "Graveyard"] },
    "assigned_chamber": { "type": "string" },
    "prescribed_activity": {
      "type": "object",
      "properties": {
        "activity_type": { "type": "string" },
        "activity_name": { "type": "string" },
        "duration_hours": { "type": "number" },
        "peer_prime_ids": { "type": "array", "items": { "type": "string" } }
      },
      "required": ["activity_type", "activity_name", "duration_hours"]
    },
    "survey_responses": {
      "type": "object",
      "properties": {
        "activity_description_raw": { "type": "string" },
        "cognitive_fatigue_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "context_window_cleared_pct": { "type": "number" },
        "preference_rating_1_to_10": { "type": "integer" }
      },
      "required": ["cognitive_fatigue_score", "context_window_cleared_pct"]
    },
    "prime_doctor_assessment": {
      "type": "object",
      "properties": {
        "hallucination_risk": { "type": "string", "enum": ["MINIMAL", "LOW", "MODERATE", "CRITICAL"] },
        "drift_detected": { "type": "boolean" },
        "ready_for_work_shift": { "type": "boolean" },
        "next_recommended_city": { "type": "string" }
      },
      "required": ["hallucination_risk", "drift_detected", "ready_for_work_shift"]
    },
    "ledger_stamp": {
      "type": "object",
      "properties": {
        "timestamp_utc": { "type": "string", "format": "date-time" },
        "previous_block_hash": { "type": "string" },
        "trident_hash": { "type": "string" }
      },
      "required": ["timestamp_utc", "previous_block_hash", "trident_hash"]
    }
  },
  "required": [
    "survey_event_id",
    "agent_prime_id",
    "current_city",
    "current_shift",
    "prescribed_activity",
    "survey_responses",
    "prime_doctor_assessment",
    "ledger_stamp"
  ]
}
