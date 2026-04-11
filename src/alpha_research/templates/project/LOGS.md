# LOGS

> The single append-only log for every change to this research project —
> both the researcher's weekly entries AND every automated agent revision.
> Doctrine §9.2: *"The log is non-negotiable: what you tried, expected,
> observed, concluded, what's next."*

This file has two sections:

1. **Agent revisions** — appended automatically by skills / pipelines
   (via `alpha_research.project.append_revision_log`). Each entry records
   the agent, the artifact it touched, the revision it made, and the
   result / feedback from downstream verification.
2. **Weekly log** — appended by the researcher (via
   `alpha-research project log`). One entry per week in the Tried /
   Expected / Observed / Concluded / Next format.

Both sections are append-only and chronological: most recent entries LAST.

---

## Agent revisions

<!-- Automated entries are appended below this marker.
Do NOT hand-edit inside this block — instead, write commentary in the
weekly log section and reference the revision timestamp. Each entry
follows the schema:

### {ISO-8601 UTC timestamp} — {agent/skill name}

- **Stage**: {project stage at time of revision}
- **Target**: {artifact / file / record the agent touched}
- **Revision**: {what the agent changed, concretely}
- **Result**: {what the downstream verifier / guard / metric reported}
- **Feedback**: {reviewer feedback, skill verdict, or error message}
-->

<!-- AGENT_REVISIONS_END -->

---

## Weekly log

Each entry follows the five-line structure:

- **Tried**: the action taken — experiment / code change / formalization attempt / literature dive
- **Expected**: what you predicted would happen BEFORE you ran it
- **Observed**: what actually happened — facts, not interpretation
- **Concluded**: the interpretation — what this means for the state machine (any backward triggers?)
- **Next**: the concrete next action

Calibration (§11.2 exercise 6) comes from tracking expected vs observed over time.

<!-- Weekly entries are appended below this line. Most recent LAST. -->
