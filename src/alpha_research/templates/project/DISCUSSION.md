# Discussion — {{project_id}}

> This file is the durable record of every discussion between the
> researcher and the agents working on this project. Whenever the
> researcher steers, corrects, or clarifies something, append an entry
> here so future agent invocations have the conversational context that
> disappeared from the transient chat buffer.

## How to use this file

- One entry per discussion (roughly a session — not per message).
- Newest entries go at the bottom, with an ISO-8601 UTC timestamp header.
- Capture the **question/ask**, the **conclusion** reached, and any
  **open threads** the next session should pick up.
- When a discussion results in a decision that changes a design choice,
  also reference the relevant file (e.g. `PROJECT.md § Scope`) so the
  reason lives next to the choice.

## Entry template

```markdown
## {YYYY-MM-DDTHH:MM:SSZ} — {short topic}

**Participants**: researcher, {agents/skills involved}

**Context**: what prompted the discussion (stage, recent finding, blocker).

**Ask**: what the researcher wanted to resolve.

**Outcome**:
- Decision / conclusion / reframing.
- Affected files / records / state.

**Follow-ups**:
- [ ] open thread 1
- [ ] open thread 2
```

---

<!-- Discussion entries are appended below this line. Most recent LAST. -->
