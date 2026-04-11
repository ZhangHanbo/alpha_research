# Skills for Autonomous Robotics Research

A skills-only architecture for the alpha_research project. **Zero new tools.** Every capability a researcher needs is already reachable through Claude Code's built-in tools (`Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `WebSearch`, `WebFetch`, `Task`, `TodoWrite`, `NotebookEdit`) plus the existing `alpha_review` Python module at `../alpha_review`. The entire value of this project lives in the **skill recipes** — markdown files that encode the research-guideline and review-guideline knowledge as executable instructions for Claude.

---

## Part I. The Realization

Earlier drafts of this document proposed an MCP server with 5, 9, 11, or 19 custom tools. After repeated minimality passes, the right answer turned out to be simpler: **zero new tools**. Here is why.

### Everything a researcher does is already reachable

A robotics researcher's day consists of activities that fall cleanly into two buckets:

**Bucket 1 — activities the platform already handles**
Reading papers, writing code, running training scripts, launching simulators, querying wandb, running sympy checks, making plots, compiling LaTeX, git operations, searching the codebase, fetching web documentation. All of these are `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `WebSearch`, `WebFetch`.

**Bucket 2 — activities that need structured scholarly data or persistent memory**
Searching ArXiv / S2 / OpenAlex / Google Scholar for papers, traversing citation graphs, extracting full-text sections from PDFs with quality flags, persisting rubric evaluations and findings across sessions.

The first bucket is solved by Claude Code directly. The second bucket is solved by **`alpha_review`** — a Python module at `../alpha_review` that already has:
- `alpha_review.apis.search_all` — unified ArXiv + S2 + OpenAlex search with caching and rate limits
- `alpha_review.apis.s2_references` / `s2_citations` — citation graph
- `alpha_review.apis.unpaywall_pdf_url` — open-access PDF resolution
- `alpha_review.scholar.scholar_search_papers` — Google Scholar scraper
- `alpha_review.models.ReviewState` — SQLite-backed persistent store
- `alpha_review.sdk.run_plan` / `run_scope` / `run_search` / `run_read` / `run_write` — full survey lifecycle
- `alpha-review` CLI entry point — runs the whole survey pipeline from the shell

And the existing `alpha_research` codebase already has:
- `src/alpha_research/tools/paper_fetch.py::fetch_and_extract` — PDF → structured sections with quality flagging

**The Python is already written.** Building an MCP server to wrap these functions is pure indirection — it adds schemas, adapters, and maintenance burden without expanding capability.

### The right bridge is `Bash`, not MCP

Any Python function in `alpha_review` or `alpha_research` is reachable from a skill via one `Bash` call:

```bash
python -c "from alpha_review.apis import search_all; import json; print(json.dumps(search_all('tactile manipulation', limit_per_source=15), indent=2))"
```

or via a helper script the skill writes with `Write` and then runs with `Bash`:

```bash
python scripts/_tmp_search.py
```

or via the existing CLI:

```bash
alpha-review "scene representations for mobile manipulation" -o output/scene_repr
```

**`Bash` is the universal tool.** A skill's instruction text tells Claude exactly what Python to run; `Bash` executes it; stdout (structured as JSON) comes back as tool output. No MCP server, no JSON Schema duplication, no adapter layers.

### Persistent project memory is JSONL files, not a new database

The one genuine gap from the earlier analysis — "project-scoped structured memory for evaluations, findings, reviews, frontier snapshots" — is solved by **one JSONL file per record type** in the project's output directory:

```
output/<project>/
├── review.db                        # alpha_review's papers + themes (existing)
├── evaluations.jsonl                # our rubric scores (one line per evaluation)
├── findings.jsonl                   # our cross-paper findings
├── reviews.jsonl                    # our adversarial reviews
├── frontier.jsonl                   # our capability-frontier snapshots
└── research_log.md                  # human-authored daily log
```

Writing is `python -c "import json; open('output/x/evaluations.jsonl','a').write(json.dumps(rec)+'\n')"`. Reading with filters is `python -c "import json; recs = [json.loads(l) for l in open('...')]; print([r for r in recs if r['B.3']['score']>=4])"`. At research scale (hundreds of records, not millions), O(N) full scans are instant.

No schema migrations. No SQLite extension tables. No database libraries beyond what Python ships with. The researcher can inspect and edit files by hand.

### What the project delivers

With tools solved and memory solved, the project's entire deliverable is the **skills layer** — 12 `SKILL.md` files encoding the guideline knowledge as executable Claude recipes. That's where the research taste, the attack vectors, the rubric calibration, the venue thresholds, and the graduated pressure logic live. That's the actual value.

---

## Part II. The Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  .claude/skills/*/SKILL.md                                           │
│                                                                      │
│  The entire deliverable of this project. 12 markdown recipes         │
│  encoding research_guideline.md and review_guideline.md as           │
│  executable instructions for Claude.                                 │
│                                                                      │
│  Each skill tells Claude which Bash / Read / Write / Edit commands   │
│  to run, which alpha_review Python functions to invoke, how to       │
│  interpret the results, and what structured output to produce.       │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  Existing Python modules (no wrapping, no MCP)                       │
│                                                                      │
│  alpha_review/                                                       │
│    apis.py      search_all, s2_references, s2_citations,             │
│                 arxiv_search, openalex_search, unpaywall_pdf_url     │
│    scholar.py   scholar_search_papers                                │
│    models.py    ReviewState (SQLite for papers/themes/ideas)         │
│    sdk.py       run_plan/scope/search/read/write, run_survey         │
│    CLI          alpha-review "<query>" -o <dir>                      │
│                                                                      │
│  alpha_research/                                                     │
│    tools/paper_fetch.py   fetch_and_extract (PDF → sections)         │
│    agents/                ResearchAgent, ReviewAgent, etc.           │
│    models/                Review, Finding, Verdict dataclasses       │
│    metrics/               review_quality, convergence                │
│                                                                      │
│  All invoked from skills via `bash python -c "..."` or helper        │
│  script files written with `Write` and run with `Bash`.              │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  JSONL project records                                               │
│                                                                      │
│  output/<project>/{evaluations,findings,reviews,frontier}.jsonl      │
│                                                                      │
│  Append with `python -c "import json; open(...,'a').write(...)"`     │
│  Query with `python -c "import json; [... for l in open(...)]"`      │
│  No schema, no database, no migrations.                              │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  Claude Code built-in tools                                          │
│                                                                      │
│  Read, Write, Edit                — file I/O                         │
│  Bash                             — everything computational         │
│  Grep, Glob                       — codebase search                  │
│  WebSearch, WebFetch              — non-scholarly web                │
│  Task                             — subagent spawning                │
│  TodoWrite                        — in-session task tracking         │
│  NotebookEdit                     — Jupyter                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**No MCP server. No new tool definitions. No `.claude/.mcp.json` additions.**

---

## Part III. The Skill-Bash-Python Pattern

Every skill follows the same composition pattern. Here is the canonical shape before we look at individual skills.

### Pattern 1 — Inline Python via `bash python -c`

For short operations, the skill gives Claude a `Bash` command with an inline Python snippet:

```bash
python -c "
from alpha_review.apis import search_all
import json
results = search_all('tactile manipulation for deformable objects',
                     limit_per_source=15, year_lo=2023)
print(json.dumps([{'title': r['title'], 'year': r['year'],
                   'citationCount': r.get('citationCount', 0),
                   'doi': r.get('doi', ''), 'abstract': r.get('abstract', '')[:300]}
                  for r in results[:10]], indent=2))
