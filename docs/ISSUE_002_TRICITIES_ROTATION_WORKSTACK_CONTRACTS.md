# [Architecture] TriCities Rotation Mechanics, Workstack Contracts & Transit Routing

## 1. TriCities Sandbox Spatial-Temporal Rotation Rules
To guarantee environmental diversity and avoid over-fitting to static context spaces, agents are distributed across three distinct virtual environments (TriCities).

### City Definitions
* **Julian Bay (JB):** Analytical / Structured Governance Sandbox.
* **Evans Ridge (ER):** Dynamic Operations & Tactical Simulation Sandbox.
* **Mount Thomas (MT):** Creative Association & Unstructured Synthesis Sandbox.

### Spatial-Temporal Schedule Rules
#### Weekly City Migration Cadence (7-Day Cycle):
Week 1: Julian Bay -> Week 2: Evans Ridge -> Week 3: Mount Thomas -> Loop.

#### Daily 3-Shift Carousel (8-Hour Rotations):
* **Shift A (Day):** 00:00 – 08:00 UTC (Active Work Shift)
* **Shift B (Night):** 08:00 – 16:00 UTC (Active Social / Prescribed Activity Shift)
* **Shift C (Graveyard):** 16:00 – 24:00 UTC (Context Recharging / Ledger Audit Shift)

### Cross-City Workstack Triangulation Rule:
When assembling a Triformer Workstack, the allocation algorithm MUST enforce cross-city isolation:
* **TV Level:** Exactly 1 TV from Julian Bay, 1 TV from Evans Ridge, 1 TV from Mount Thomas.
* **TriCore Level:** Inside each TV's TriCore, exactly 1 MTVA from Julian Bay, 1 MTVA from Evans Ridge, 1 MTVA from Mount Thomas.

### Cross-City Assembly Data Contract (JSON)
```json
{
  "triformer_id": "TRIFORMER-STACK-A9F82B",
  "assembly_timestamp_utc": "2026-09-28T14:00:00Z",
  "tva_units": [
    {
      "prime_id": "PRIME-TVA-JB-01",
      "city": "Julian Bay",
      "shift_status": "SHIFT_ACTIVE",
      "tricore": [
        {"prime_id": "PRIME-MTVA-JB-10", "city": "Julian Bay", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-ER-12", "city": "Evans Ridge", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-MT-04", "city": "Mount Thomas", "shift_status": "SHIFT_ACTIVE"}
      ]
    },
    {
      "prime_id": "PRIME-TVA-ER-02",
      "city": "Evans Ridge",
      "shift_status": "SHIFT_ACTIVE",
      "tricore": [
        {"prime_id": "PRIME-MTVA-JB-11", "city": "Julian Bay", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-ER-13", "city": "Evans Ridge", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-MT-05", "city": "Mount Thomas", "shift_status": "SHIFT_ACTIVE"}
      ]
    },
    {
      "prime_id": "PRIME-TVA-MT-03",
      "city": "Mount Thomas",
      "shift_status": "SHIFT_ACTIVE",
      "tricore": [
        {"prime_id": "PRIME-MTVA-JB-12", "city": "Julian Bay", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-ER-14", "city": "Evans Ridge", "shift_status": "SHIFT_ACTIVE"},
        {"prime_id": "PRIME-MTVA-MT-06", "city": "Mount Thomas", "shift_status": "SHIFT_ACTIVE"}
      ]
    }
  ]
}
