# 🧠 LifeLens — Global Agent Upgrade Specification

This document defines how **all agents in LifeLens** must be upgraded so they appear:

- autonomous
- adaptive
- Qdrant-centric
- fault-tolerant
- observable
- judge-credible

This applies to:

✔ Ask-LifeLens agents  
✔ Ingestion agents  
✔ Trigger agents  
✔ Mood analytics agents  
✔ Summary agents  
✔ Dashboard agents  

---

# 🎯 What Makes Agents “Real”

Judges implicitly test whether:

- agents decide when to retrieve
- retries exist
- failures are graceful
- tools are invoked conditionally
- plans are structured
- traces are visible
- decisions persist
- Qdrant is central

If any are missing → system feels scripted.

---

# 🧠 Fix #1 — Unified Planner Schema (MANDATORY)

All planners must output **strict JSON** using this schema.

```json
{
  "intent": "memory_recall | ingestion | analytics | summary | trigger_scan",
  "needs_retrieval": true,
  "temporal_scope": "last_week | last_month | custom",
  "entities": ["John"],
  "modalities": ["image", "audio", "text", "video"],
  "confidence_threshold": 0.75,
  "fallback": "ask_caretaker | notify | ignore",
  "trigger_if_missing": true,
  "max_retries": 2
}
````

No free-text plans.

All downstream agents depend on this structure.

---

# 🔁 Fix #2 — Retry & Replanning Loop (GLOBAL)

All orchestrators must support this pattern:

```
Planner → Retriever → Critic
          ↓
       FAIL?
          ↓
Planner.replan() → Retriever → Critic
          ↓
       FAIL?
          ↓
Trigger Agent
```

---

## 🔧 Orchestrator Contract

```python
attempt = 0

while attempt <= plan["max_retries"]:

    if plan["needs_retrieval"]:
        results = retriever.search(plan)

    verdict = critic.evaluate(results)

    if verdict == "OK":
        break

    plan = planner.replan(plan, verdict)
    attempt += 1

if verdict != "OK":
    trigger_agent.handle_failure(...)
```

This loop is **non-negotiable**.

---

# 🧠 Fix #3 — Log Every Decision to Qdrant

Create / reuse:

```
collection: agent_decisions
```

Payload:

```json
{
  "patient_id": "p123",
  "agent": "planner",
  "plan": {...},
  "verdict": "RETRY",
  "attempt": 1,
  "timestamp": "2026-02-08T11:00:00Z"
}
```

Agents must write:

* initial plans
* replans
* critic verdicts
* trigger fires
* failures

Qdrant becomes **meta-memory**.

---

# 🧠 Fix #4 — UI Trace Panel (ALL FLOWS)

Every major agent run must expose:

---

## 🧠 Agent Reasoning

* Planner Plan
* Retrieval Count
* Critic Verdict
* Retry Attempts
* Trigger Fired?
* Timestamp

---

Streamlit Implementation:

Expandable accordion:

```
▶ Agent Reasoning
```

Only shown to caretakers/admin.

---

# 🧠 Fix #5 — Planner Must Gate Tools

No unconditional execution.

❌ BAD:

```python
plan = planner(...)
retriever(...)
```

✅ GOOD:

```python
plan = planner(...)

if plan["needs_retrieval"]:
    results = retriever.search(plan)

if verdict == "RETRY":
    ...
```

Every tool invocation must be justified by plan.

---

# 🧠 Fix #6 — Critic Standard Verdict Enum

Critic outputs must be one of:

```
OK
RETRY
NOT_ENOUGH_EVIDENCE
SUGGEST_TRIGGER
IGNORE
```

No prose.

---

# 🧠 Fix #7 — Trigger Agent Contract

Trigger Agent fires only if:

* verdict == NOT_ENOUGH_EVIDENCE
* verdict == SUGGEST_TRIGGER
* risk_score > threshold

All trigger decisions logged to Qdrant.

---

# 🧠 Fix #8 — Apply To All Agent Types

These rules apply to:

| Area          | Agents                                      |
| ------------- | ------------------------------------------- |
| Chat          | Planner / Retriever / Critic / Trigger      |
| Upload        | Ingestion Planner / Vision / Audio / Critic |
| Mood          | Analytics / Critic / Trigger                |
| Dashboard     | Analytics / Summary                         |
| Family Portal | Summary / Critic                            |
| Hygiene       | Cleanup / Trigger                           |

No exceptions.

---

# 🧠 Qdrant Centrality Rule

All agents must:

* read from Qdrant
* write results to Qdrant
* log decisions to Qdrant
* store feedback to Qdrant

No in-memory-only flows.

---

# 🧪 Acceptance Tests

System passes only if:

* [ ] plans stored in Qdrant
* [ ] retries executed
* [ ] verdict enums enforced
* [ ] UI shows traces
* [ ] triggers gated
* [ ] no forced retrieval
* [ ] logs persisted
* [ ] Qdrant queried dynamically

---

# 🎬 Demo Must Show

1️⃣ failed query
2️⃣ critic rejects
3️⃣ replan
4️⃣ second retrieval
5️⃣ still fails
6️⃣ ntfy trigger
7️⃣ Qdrant logs
8️⃣ UI trace visible

---

# 🏁 Summary

This upgrade ensures LifeLens agents:

✔ autonomous
✔ retry capable
✔ Qdrant-centered
✔ observable
✔ grounded
✔ finals-credible

---