"
```

Claude receives the JSON output on stdout, parses it naturally, and reasons over the structured records.

### Pattern 2 — Helper script via `Write` + `Bash`

For multi-step operations or anything longer than ~5 lines, the skill tells Claude to write a temporary Python script and execute it:

```
1. Write this file to `scripts/_evaluate.py`:
   ---
   from alpha_research.tools.paper_fetch import fetch_and_extract
   from alpha_review.apis import s2_paper_details
   import json, sys

   paper_id = sys.argv[1]
   content = fetch_and_extract(paper_id, extract_sections=True)
   meta = s2_paper_details(paper_id)
   print(json.dumps({
       "title": content.title,
       "sections": list(content.sections.keys()),
       "extraction_quality": content.extraction_quality.overall,
       "citation_count": meta.get("citationCount", 0) if meta else 0,
   }))
   ---
2. Run: `python scripts/_evaluate.py arxiv:2501.12345`
```

The script stays on disk (recoverable, debuggable) but the skill ensures Claude cleans it up after use or names it with a `_tmp_` prefix.

### Pattern 3 — Existing CLI via `Bash`

When `alpha_review`'s CLI covers the whole operation (literature surveys), the skill just invokes it:

```bash
alpha-review "contact-rich manipulation under uncertainty" -o output/contact_rich --yes
```

### Pattern 4 — JSONL append for persistent records

Writing a structured record to project memory:

```bash
python -c "
import json, time, uuid
rec = {
    'id': 'eval_' + uuid.uuid4().hex[:10],
    'paper_id': 'arxiv:2501.12345',
    'rubric_scores': {'B.1': {'score': 4, 'confidence': 'medium', 'evidence': [...]}, ...},
    'task_chain': {'task': '...', 'problem': '...', 'challenge': '...', 'approach': '...'},
    'significance_assessment': {...},
    'human_flags': ['formalization_quality'],
    'created_at': time.time(),
}
with open('output/my_project/evaluations.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
"
```

And reading with a filter:

```bash
python -c "
import json
records = [json.loads(l) for l in open('output/my_project/evaluations.jsonl')]
strong = [r for r in records if r['rubric_scores'].get('B.3', {}).get('score', 0) >= 4]
print(json.dumps(strong, indent=2))
"
```

This is all the persistent-memory infrastructure the project needs.

---

## Part IV. The 12 Skills

Each skill lives at `.claude/skills/<slug>/SKILL.md`. Below is the full specification for every skill: frontmatter, purpose, process, output format, honesty protocol, and references.

### Quick index

| # | Skill | Research stage | Primary guideline section |
|---|---|---|---|
| 1 | `literature-survey` | SIGNIFICANCE → all | research_guideline §5.2, research_plan SM-1..5 |
| 2 | `significance-screen` | SIGNIFICANCE | research_guideline §2.2 |
| 3 | `formalization-check` | FORMALIZE | research_guideline §2.4, §3.1 |
| 4 | `diagnose-system` | DIAGNOSE | research_guideline §2.4 empirical diagnosis |
| 5 | `challenge-articulate` | CHALLENGE | research_guideline §2.5, §2.7 |
| 6 | `method-survey` | APPROACH | research_guideline §2.7 |
| 7 | `experiment-audit` | VALIDATE | research_guideline §8, review_guideline §3.5 |
| 8 | `adversarial-review` | VALIDATE (self) | review_guideline Part III |
| 9 | `paper-evaluate` | all (per-paper) | research_guideline Appendix B |
| 10 | `concurrent-work-check` | APPROACH, VALIDATE | research_guideline §2.2, §2.6 |
| 11 | `gap-analysis` | SIGNIFICANCE, CHALLENGE | research_guideline §5.1 Axis 1 |
| 12 | `frontier-mapping` | SIGNIFICANCE | research_guideline §5.1 Axis 3 |

---

### Skill 1 — `literature-survey`

**Path:** `.claude/skills/literature-survey/SKILL.md`

```markdown
---
name: literature-survey
description: Run a systematic literature survey on a research topic. Uses
             alpha_review's SDK to plan, scope, search, read, and write a
             LaTeX survey with BibTeX and PDF. Then layers the
             research_guideline Appendix B rubric on top of the included
             papers. Use when the user asks for a "landscape survey",
             "literature review", or "map the field on X".
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Task
model: claude-sonnet-4-6
---

# Literature Survey

## When to use
Invoked when the researcher needs a systematic map of a subfield: who is
publishing what, which approaches exist, claimed results, where groups are
heading. Covers the SIGNIFICANCE stage of the research state machine and
supports all downstream stages.

## Process

### Phase A — Delegate to alpha_review for coverage

1. Sanitize the query into an output directory name:
   `output_dir = 'output/<sanitized_query>'`

2. Run the full alpha_review pipeline as one Bash call:
   ```bash
   alpha-review "<query>" -o <output_dir> --yes
   ```
   This executes PLAN → SCOPE → SEARCH/READ loop → WRITE and produces:
   - `<output_dir>/review.db` (SQLite: papers, themes, ideas)
   - `<output_dir>/review_grounded.tex` (LaTeX survey)
   - `<output_dir>/review_grounded.bib` (BibTeX)
   - `<output_dir>/review_grounded.pdf` (compiled PDF, if pdflatex available)
   - `<output_dir>/procedure.md` (pipeline trace)

3. Check that the survey completed:
   ```bash
   ls <output_dir>/review_grounded.tex && echo "survey ready"
   ```

### Phase B — Layer the alpha_research rubric

4. Pull the list of included papers:
   ```bash
   python -c "
   from alpha_review.models import ReviewState, PaperStatus
   import json
   state = ReviewState('<output_dir>/review.db')
   papers = state.get_papers(status=PaperStatus.INCLUDED)
   print(json.dumps([{'id': p.id, 'title': p.title, 'doi': p.doi,
                      'abstract': p.abstract[:300]} for p in papers], indent=2))
   state.close()
   "
   ```

5. For each included paper (batch of 10 at a time, use Task for parallelism):
   - Invoke the `paper-evaluate` skill with the paper_id
   - Paper-evaluate writes an evaluation record to
     `<output_dir>/evaluations.jsonl`

6. Once evaluations are written, synthesize an alpha_research report that
   adds what alpha_review does not:
   - Approach taxonomy grouped by challenge type (§2.7 table)
   - Capability frontier (reliable / sometimes / can't-yet)
   - Recurring gaps — invoke the `gap-analysis` skill
   - Significance assessment with human_flags everywhere Hamming-testable

   Write the synthesis to `<output_dir>/alpha_research_report.md`.

### Phase C — Deliver

7. Summarize for the user:
   - Number of papers surveyed and included
   - Path to LaTeX / PDF
   - Path to alpha_research rubric report
   - Top 3 gaps identified
   - Any papers flagged with extraction_quality < "medium" that need
     human verification

## Output format

A final message to the user containing:
- `tex_path`, `bib_path`, `pdf_path`, `report_path`
- `papers_total`, `papers_included`
- Top gaps and top 5 highest-scored papers by B.1 (significance)
- Any human_flags that must be reviewed

## Honesty protocol

You cannot independently judge the significance of a research direction
(Hamming test). Your added value over alpha_review is consistent rubric
application and adversarial cross-check, not a new judgment layer. Flag
all significance assessments as requiring human confirmation.

## References

- `guidelines/doctrine/research_guideline.md` — Appendix B rubric, §5.2 process
- `guidelines/spec/research_plan.md` — SM-1 through SM-5 state machines
- `../alpha_review/alpha_review/sdk.py` — run_survey pipeline
- `../alpha_review/alpha_review/apis.py` — search and metadata APIs
```

---

### Skill 2 — `significance-screen`

**Path:** `.claude/skills/significance-screen/SKILL.md`

```markdown
---
name: significance-screen
description: Evaluate whether a research problem is worth pursuing. Apply
             the Hamming, Consequence, Durability, and Compounding tests
             from research_guideline §2.2. Use when the user asks "is this
             problem worth working on", "should I work on X", or "is this
             significant".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
---

# Significance Screen

## When to use

The researcher proposes a candidate problem and asks whether it's worth
committing months or years to. Maps to the SIGNIFICANCE stage of the
research state machine — the most commonly-skipped step in average
research. Your job is to ensure it does not get skipped.

## The four tests (from research_guideline.md §2.2)

### 1. Hamming Test — necessity
- Is the problem on the researcher's Hamming list of important unsolved
  problems?
- Is there a reasonable attack? Importance requires BOTH (a) the solution
  would matter AND (b) a viable path exists.
- Would solving it generate MORE interest over time, not less?
  (Sim-to-real for rigid pick-and-place is becoming LESS interesting as
  foundation models improve. Contact-rich manipulation under uncertainty
  is becoming MORE interesting.)

### 2. Consequence Test — impact
- If magically solved overnight, what concretely changes?
- Name a specific downstream system, capability, or understanding that
  improves. "Other researchers would cite us" is NOT an answer. Demand
  concrete systems, capabilities, or understandings.

### 3. Durability Test
- Will a 10x bigger model or 10x more data trivially solve this in 24
  months? Does it require structural insight that resists scaling?
- Problems that resist scaling are good. Problems scaling will kill are
  bad bets.

### 4. Compounding Test — portfolio
- Does solving this enable OTHER research?
- High-value: representations that transfer, formal frameworks, data
  infrastructure, safety guarantees.
- Low-value: task-specific controllers, benchmark tweaks, marginal
  accuracy improvements.

## Process

### Step 1 — Find recent work on the problem
```bash
python -c "
from alpha_review.apis import search_all
import json, sys
query = sys.argv[1]
results = search_all(query, limit_per_source=15, year_lo=2023)
print(json.dumps([{'id': r.get('paperId'), 'title': r['title'], 'year': r['year'],
                   'venue': r.get('venue',''), 'citations': r.get('citationCount',0),
                   'doi': r.get('doi',''), 'abstract': r.get('abstract','')[:400]}
                  for r in results[:20]], indent=2))
" "<problem>"
```

### Step 2 — Fetch full text for the top 5 hits
For each of the top 5 by citation count or recency:
```bash
python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
content = fetch_and_extract(sys.argv[1])
print(json.dumps({'title': content.title,
                  'abstract': content.abstract,
                  'intro': content.sections.get('introduction','')[:2000],
                  'conclusion': content.sections.get('conclusion','')[:1000],
                  'quality': content.extraction_quality.overall}, indent=2))
" "<paper_id>"
```

### Step 3 — Impact trajectory check
For 2-3 seminal prior papers on the topic, check the citation trajectory:
```bash
python -c "
from alpha_review.apis import s2_citations
import json, sys
cites = s2_citations(sys.argv[1], limit=50)
print(json.dumps([{'year': c.get('year'), 'title': c['title'][:80]}
                  for c in cites], indent=2))
" "<seminal_paper_id>"
```
Count citations per year. Is the trajectory rising (more interest) or
falling (field moving on)?

### Step 4 — Check for prior evaluations in the project memory
```bash
python -c "
import json, os
path = 'output/<project>/evaluations.jsonl'
if os.path.exists(path):
    records = [json.loads(l) for l in open(path)]
    matching = [r for r in records
                if any(kw.lower() in r.get('paper_title','').lower()
                       for kw in ['<keyword1>', '<keyword2>'])]
    print(json.dumps(matching, indent=2))
"
```

### Step 5 — Score each test
For each of the four tests, produce:
- `score: int` (1-5)
- `evidence: list[str]` (specific quotes, citation counts, trend data)
- `confidence: "high" | "medium" | "low"`
- `human_flag: bool` — TRUE if you cannot independently verify

### Step 6 — Write the result to project memory
```bash
python -c "
import json, time, uuid, sys
rec = json.loads(sys.argv[1])
rec['id'] = 'sig_' + uuid.uuid4().hex[:10]
rec['created_at'] = time.time()
with open('output/<project>/significance_screens.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
" '<serialized_result>'
```

## Output format

```json
{
  "problem": "...",
  "hamming": {"score": 4, "evidence": [...], "confidence": "medium", "human_flag": true},
  "consequence": {"score": 5, "evidence": [...], "confidence": "high", "human_flag": false},
  "durability": {"score": 3, "evidence": [...], "confidence": "medium", "human_flag": true},
  "compounding": {"score": 4, "evidence": [...], "confidence": "medium", "human_flag": true},
  "overall_recommendation": "proceed | proceed with caveats | do not proceed",
  "human_checkpoint_required": true,
  "notes": "..."
}
```

## Honesty protocol

You CANNOT judge actual significance — that requires the researcher's
Hamming list and field taste. Your job is to verify that significance
ARGUMENTS exist and are plausible, and to FLAG assessments that require
human judgment. ALWAYS set `human_flag=true` for the Hamming test.
Concrete, falsifiable consequence claims CAN be verified (set
`human_flag=false` when you find a specific downstream system named).

## References

- `guidelines/doctrine/research_guideline.md` §2.2 — significance tests
- `guidelines/doctrine/review_guideline.md` §3.1 — significance attack vectors
- `guidelines/spec/review_plan.md` §1.2 — significance metrics
```

---

### Skill 3 — `formalization-check`

**Path:** `.claude/skills/formalization-check/SKILL.md`

```markdown
---
name: formalization-check
description: Assess whether a research problem has a proper formal
             mathematical definition. Detects formalization level,
             identifies framework (MDP/POMDP/constrained-opt/etc.), and
             optionally verifies mathematical consistency with sympy.
             Use when the user asks "is this well-formalized", "what's
             the right framework for this problem", or to check a paper's
             problem statement.
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
---

# Formalization Check

## When to use

Applied to a paper, a proposed problem, or one of the researcher's own
drafts. Maps to the FORMALIZE stage of the research state machine and
to review attack vectors §3.2.

Per Tedrake: "If you can't write the math, you don't understand the
problem." Your job is to enforce this standard.

## Process

### Step 1 — Obtain the problem statement

If input is a paper:
```bash
python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
c = fetch_and_extract(sys.argv[1])
# Focus on abstract, intro, and problem-statement-heavy sections
print(json.dumps({
    'abstract': c.abstract,
    'intro': c.sections.get('introduction', '')[:3000],
    'problem': c.sections.get('problem', '') or c.sections.get('preliminaries', ''),
    'method': c.sections.get('method', '')[:2000],
    'quality': c.extraction_quality.overall,
    'math_preserved': c.extraction_quality.math_preserved,
}, indent=2))
" "<paper_id>"
```

If input is the researcher's own draft, use `Read` on the markdown/tex file.

### Step 2 — Classify formalization level

Read the problem statement and classify as:
- `formal_math` — explicit objective function, variables, constraints, and
  information structure written as mathematics
- `semi_formal` — some mathematical notation but key pieces are in prose
- `prose_only` — English description with no mathematical objects
- `absent` — no attempt at a formal problem statement

### Step 3 — If math is present, extract the structure

For `formal_math` or `semi_formal`, identify:
- **Framework**: MDP, POMDP, constrained optimization, Bayesian inference,
  dynamical system, hybrid system, game, SDE, other
- **Objective function**: what is being optimized/estimated/decided?
- **Decision variables**: what does the agent choose?
- **Constraints**: what restricts the feasible set?
- **Information structure**: what is observable, what is known a priori,
  what is stochastic?
- **Exploited structure**: convexity, symmetries (SE(3), permutation,
  time invariance), decomposability, sparsity, low-dimensional manifolds,
  Lyapunov structure, contact complementarity

### Step 4 — Check framework-reality fit

Common mismatches to flag:
- MDP used when the problem has partial observability → should be POMDP
- Deterministic formulation for a stochastic-dynamics problem
- Continuous formulation for a problem with hybrid contact switching
- Quasi-static when dynamics matter (e.g., acceleration-dependent slip)
- Convex relaxation whose violated original constraints matter in practice

### Step 5 — Optional sympy verification

If the paper claims specific mathematical properties (convexity,
smoothness, gradient form, closed-form solution), verify:

```bash
python -c "
import sympy as sp

# example: verify claimed convexity of an objective
x, y = sp.symbols('x y', real=True)
f = (x - 2*y)**2 + sp.exp(x)    # placeholder — substitute the actual expression
H = sp.hessian(f, (x, y))
eigvals = H.eigenvals()
print('Hessian:', H)
print('Eigenvalues:', eigvals)
print('All non-negative?', all(sp.simplify(e) >= 0 for e in eigvals))
"
```

Report whether the sympy check agreed with the paper's claim.

### Step 6 — Search for alternative formalizations

```bash
python -c "
from alpha_review.apis import search_all
import json, sys
query = sys.argv[1]  # e.g., 'POMDP contact-rich manipulation'
results = search_all(query, limit_per_source=10, year_lo=2020)
print(json.dumps([{'title': r['title'], 'year': r['year'],
                   'abstract': r.get('abstract','')[:300]}
                  for r in results[:10]], indent=2))
" "<framework> <problem keywords>"
```

Compare how other papers formalize similar problems. If most use a
different framework, note the discrepancy.

### Step 7 — Persist the result

```bash
python -c "
import json, time, uuid, sys
rec = json.loads(sys.argv[1])
rec['id'] = 'form_' + uuid.uuid4().hex[:10]
rec['created_at'] = time.time()
with open('output/<project>/formalization_checks.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
" '<serialized_result>'
```

## Output format

```json
{
  "level": "formal_math | semi_formal | prose_only | absent",
  "framework": "MDP | POMDP | constrained_opt | ...",
  "objective": "...",
  "decision_variables": [...],
  "constraints": [...],
  "information_structure": "...",
  "exploited_structure": ["convexity", "SE(3) symmetry", ...],
  "assumptions": [...],
  "framework_mismatch": "none | minor | major",
  "mismatch_details": "...",
  "sympy_verification": {"run": true, "passed": true, "notes": "..."},
  "alternative_formalizations_found": [...],
  "confidence": "high | medium | low",
  "human_flag": true
}
```

## Honesty protocol

You can detect PRESENCE or ABSENCE of formal statements with high
confidence. You CANNOT deeply judge whether a formalization captures the
RIGHT structure — that requires mathematical intuition the researcher
must provide. ALWAYS set `human_flag=true`. Provide strong signal but
defer judgment.

## References

- `guidelines/doctrine/research_guideline.md` §2.4, §3.1 — formalization standards
- `guidelines/doctrine/review_guideline.md` §3.2 — formalization attack vectors
- `guidelines/spec/review_plan.md` §1.3 — formalization metrics
```

---

### Skill 4 — `diagnose-system`

**Path:** `.claude/skills/diagnose-system/SKILL.md`

```markdown
---
name: diagnose-system
description: Build (or use) a minimal end-to-end system, run it, observe
             failures, and map each failure to a specific term in the
             formal problem structure. Use when the user says "let's
             diagnose what's failing", "run the minimal system", or
             "what's actually the bottleneck".
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, NotebookEdit, Task
model: claude-sonnet-4-6
---

# Diagnose System

## When to use

The researcher has a formalized problem (from `formalization-check`) and
needs to see what actually fails when a minimal system attempts the task.
Per research_guideline §2.4: "AFTER formalization, build the simplest
possible system and run it. Watch it fail."

This skill DOES NOT include its own simulator or training stack — it uses
the lab's existing infrastructure via `Bash`. The skill text must be
customized per-lab with local conventions; the template below uses
`configs/*.yaml`, `wandb`, and `mjpython` as placeholders.

## Process

### Step 1 — Locate the minimal system
```
Check these standard locations in order:
1. `Read` configs/minimal.yaml — lab convention
2. `Glob` "configs/*minimal*.yaml"
3. Ask the user for the path
```

### Step 2 — Run the experiment (lab-specific)

Replace this command with the lab's convention:
```bash
# Training / policy run
python scripts/run_policy.py --config configs/minimal.yaml --seeds 0 1 2 --n_trials 20

# Or simulation-only:
mjpython scripts/eval_sim.py --config configs/minimal.yaml --n_trials 20

# Log to wandb for later analysis
```

While running, use `Bash` with a generous timeout or (if long-running)
run in the background via `run_in_background=True`.

### Step 3 — Collect results

```bash
# From wandb
python -c "
import wandb, json
api = wandb.Api()
runs = api.runs('<project>', filters={'config.config_name': 'minimal.yaml'})
results = [{'run_id': r.id, 'success_rate': r.summary.get('success_rate'),
            'failure_reasons': r.summary.get('failure_reasons'),
            'trial_logs': r.config.get('trial_logs_path')} for r in runs[:3]]
print(json.dumps(results, indent=2))
"

# Or from local logs
python -c "
import json, glob
logs = sorted(glob.glob('logs/run_*/trial_*.json'))
data = [json.load(open(l)) for l in logs]
print(json.dumps({'n_trials': len(data),
                  'success_rate': sum(d['success'] for d in data)/len(data),
                  'failure_modes': [d.get('failure_reason') for d in data if not d['success']]},
                 indent=2))
"
```

### Step 4 — Classify failures into a taxonomy

For each failed trial, classify into one of:
- **Perception** — observation was wrong or insufficient
- **Planning** — decision was wrong given the observation
- **Execution** — action did not produce intended state change
- **Physics** — unexpected dynamics (slip, contact transition, deformation)
- **Spec** — success criterion was met but the task wasn't actually done

Produce a table: trial_id | failure_type | specific_description.

### Step 5 — Write specific failure descriptions (CRITICAL)

Do not write vague descriptions. Per §2.4:
- BAD: "grasping fails"
- GOOD: "grasping fails on objects <2mm thick because the depth camera
  has 3mm resolution at working distance, so the gripper closes on empty
  space"
- BAD: "the policy doesn't generalize"
- GOOD: "the visual encoder maps objects of similar color to nearby
  features despite different shapes, so the policy executes the mean
  action and fails on asymmetric objects"
- BAD: "planning is too slow"
- GOOD: "collision checking dominates (78% of wall-clock time); each check
  requires full forward kinematics on a 7-DOF arm (~2ms); total plan
  time 1.8s at 500Hz fk calls"

For each failure mode, ask: can you name the specific mechanism?

### Step 6 — Map failures to formal structure

Load the most recent formalization check:
```bash
python -c "
import json
recs = [json.loads(l) for l in open('output/<project>/formalization_checks.jsonl')]
latest = recs[-1] if recs else None
print(json.dumps(latest, indent=2))
"
```

For each failure mode, identify which term in the formal structure breaks:
- Observation model P(z|s) insufficient → perception failure on specific dim
- State representation missing relevant dim → planning failure
- Action representation discretized wrong → execution failure
- Dynamics model missing effect → physics failure

If failures map to terms in the formalization, the current formalization
is on track. If failures have NO mapping (they live outside the formal
structure), that triggers backward transition t4 (research_plan §outer
layer) — retreat to FORMALIZE with new information.

### Step 7 — Persist the diagnosis

```bash
python -c "
import json, time, uuid
rec = {
  'id': 'diag_' + uuid.uuid4().hex[:10],
  'created_at': time.time(),
  'system_config': 'configs/minimal.yaml',
  'n_trials': 60,
  'success_rate': 0.35,
  'failure_taxonomy': {...},
  'specific_failures': [...],
  'failure_to_formalism_map': {...},
  'suggested_next_stage': 'CHALLENGE | FORMALIZE (t4)',
  'dominant_failure_mode': '...',
}
with open('output/<project>/diagnoses.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
"
```

## Output format

```json
{
  "n_trials": 60,
  "success_rate": 0.35,
  "failure_taxonomy": {"perception": 18, "planning": 12, "execution": 9, "physics": 0, "spec": 0},
  "specific_failures": [
    {"trial": 3, "type": "perception", "description": "depth camera could not resolve..."},
    ...
  ],
  "failure_to_formalism_map": {
    "depth_resolution": "observation model P(z|s) insufficient for state dim h (object height)",
    ...
  },
  "dominant_failure_mode": "perception — insufficient depth resolution",
  "suggested_next_stage": "CHALLENGE",
  "human_review_required": ["physical_intuition_on_edge_cases"]
}
```

## Honesty protocol

You cannot run the physical robot yourself. You cannot *see* what went
wrong in a failed trial — you see logs, numbers, and possibly rendered
frames. When the failure mechanism requires physical intuition (e.g.,
"why did the object slip?"), flag it for the researcher to confirm.

## References

- `guidelines/doctrine/research_guideline.md` §2.4 — empirical diagnosis
- `guidelines/doctrine/research_guideline.md` §8.1 — failure taxonomy
- `guidelines/spec/research_plan.md` — backward trigger t4 (DIAGNOSE→FORMALIZE)
```

---

### Skill 5 — `challenge-articulate`

**Path:** `.claude/skills/challenge-articulate/SKILL.md`

```markdown
---
name: challenge-articulate
description: From diagnosed failures, identify the structural barrier
             (the challenge) that resists current solutions. The challenge
             must be structural (not a resource complaint) and must
             constrain the solution class. Use when the user has a
             diagnosis and asks "what's the real challenge here" or
             "why is this fundamentally hard".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
---

# Challenge Articulate

## When to use

The researcher has diagnosed specific failure modes (from `diagnose-system`)
and needs to identify the structural barrier underneath them. This is
where research taste lives. Maps to the CHALLENGE stage.

## The depth test (from research_guideline §2.5)

A well-articulated challenge:
1. Identifies a STRUCTURAL barrier, not a difficulty or resource complaint
   - BAD: "we need more data"
   - GOOD: "the data distribution shifts when the policy changes,
     creating a non-stationary optimization problem"
2. Suggests the CLASS of solutions that could work
   - The challenge should narrow the solution space dramatically
3. Distinguishes this problem from related problems
   - "Distributional shift in offline RL" ≠ "domain gap in sim-to-real"

## Process

### Step 1 — Load the diagnosis
```bash
python -c "
import json
recs = [json.loads(l) for l in open('output/<project>/diagnoses.jsonl')]
print(json.dumps(recs[-1], indent=2))
"
```

### Step 2 — Propose candidate challenges

For the dominant failure mode, propose 2-3 candidate structural
explanations. For each:
- State it in one sentence
- Classify its type using the research_guideline §2.7 table:
  - Sample complexity
  - Distribution shift
  - Combinatorial explosion
  - Model uncertainty
  - Sensing limitation
  - Hardware limitation
  - Discontinuity
  - Long-horizon credit
  - Grounding gap

### Step 3 — Apply the structural test

For each candidate:
1. Is it structural or a resource complaint?
2. Does it constrain the solution class? (If yes, name the implied class
   from the §2.7 table)
3. If someone understood ONLY the challenge, would they predict the
   method class?

If any candidate fails all three tests, discard it.

### Step 4 — Search for how others articulate similar challenges

```bash
python -c "
from alpha_review.apis import search_all
import json, sys
query = sys.argv[1]  # e.g., 'distribution shift offline RL structural'
results = search_all(query, limit_per_source=10, year_lo=2020)
# Focus on high-citation papers that likely contain well-articulated challenges
results.sort(key=lambda r: r.get('citationCount', 0), reverse=True)
print(json.dumps([{'title': r['title'], 'cites': r.get('citationCount',0),
                   'abstract': r.get('abstract','')[:400]} for r in results[:5]],
                 indent=2))
" "<challenge_keywords>"
```

For top hits, use `paper-evaluate` skill (or fetch_and_extract inline) to
extract how they articulate the challenge.

### Step 5 — Check if the challenge has been addressed

```bash
python -c "
from alpha_review.apis import search_all
import json
results = search_all('<specific_challenge_keywords>', limit_per_source=10, year_lo=2023)
print(json.dumps([{'title': r['title'], 'year': r['year'],
                   'venue': r.get('venue',''), 'doi': r.get('doi','')}
                  for r in results], indent=2))
"
```

If the specific structural barrier has been solved by recent work, this
is trigger t12 (backward to CHALLENGE re-articulation) or t9 (scooped,
backward to SIGNIFICANCE).

### Step 6 — Persist the articulated challenge

```bash
python -c "
import json, time, uuid
rec = {
  'id': 'chal_' + uuid.uuid4().hex[:10],
  'created_at': time.time(),
  'challenge_statement': '...',
  'challenge_type': 'distribution_shift',  # from §2.7 table
  'implied_solution_class': 'robust methods, conservative estimation',
  'diagnosis_id': '<diag_id>',
  'related_work': [...],
  'prior_work_addressing_it': [...],  # or empty
  'passes_structural_test': true,
  'human_review_required': true
}
with open('output/<project>/challenges.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
"
```

## Output format

```json
{
  "challenge_statement": "single sentence naming the structural barrier",
  "challenge_type": "sample_complexity | distribution_shift | combinatorial_explosion | model_uncertainty | sensing_limitation | hardware_limitation | discontinuity | long_horizon_credit | grounding_gap",
  "implied_solution_class": "what §2.7 says this challenge suggests",
  "related_work_articulating_similar_challenge": [...],
  "prior_work_addressing_this_specific_barrier": [...],
  "passes_structural_test": true,
  "passes_solution_narrowing_test": true,
  "human_flag": true,
  "suggested_next_stage": "APPROACH | CHALLENGE re-articulation (t12)"
}
```

## Honesty protocol

Identifying the right structural barrier is where research taste lives.
Your role is to enforce the three structural-test criteria and to propose
candidates from the §2.7 table — not to authoritatively name the "correct"
challenge. Always flag for human review.

## References

- `guidelines/doctrine/research_guideline.md` §2.5 — challenge analysis
- `guidelines/doctrine/research_guideline.md` §2.7 — challenge → approach table
- `guidelines/doctrine/review_guideline.md` §3.3 — challenge attack vectors
- `guidelines/spec/research_plan.md` — guards g3, g4; triggers t6, t12
```

---

### Skill 6 — `method-survey`

**Path:** `.claude/skills/method-survey/SKILL.md`

```markdown
---
name: method-survey
description: Survey existing methods within the solution class implied by
             an articulated challenge. Build a comparison table of
             performance, assumptions, complexity, and practical viability.
             Use when the user has a challenge and asks "what methods exist
             for this", "how have others approached this challenge".
allowed-tools: Bash, Read, Write, Grep, Task
model: claude-sonnet-4-6
---

# Method Survey

## When to use

The researcher has articulated a challenge (from `challenge-articulate`)
and needs to survey the methods within the solution class that challenge
implies. This is the inner layer search of the APPROACH stage.

## Process

### Step 1 — Load the challenge
```bash
python -c "
import json
recs = [json.loads(l) for l in open('output/<project>/challenges.jsonl')]
print(json.dumps(recs[-1], indent=2))
"
```

Identify `challenge_type` and `implied_solution_class`.

### Step 2 — Search within the implied method class
```bash
python -c "
from alpha_review.apis import search_all
import json, sys
# Example queries per challenge type:
# sample_complexity → 'equivariant grasping', 'physics-informed priors'
# distribution_shift → 'conservative Q-learning', 'domain randomization'
# sensing_limitation → 'tactile insertion', 'active perception'
# combinatorial_explosion → 'task and motion planning', 'skill composition'
query = sys.argv[1]
results = search_all(query, limit_per_source=15, year_lo=2020)
results.sort(key=lambda r: r.get('citationCount', 0), reverse=True)
print(json.dumps([{'id': r.get('paperId'), 'title': r['title'],
                   'year': r['year'], 'cites': r.get('citationCount',0),
                   'doi': r.get('doi',''),
                   'abstract': r.get('abstract','')[:300]} for r in results[:15]],
                 indent=2))
" "<method_class_query>"
```

### Step 3 — Expand via citation graph
For the top 3 most-cited papers, traverse references and citations:
```bash
python -c "
from alpha_review.apis import s2_references, s2_citations
import json, sys
pid = sys.argv[1]
refs = s2_references(pid, limit=20)
cites = s2_citations(pid, limit=20)
print(json.dumps({'references': [{'title': r['title'], 'year': r['year']} for r in refs],
                  'citations':  [{'title': c['title'], 'year': c['year']} for c in cites]},
                 indent=2))
" "<top_paper_id>"
```

### Step 4 — Extract method details (parallel via Task)
For each candidate method paper, extract:
- Approach summary (1-2 sentences)
- Key assumptions
- Reported performance (numbers)
- Baselines used
- Computational complexity / wall-clock time
- Failure modes (if reported)
- Code release

Use `Task` to parallelize across papers — each subagent invokes
`paper-evaluate` skill on one paper.

### Step 5 — Build comparison table

| Method | Year | Assumptions | Reported SR | Baselines | Code | Failure modes |
|---|---|---|---|---|---|---|
| ... | | | | | | |

### Step 6 — Identify gaps in the solution class

For the implied method class, what hasn't been tried?
- Methods on the boundary of this class
- Cross-cuts with other method classes
- Obvious ablations no one has run
- Specific assumptions no one has relaxed

### Step 7 — Persist
```bash
python -c "
import json, time, uuid
rec = {
  'id': 'msurv_' + uuid.uuid4().hex[:10],
  'created_at': time.time(),
  'challenge_id': '<chal_id>',
  'method_class': '...',
  'methods_surveyed': [...],
  'comparison_table': [...],
  'gaps_in_class': [...],
  'suggested_approach_direction': '...',
  'human_flag': false
}
with open('output/<project>/method_surveys.jsonl', 'a') as f:
    f.write(json.dumps(rec) + '\n')
print(rec['id'])
"
```

## Output format
Structured comparison table + gaps + suggested direction.

## Honesty protocol

You can compare reported numbers but cannot verify they reproduce. Flag
any paper where `paper-evaluate` assigned low confidence to B.3
(experimental rigor).

## References

- `guidelines/doctrine/research_guideline.md` §2.7 — challenge → method class table
- `guidelines/spec/research_plan.md` APPROACH stage inner layer
```

---

### Skills 7-12 (condensed)

For brevity, the remaining 6 skills follow the same structure. Full
`SKILL.md` files are provided in the implementation plan. Here is the key
content for each.

---

#### Skill 7 — `experiment-audit`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write, Grep`
- `model: claude-sonnet-4-6`

**Purpose:** Check whether experimental evidence supports the claims:
statistical sufficiency, baseline strength, ablation isolation, venue
thresholds. Applied to own experiments or to a paper under review.

**Key process steps:**
1. Load experimental data (via `Read` for own logs, `python -c fetch_and_extract` for papers)
2. Run statistical tests via `bash python -c "from scipy.stats import ..."`:
   - Trials per condition (venue thresholds: IJRR/T-RO/RSS ≥20, CoRL ≥10)
   - Confidence intervals and variance across seeds
   - Ablation isolation: does removing claimed contribution actually degrade performance?
3. Name the strongest MISSING baseline via `alpha_review.apis.search_all`
4. Check overclaiming patterns from `review_guideline.md` §3.5.3:
   - Generality overclaim (scope vs test-scope)
   - Novelty overclaim (claim vs actual delta)
   - Comparison overclaim (claimed superiority vs tested metrics)
5. Write `AuditReport` to `output/<project>/audits.jsonl`

**Key references:** research_guideline §8, review_guideline §3.5, review_plan §1.6

---

#### Skill 8 — `adversarial-review`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write, Edit, Grep, Task`
- `model: claude-opus-4-6`

**Purpose:** Full adversarial review applying all attack vectors from
`review_guideline.md` Part III, with graduated pressure per `review_plan.md` §3.

**Key process — graduated pressure:**

**Iteration 1 — Structural scan (5 min):**
1. `python -c "from alpha_research.tools.paper_fetch import fetch_and_extract; ..."`
2. Extract logical chain: SIGNIFICANCE → FORMALIZATION → CHALLENGE → APPROACH → VALIDATION
3. Quick fatal-flaw scan per `review_guideline.md` Appendix A.1

**Iteration 2 — Full review (30 min):**
1. Apply all six attack vectors §3.1–§3.6 systematically
2. Invoke sub-skills via `Task`:
   - `concurrent-work-check` (for §3.1 scoop detection)
   - `formalization-check` (for §3.2 formalization attack)
   - `experiment-audit` (for §3.5 validation attack)
3. For each finding: classify severity (fatal/serious/minor), and write:
   - `what_is_wrong`
   - `why_it_matters`
   - `what_would_fix_it`
   - `falsification_condition`
4. Steel-man the argument (≥3 sentences of genuine strengths)
5. Compute verdict MECHANICALLY from findings per `review_plan.md` §1.9
   (not gestalt averaging)

**Iteration 3+ — Focused re-review:**
1. For each previous finding: addressed / partially / not / regressed
2. Check for new weaknesses introduced by revisions

**Output:** `Review` record written to `output/<project>/reviews.jsonl` with
chain_extraction, steel_man, findings, verdict, confidence, questions_for_authors.

**Key references:** review_guideline.md Part III, review_plan.md §1, §3

---

#### Skill 9 — `paper-evaluate`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write`
- `model: claude-sonnet-4-6` (deep); can delegate skim phase to Haiku

**Purpose:** Per-paper evaluation against the full `research_guideline.md`
Appendix B rubric (B.1–B.7).

**Key process:**

1. **Fetch paper content:**
   ```bash
   python -c "
   from alpha_research.tools.paper_fetch import fetch_and_extract
   from alpha_review.apis import s2_paper_details
   import json, sys
   c = fetch_and_extract(sys.argv[1], extract_sections=True)
   meta = s2_paper_details(sys.argv[1])
   print(json.dumps({
       'title': c.title, 'abstract': c.abstract,
       'sections': c.sections, 'quality': c.extraction_quality.overall,
       'citations': meta.get('citationCount', 0) if meta else 0,
       'venue': meta.get('venue', '') if meta else '',
   }))
   " "<paper_id>"
   ```

2. **Skim pass** (Haiku can do this): score relevance 0-1 from title + abstract + conclusion only. If < 0.5, short-circuit with `relevance_only` record.

3. **Deep pass** (Sonnet/Opus): for each rubric dimension B.1-B.7:
   - Score (1-5)
   - Evidence (quotes with section references)
   - Confidence (high/medium/low)
   - Honesty flag (set when extraction_quality.overall is "low" or when the dimension requires physical intuition)

4. **Task chain extraction:** extract `task`, `problem`, `challenge`, `approach`, `one_sentence` — the most important extraction per the guideline.

5. **Cross-check novelty against prior evaluations:**
   ```bash
   python -c "
   import json
   recs = [json.loads(l) for l in open('output/<project>/evaluations.jsonl')]
   related = [r for r in recs if any(kw in r.get('title','').lower() for kw in [...])]
   print(json.dumps(related, indent=2))
   "
   ```

6. **Persist** to `output/<project>/evaluations.jsonl`.

**Key references:** research_guideline.md Appendix B

---

#### Skill 10 — `concurrent-work-check`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write`
- `model: claude-sonnet-4-6`

**Purpose:** Detect if a problem has been solved (or nearly solved) by
concurrent or recent work. Maps to research_guideline §2.2 concurrent
work test and backward trigger t9.

**Key process:**
1. Search with multiple query formulations:
   ```bash
   python -c "
   from alpha_review.apis import search_all
   import json
   queries = ['<problem statement>', '<approach keywords>', '<key technical terms>']
   for q in queries:
       results = search_all(q, limit_per_source=10, year_lo=2024)
       print(json.dumps({'query': q, 'results': results[:5]}, indent=2))
   "
   ```

2. For high-overlap hits, fetch full text via `paper_fetch` and compare
   approach details.

3. As a last resort, search Google Scholar for workshop/tech-report
   coverage:
   ```bash
   python -c "
   from alpha_review.scholar import scholar_search_papers
   import json
   papers, rel = scholar_search_papers('<query>', max_pages=1)
   print(json.dumps(papers, indent=2))
   "
   ```

4. Write a `ConcurrentWorkReport` with `overlap_degree` ∈
   {none, minor, significant, scooped} and a differentiation plan.

**Key references:** research_guideline.md §2.2 (concurrent work test),
§2.6 (why-now), research_plan.md backward trigger t9

---

#### Skill 11 — `gap-analysis`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write`
- `model: claude-opus-4-6`

**Purpose:** Identify recurring limitations and unsolved failure modes
across a body of evaluated papers. Maps to research_guideline §5.1 Axis 1.

**Key process:**

1. Aggregate evaluations from project memory:
   ```bash
   python -c "
   import json
   recs = [json.loads(l) for l in open('output/<project>/evaluations.jsonl')]
   print(json.dumps({'count': len(recs),
                     'weaknesses': [{'paper': r['paper_id'],
                                     'weaknesses': r.get('weaknesses', [])} for r in recs]},
                    indent=2))
   "
   ```

2. Identify limitations appearing in ≥ 3 papers.

3. For each candidate gap, search to verify it's a REAL gap (not just
   missed papers): `bash python -c "from alpha_review.apis import search_all; ..."`.

4. Cross-reference with the researcher's Hamming list (in
   `guidelines/hamming_list.md` or similar).

5. Propose directions with `significance-screen` applied to each.

6. Write `GapReport` to `output/<project>/gaps.jsonl`.

**Key references:** research_guideline.md §5.1 Axis 1, review_guideline.md
§3.3 challenge attack

---

#### Skill 12 — `frontier-mapping`

**Frontmatter summary:**
- `allowed-tools: Bash, Read, Write`
- `model: claude-sonnet-4-6`

**Purpose:** Classify current capabilities in a domain into three tiers:
reliable / sometimes / can't-yet. Maps to research_guideline §5.1 Axis 3.

**Key process:**

1. Gather evaluations for the domain:
   ```bash
   python -c "
   import json
   recs = [json.loads(l) for l in open('output/<project>/evaluations.jsonl')]
   domain_recs = [r for r in recs if '<domain keyword>' in r.get('task_chain',{}).get('task','').lower()]
   print(json.dumps(domain_recs, indent=2))
   "
   ```

2. Search for recent papers claiming new capabilities:
   ```bash
   python -c "
   from alpha_review.apis import search_all
   import json
   results = search_all('<domain> SOTA', limit_per_source=15, year_lo=2024)
   print(json.dumps([{'title': r['title'], 'venue': r.get('venue',''),
                      'claimed_capability': r.get('abstract','')[:300]}
                     for r in results], indent=2))
   "
   ```

3. Classify capabilities into three tiers with evidence per capability.

4. If a previous frontier snapshot exists in
   `output/<project>/frontier.jsonl`, compute the diff (what moved
   between tiers).

5. Write new snapshot to `output/<project>/frontier.jsonl`.

**Key references:** research_guideline.md §5.1 Axis 3

---

## Part V. Skill Discovery and Invocation

Skills are Claude Code's primary extension mechanism.

**Auto-discovery:** Claude Code reads all skill `description` fields at
startup (~100 tokens each). When the user's prompt matches a skill's
description, Claude pulls the full `SKILL.md` into context (progressive
disclosure — the body is not in context until matched).

**Explicit invocation:** `/significance-screen "contact-rich manipulation"`
when a skill has `user-invocable: true`.

**Agent invocation:** Our existing Python agents (`ResearchAgent`,
`ReviewAgent`, `MetaReviewer`, `Orchestrator`) reference skills by name in
their system prompts. When the conversation reaches the relevant research
stage, Claude executes the skill.

**Composition via `Task`:** A skill can spawn a subagent (via built-in
`Task`) that runs another skill. `literature-survey` uses this to run
`paper-evaluate` in parallel across included papers.

---

## Part VI. What Changes in the `alpha_research` Codebase

### Add
- `.claude/skills/literature-survey/SKILL.md`
- `.claude/skills/significance-screen/SKILL.md`
- `.claude/skills/formalization-check/SKILL.md`
- `.claude/skills/diagnose-system/SKILL.md`
- `.claude/skills/challenge-articulate/SKILL.md`
- `.claude/skills/method-survey/SKILL.md`
- `.claude/skills/experiment-audit/SKILL.md`
- `.claude/skills/adversarial-review/SKILL.md`
- `.claude/skills/paper-evaluate/SKILL.md`
- `.claude/skills/concurrent-work-check/SKILL.md`
- `.claude/skills/gap-analysis/SKILL.md`
- `.claude/skills/frontier-mapping/SKILL.md`
- `alpha_review` as editable dependency in `pyproject.toml`

### Keep (but make skill-invokable via `bash python -c`)
- `src/alpha_research/tools/paper_fetch.py` — existing PDF extraction
- `src/alpha_research/agents/*.py` — Python orchestration layer
- `src/alpha_research/models/review.py` — Review/Finding/Verdict dataclasses
- `src/alpha_research/metrics/*.py` — review quality, convergence
- `src/alpha_research/prompts/*.py` — migrate content into skills over time

### Delete (no longer needed — replaced by alpha_review + skills)
- `src/alpha_research/tools/arxiv_search.py` — replaced by `alpha_review.apis.arxiv_search`
- `src/alpha_research/tools/semantic_scholar.py` — replaced by `alpha_review.apis.s2_*`
- `src/alpha_research/knowledge/store.py` (paper/theme portions) — replaced by `alpha_review.ReviewState`
- `src/alpha_research/knowledge/schema.py` (paper/theme portions) — same
- Any plans for an MCP server at `src/alpha_research/mcp_server/` — do not build

### Not needed
- No MCP server
- No new tool wrappers
- No extension SQLite schema (use JSONL files instead)
- No JSON Schema duplication
- No provider adapters for tools (tools don't exist)

---

## Part VII. Cross-LLM Portability

### The honest picture

- **Claude Code / Claude Agent SDK / Claude API**: native support. SKILL.md
  files are read directly. `Bash` + `Read` + `Write` all available.

- **OpenAI (Assistants API, Agents SDK)**: translate each SKILL.md's body
  into the Assistant `instructions` field. Provide `code_interpreter` as
  the equivalent of `Bash` (with `alpha_review` pre-installed in the
  interpreter's environment). Provide `file_search` / `retrieval` for the
  JSONL project memory.

- **Gemini**: translate SKILL.md body into `system_instruction`. Provide
  `code_execution` as the `Bash` equivalent.

- **Open-source (LLaMA 3.1+, Qwen 2.5+, DeepSeek V3, local via vLLM/Ollama)**:
  wrap via LangChain. Each SKILL.md body becomes a `SystemMessage`;
  `Bash` becomes a `PythonREPLTool` or `ShellTool`.

### The adapter is small

```python
# src/alpha_research/adapters/skill_translator.py

from pathlib import Path
import yaml

def skill_to_system_prompt(skill_md_path: Path) -> dict:
    """Translate .claude/skills/<slug>/SKILL.md into a provider-neutral
    system prompt + tool list + model hint."""
    content = skill_md_path.read_text()
    parts = content.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()
    return {
        "name": frontmatter["name"],
        "description": frontmatter.get("description", ""),
        "system_prompt": f"# Role: {frontmatter['name']}\n\n{body}",
        "required_tools": frontmatter.get("allowed-tools", "").replace(",", " ").split(),
        "model_hint": frontmatter.get("model"),
    }
```

That's the entire cross-LLM adapter. ~20 lines, not a framework.

---

## Part VIII. Explicit Non-Goals

To keep the architecture honest, here is what we are explicitly NOT
building, with reasons:

| Non-goal | Why not |
|---|---|
| MCP server | No capability gap that MCP fills. `Bash` reaches everything. |
| Custom tool definitions | Same reason. |
| Extension SQLite tables | JSONL files serve the same purpose with zero schema management. |
| Wrapper classes around `alpha_review` APIs | The Python functions are already cleanly callable. |
| Cross-provider tool registry | Tools don't exist in this architecture. Only skills and their translations. |
| Framework for skill composition | `Task` (built-in subagent) + JSONL records handle it. |
| New CLI commands | `alpha_review` already provides `alpha-review`. `Bash` runs everything else. |
| Experiment launch/query abstractions | Lab-specific. Use `Bash` + skill text. |
| Math verification tool | `bash python -c "import sympy; ..."` is one line. |
| Plot generation tool | `bash python plot.py`. |
| Statistical test tool | `bash python -c "from scipy.stats import ..."`. |

**Everything the project needs is a skill.** That is the entire architectural
thesis.

---

## Appendix — The 12 skills at a glance

| # | Skill | Model | Primary built-ins | `alpha_review` Python used |
|---|---|---|---|---|
| 1 | `literature-survey` | Sonnet | Bash, Read, Write, Task | `alpha-review` CLI + `ReviewState` |
| 2 | `significance-screen` | Opus | Bash, Read, Write | `apis.search_all`, `apis.s2_citations`, `paper_fetch` |
| 3 | `formalization-check` | Opus | Bash, Read, Write | `apis.search_all`, `paper_fetch`, sympy |
| 4 | `diagnose-system` | Sonnet | Bash, Read, Write, Edit, NotebookEdit | lab-specific scripts |
| 5 | `challenge-articulate` | Opus | Bash, Read, Write | `apis.search_all`, `paper_fetch` |
| 6 | `method-survey` | Sonnet | Bash, Read, Write, Task | `apis.search_all`, `apis.s2_references`, `apis.s2_citations` |
| 7 | `experiment-audit` | Sonnet | Bash, Read, Write | `apis.search_all`, scipy |
| 8 | `adversarial-review` | Opus | Bash, Read, Write, Edit, Task | `apis.search_all`, `apis.s2_citations`, `paper_fetch` |
| 9 | `paper-evaluate` | Haiku → Sonnet | Bash, Read, Write | `paper_fetch`, `apis.s2_paper_details` |
| 10 | `concurrent-work-check` | Sonnet | Bash, Read, Write | `apis.search_all`, `scholar.scholar_search_papers`, `paper_fetch` |
| 11 | `gap-analysis` | Opus | Bash, Read, Write | JSONL reads + `apis.search_all` |
| 12 | `frontier-mapping` | Sonnet | Bash, Read, Write | JSONL reads + `apis.search_all` |

**Total custom infrastructure: 12 markdown files. Zero tools. Zero schemas. Zero new Python modules.**

---

## Sources

- `guidelines/doctrine/research_guideline.md` — the research lifecycle
- `guidelines/doctrine/review_guideline.md` — adversarial review companion
- `guidelines/spec/research_plan.md` — state-machine architecture
- `guidelines/spec/review_plan.md` — executable review metrics
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude Code built-in tools: https://code.claude.com/docs/en/tools
- `../alpha_review/` — dependency providing scholarly APIs, state, survey SDK

---

## Note on `tools_and_skills_implementation.md`

The separate implementation-plan document in this directory (written for
the earlier tool-heavy architecture) is now **mostly obsolete**. Its
skill-content sections (Part II) are still usable, but Parts I (MCP tool
specs), III (tool test strategy), IV Phase 1 (tool implementation tasks),
VI (tool acceptance checklist), and VII (tool source mapping) should be
deleted or ignored. A future revision should either delete that file or
rewrite it to cover only skill-file authoring and JSONL record conventions.
