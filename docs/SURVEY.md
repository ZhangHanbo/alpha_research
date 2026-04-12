# Alpha Research — Online Survey Log

This file is the multi-round record of online surveys conducted
during Alpha Research's design. Every design decision stands on a
documented survey. Rounds are added over time, newest at the bottom.
Each round states its date, scope, method, and deliverables. Source
citations are preserved so future surveys can refresh them.

**Organization**:
- Round 1 — 2026-03 — Venue calibration + open-source landscape

Future rounds will append below Round 1 without reorganizing it.

---

# Round 1 — 2026-03

**Date**: March 2026 (finalized before the 2026-04-11 three-canonical-docs session).

**Scope**: (a) compile the reviewer guidelines, evaluation criteria,
scoring rubrics, and expert advice from top robotics and AI
conferences/journals to inform the adversarial review agent's
venue calibration, and (b) review the open-source AI research agent
landscape to inform the frontend plan (later deferred).

**Method**: Online research across official venue guidelines, vendor
docs, open-source repositories, and foundational texts on reviewing.
No primary interviews.

**Deliverables**: Two distinct investigations, consolidated here.
The conclusions flowed into `docs/PROJECT.md` §5 Review Doctrine
(via `guidelines/doctrine/review_guideline.md`) and into the
deferred frontend plan in `docs/PLAN.md` §8.2.

---

## 1.1 — Venue Calibration

Source compilation from `guidelines/doctrine/review_standards_reference.md`.
Covers RSS, CoRL, ICRA, IROS, T-RO, IJRR, RA-L, HRI, NeurIPS, ICML,
ICLR, and CVPR, plus three foundational texts on reviewing.

### 1.1.1 RSS — Robotics: Science and Systems

**Review Form (8 components)**:

1. **Expertise Assessment** — Reviewer rates familiarity with subject
2. **Paper Summary** — Must "re-express your paper's position so
   clearly, vividly, and fairly that the authors say, 'Thanks, I
   wish I'd thought of putting it that way.'"
3. **Points of Agreement** — Identification of consensus areas
4. **Learning Outcomes** — What insights the reviewer gained
5. **Quality Score** (5-tier):
   - **Excellent**: Standout papers from the past year
   - **Very Good**: Solid, important contributions
   - **Good**: Flawed but valuable
   - **Fair**: Developing but incomplete
   - **Poor**: Requires substantial revision
6. **Impact Checkbox** — Whether work differs meaningfully with community influence potential
7. **Detailed Justification** — Thorough analysis
8. **Confidential Comments** — Optional notes for the papers committee

**Process**: Two-stage with threshold decision in Round 1. Papers
receiving at least one recommendation of Weak Accept or higher
advance to revision (3 weeks). Recommendations: Accept (A), Weak
Accept (WA), Weak Reject (WR), Reject (R). Round 2 results: Accept
with Minor Revisions or Reject.

**Key Policy**: Maximum 8 pages excluding references. "This is a
ceiling, not a floor, and reviewers are likely to look favorably
upon papers that are not unnecessarily long or verbose."

**Desk Rejection Criteria**: Incomplete submissions, non-anonymized
papers, formatting errors, out of scope, not in English.

**Sources**: [RSS Review Process](https://roboticsconference.org/2024/reviewps/),
[RSS Review Form](https://roboticsconference.org/2019/12/04/review-form/)

### 1.1.2 CoRL — Conference on Robot Learning

**Six Evaluation Dimensions**:

1. **Originality** — Are the problems or methods new? Novel combination? Evaluate novelty, differentiation from prior work, citation adequacy.
2. **Quality** — Technical soundness, empirical/theoretical support, methodological appropriateness, completeness.
3. **Clarity** — Organization, readability, expert-reproduction detail.
4. **Significance** — Practical impact, adoption likelihood, SOTA advancement, theoretical/experimental uniqueness.
5. **Relevance** — Addresses robot learning? Applies or improves learning-based method? Evaluated in sim or real? CoRL audience interest?
6. **Limitations** — Papers must include a limitations section. "Honestly reported limitations should be treated kindly and with high appreciation." Unreported obvious flaws warrant strong criticism.

**Scope**: Submissions must demonstrate relevance through either
explicitly addressing a learning question for physical robots, OR
testing proposed solutions on actual robotic systems.

**Reviewer Qualifications**: Minimum 3 first-author publications in
major robotics venues (CoRL, RSS, ICRA, IROS, IJRR, TRO, RAL) and
core ML venues (NeurIPS, ICML, AIStats, JMLR, PAMI).

**Key Principle**: "Be constructive and concrete; be courteous and
respectful. Start with the positive aspects, suggest improvements,
and accept diverse views in a discussion." **Avoid blanket
rejections based on single factors** (lack of novelty alone, missing
datasets, absence of theorems).

**Sources**: [CoRL 2024 Instructions](https://2024.corl.org/contributions/instruction-for-reviews),
[CoRL 2023 Guidelines](https://www.corl2023.org/reviewer-guidelines)

### 1.1.3 ICRA — IEEE International Conference on Robotics and Automation

**Evaluation Criteria**: Originality, significance, technical
quality, clarity of presentation.

**Review Board**: Editor-in-Chief, Senior Editors, ~400 Associate
Editors, several hundred Reviewers. Each paper: one Editor + one
AE, minimum two high-quality reviews.

**Process**: Rigorous peer review with plagiarism checks,
formatting adherence, page limit verification. Each paper assigned
to expert reviewers.

**AI Policy**: Generative AI tools may not be listed as authors.
AI-generated content must be disclosed in acknowledgments with
specific sections identified.

**Source**: [ICRA 2026 Call for Papers](https://2026.ieee-icra.org/contribute/call-for-icra-2026-papers-now-accepting-submissions/)

### 1.1.4 IROS — IEEE/RSJ International Conference on Intelligent Robots and Systems

**Structure**: IROS Conference Paper Review Board (ICPRB): EiC,
27 Senior Editors, ~400 Associate Editors, several hundred
Reviewers. Each paper: minimum two high-quality reviews.

**Review Requirements**:
- **Minimum 1,200 non-white character threshold per review** (substantive feedback)
- Must include: confidence statement, criteria assessments, potential
  confidential statement to ICPRB, and detailed review describing
  contribution and justifying overall assessment

**Conflict of Interest**: Co-author, student/advisor, co-authored
paper in previous 5 years, same institution at department/division
level.

**Source**: [IROS Information for Reviewers](https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/information-for-reviewers)

### 1.1.5 T-RO — IEEE Transactions on Robotics

**Key Principle**: "Editors and reviewers are not there to be
inflexible judges; rather their role is to help authors write
better papers."

**Evaluation Areas**: Paper contribution and significance; clarity;
purpose statement; reference completeness; technical soundness;
paper length and condensation possibilities.

**Review Format**:
1. Brief summary demonstrating comprehension
2. Overall comments (excluding publication recommendation in author-visible section)
3. Detailed list of minor items
4. Confidential comments for Editorial Board only

**Critical Instructions**:
- Do not identify yourself in review text
- Avoid explicit acceptance/rejection statements in author comments
- Provide specific, detailed feedback with references to similar work
- Comment on multimedia attachments for consistency and technical quality
- **AI-generated review content is prohibited** (grammar enhancement tools acceptable with disclosure)

**Reviewer Obligation**: Submitting authors agree to provide up to
3 high-quality reviews of other T-RO submissions if called upon.

**Source**: [T-RO Information](https://www.ieee-ras.org/publications/t-ro/)

### 1.1.6 IJRR — International Journal of Robotics Research

**Quality Standard**: "The quality level expected in a paper to
appear in IJRR is at the absolute top of archival publications in
robotics research."

**Publication Criteria**: IJRR only publishes work of archival
value. To do so it must be:
- **Original**: Novel contribution
- **Solid**: Results demonstrated by all relevant scientific means —
  mathematical proofs, statistically significant and reproducible
  experimental tests, field demonstrations, **"or whatever may be
  needed to convince a duly skeptical critical scientist"**
- **Useful to others**: Practical and/or theoretical impact

**Specific Standards**:
- Results should be a **significant rather than incremental advance**
- Results must be **verified appropriately**
- **Experimental results strongly encouraged**
- Up-to-date literature review + meaningful comparisons with prior work
- Application of theoretical advances to real problems encouraged
- Code and data sharing highly recommended
- **No a priori space limit**: "A paper should be as long as necessary, but no longer"

**Reviewer Qualifications**: Only researchers who have already
published in prestigious robotics journals. **Graduate students
should not be assigned reviews.**

**Review Process**: Single-blind, minimum two expert reviewers.

**Source**: [IJRR Submission Guidelines](https://journals.sagepub.com/author-instructions/ijr)

### 1.1.7 RA-L — IEEE Robotics and Automation Letters

**Quality Standard**: "A RA Letter is a timely and concise account
of innovative research ideas and application results." Comparable
to short papers in T-RO or T-ASE, though "the requirement of
**timeliness favours originality over maturity**."

**Review Principles**:
- "Review comments and recommendation reports should be constructive in their criticism, not just noting deficiencies but also indicating how they can be mended"
- "Any diminishing or disrespectful remark must be absolutely avoided"

**Review Format**:
1. Summary of paper's main contributions (reviewer's own words)
2. Evaluation of related work coverage
3. Assessment of strengths and weaknesses with constructive suggestions
4. Specific editing recommendations
5. Overall evaluation and recommendation

**Timeline**: 30 days to review original manuscripts, 14 days for
re-reviews. Publication within 6 months from submission — **no
exceptions**.

**Process**: Double-anonymous review (as of February 2025).

**Source**: [RA-L Information for Reviewers](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-reviewers/)

### 1.1.8 HRI — ACM/IEEE International Conference on Human-Robot Interaction

**Overall Rating Scale** (5-point, inverted):
1. Definite accept
2. Probably accept
3. Borderline
4. Probably reject
5. Definite reject

**Review Form Components**:
- Experience level (graduate student through 10+ years)
- Contribution identification and alignment with claims
- Detailed review following suggested outline
- Committee comments (hidden from authors)
- Long-term comparative rating vs. published HRI papers
- Sustainability recognition assessment

**Key Philosophy**: **"Favor slightly flawed, impactful work over
perfectly executed, low-impact work."**

**Track-Specific Evaluation**: Five tracks (User Studies, Design,
Technical, System, Theory & Methods) with track-specific
expectations.

**Target acceptance rate**: ~25%.

**Source**: [HRI 2026 Reviewer Guidelines](https://humanrobotinteraction.org/2026/full-paper-reviewer-guidelines/)

### 1.1.9 NeurIPS

**Review Form (11 sections)**:

1. **Summary** — Brief overview authors would recognize (not for critique)
2. **Strengths & Weaknesses** — Four-dimensional assessment
3. **Questions** — Points addressable during rebuttal
4. **Limitations** — Adequacy of author's limitations discussion
5. **Ethical Concerns**
6. **Soundness Rating** (1-4)
7. **Presentation Rating** (1-4)
8. **Contribution Rating** (1-4)
9. **Overall Score** (1-10 for 2024; 1-6 for 2025)
10. **Confidence Score** (1-5)
11. **Code of Conduct Acknowledgment**

**Four Evaluation Dimensions**:
- **Originality** — Novelty, task/method newness, differentiation, citation adequacy. **"Does not necessarily require introducing an entirely new method."** Novel insights from evaluating existing approaches count.
- **Quality** — Technical soundness, claim support, methodology appropriateness, completeness, author honesty about strengths/weaknesses.
- **Clarity** — Writing quality, organization, reproducibility sufficiency.
- **Significance** — Result importance, likelihood of use/building upon, SOTA advancement.

**NeurIPS 2024 Overall Score (1-10)**:
- 10: Award quality, groundbreaking impact
- 9: Very Strong Accept
- 8: Strong Accept
- 7: Accept
- 6: Weak Accept
- 5: Borderline accept
- 4: Borderline reject
- 3: Reject
- 2: Strong Reject
- 1: Very Strong Reject

**NeurIPS 2025 Overall Score (1-6)**:
- 6: Strong Accept — "Technically flawless paper with groundbreaking impact"
- 5: Accept — "Technically solid paper, with high impact on at least one sub-area"
- 4: Borderline Accept — "Reasons to accept outweigh reasons to reject"
- 3: Borderline Reject — "Reasons to reject outweigh reasons to accept"
- 2: Reject — "Technical flaws, weak evaluation, inadequate reproducibility"
- 1: Strong Reject — "Well-known results or unaddressed ethical considerations"

**Confidence Scale (1-5)**:
- 5: Absolutely certain
- 4: Confident
- 3: Fairly confident
- 2: Willing to defend (likely gaps)
- 1: Educated guess

**Critical Instructions**:
- **"Do not make vague statements in your review, as they are unfairly difficult for authors to address."**
- **"Superficial, uninformed reviews without evidence are worse than no review."**
- "Authors should be rewarded rather than punished for being up front about limitations."
- "3-5 actionable points where author responses could change your opinion."

**NeurIPS 2019 Innovation (Cortes/Larochelle era)**:
- Reviewers must **"list three things this paper contributes"** — encourages reflection on strengths
- Must answer: **"What would the authors have to do for you to increase your score?"**

**Sources**: [NeurIPS 2024](https://neurips.cc/Conferences/2024/ReviewerGuidelines),
[NeurIPS 2025](https://neurips.cc/Conferences/2025/ReviewerGuidelines),
[NeurIPS 2019 Medium Post](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)

### 1.1.10 ICML

**Review Form Sections**:
1. **Summary** — Objective overview without critique
2. **Claims and Evidence** — Whether claims have clear, convincing support
3. **Relation to Prior Works** — Broader literature context
4. **Other Aspects** — Originality, significance, clarity, strengths, weaknesses
5. **Questions for Authors** — Only where responses would materially change evaluation
6. **Ethical Issues**
7. **Code of Conduct**

**Overall Recommendation Scale (1-5)**:
- 5: Strong Accept
- 4: Accept
- 3: Weak Accept (leaning accept)
- 2: Weak Reject (leaning reject)
- 1: Reject

**Application-Driven Paper Guidance**:
- Assess whether approaches address real-world problem requirements
- Encourage use-informed datasets with proper documentation
- Consider non-ML approaches alongside ML baselines
- **Value impact on important applications, not solely ML community advancement**

**Key Principles**:
- "Review papers as you would wish yours reviewed"
- "Read carefully, critically, and empathetically"
- Recognize varied forms of originality: creative combinations, removed assumptions, real-world applications
- **AI tools prohibited for writing reviews**
- Must explicitly acknowledge authors' rebuttals

**Source**: [ICML 2025 Reviewer Instructions](https://icml.cc/Conferences/2025/ReviewerInstructions)

### 1.1.11 ICLR

**Core Evaluation Framework (4 key questions)**:

1. **Research Question** — What is the specific question/problem tackled?
2. **Motivation & Context** — Is the approach well-motivated and properly situated?
3. **Evidence & Validity** — Do results support claims with scientific rigor?
4. **Significance** — Does it contribute new knowledge and sufficient value? **"State-of-the-art results are not required."**

**Review Structure Requirements**:
- Summary of claimed contributions (positive, constructive tone)
- Comprehensive strong and weak points
- Clear initial recommendation (accept/reject) with key justifications
- Supporting arguments
- Clarifying questions for authors
- Constructive improvement suggestions

**Overall Rating (ICLR 2026)**: {0, 2, 4, 6, 8, 10}
**Overall Rating (ICLR 2024-2025)**: {1, 3, 5, 6, 8, 10}

**Contribution Value**: **"Submissions bring value to the ICLR
community when they convincingly demonstrate new, relevant, impactful
knowledge"** across empirical, theoretical, or practitioner domains —
not contingent on benchmark dominance.

**Quality Enforcement**: Late or low-quality reviews trigger
penalties: author-reviewers lose access to their own paper reviews
until completing assignments; persistently poor reviewers face desk
rejection of their own submissions.

**LLM Disclosure**: Reviewers must disclose any LLM usage;
non-disclosure risks desk rejection of their own papers.

**Source**: [ICLR 2026 Reviewer Guide](https://iclr.cc/Conferences/2026/ReviewerGuide)

### 1.1.12 CVPR

**Key Principles from CVPR Reviewer Tutorial**:

- **Be Specific and Concrete** — Avoid vague statements like "the paper is interesting." Provide detailed feedback referencing specific sections, figures, and tables.
- **Embrace Novel Ideas** — "Look for what is good or stimulating in the paper, and embrace novel, brave concepts, even if they have not been tested on many datasets."
- **Maintain Tone** — "A harshly written review will be resented by the authors." Use third person ("the paper") not second person ("you").
- **Structure** — Explain key ideas, contributions, and significance. Clearly explain why the paper should be accepted or not. Final justification should show how strengths and weaknesses were weighed.
- **Be Generous** — "The most valuable comments in a review are those that help the authors understand the shortcomings of their work and how they might improve it."

**Source**: [CVPR 2022 Reviewer Tutorial](https://cvpr2022.thecvf.com/sites/default/files/2021-11/How%20to%20be%20a%20good%20reviewer-tutorials%20for%20cvpr2022%20reviewers.pptx.pdf)

### 1.1.13 Alan Jay Smith — "The Task of the Referee" (1990)

Published in IEEE Computer, Vol. 23, 1990, pp. 65-71. One of the
most cited guides on paper reviewing in computer science.

**Core Referee Task**: Evaluate in a timely manner whether a paper
makes a sufficient contribution:
1. Is the work **correct**?
2. Is the problem studied and results obtained **new and significant**?
3. Is the quality of **presentation** satisfactory?
4. What **revisions** are necessary/desirable?

**Seven-Category Paper Classification**:
1. Major results; very significant (<1% of submissions)
2. Good, solid, interesting work; definite contribution (<10%)
3. Minor but positive contribution to knowledge (10-30%)
4. Technically correct but useless ("sophisticated analyses of flying pigs")
5. Neither elegant nor useful, but factually accurate
6. Wrong and misleading
7. Too poorly written for technical evaluation

**Evaluation Framework**:

*Novelty and Significance*:
- Is the problem real and clearly stated?
- Has this work been done previously?
- Is it "a trivial variation on or extension of previous results"?
- Is the problem obsolete or lacking general applicability?

*Methodological Validity*:
- Are assumptions realistic and clearly presented?
- Is the approach sufficient for the stated purpose?
- Can the method be understood clearly, or is it obscured by mathematical formulas?

*Correctness Assessment*:
- Are mathematical proofs sound?
- Are statistical methods appropriate?
- Do results align with stated assumptions and observed facts?
- Have boundary conditions been properly tested?

*Presentation Quality*:
- Does the abstract accurately represent the paper?
- Is the logical flow clear?
- Is technical content understandable to qualified readers?

**Key Principles**:
- **"Being too lenient produces poor scholarship and misinformation, while excessive criticism blocks legitimate research and damages careers."**
- Evaluate against the specific publication's average standards, not personal benchmarks.
- Target the paper, not the person.
- For rejection: explain why. For favorable: list both necessary and suggested changes.
- **Avoid detailed critique of "a badly flawed paper that can never be made publishable" when "fatal and uncorrectable flaws" exist.**

**Source**: [Full text via Princeton](https://www.cs.princeton.edu/~jrex/teaching/spring2005/fft/reviewing.html)

### 1.1.14 NeurIPS 2023 Tutorial — "What Can We Do About Reviewer #2?"

Presented by Nihar B. Shah (CMU). Panelists: Alice Oh (NeurIPS
2022 PC), Hugo Larochelle (EIC, TMLR), Andrew McCallum (OpenReview),
Mausam.

**Key Findings**:
- Provides a scientific lens on systemic issues in peer review
- Addresses inherent challenges through experiments on peer-review processes across disciplines
- Discusses viable solutions and important open problems
- **"Significance is a highly subjective criterion based on 80% reviewer taste and 20% experience"**
- **"Even for 'good' papers, it is rather easy to come up with issues that push it into borderline status"**

**Source**: [Tutorial Page](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/)

### 1.1.15 NeurIPS 2019 Guidelines (Cortes/Larochelle Era)

**Two Key Innovations**:

1. **Contributions Assessment**: Reviewers must "list three things
   this paper contributes" — theoretical, methodological, algorithmic,
   or empirical. Rationale: encourages reviewers to "actively reflect
   on the strengths of a submission, and not merely focus on finding
   issues or weaknesses."

2. **Constructive Improvement Guidance**: Reviewers answer: **"What
   would the authors have to do for you to increase your score?"**
   Encourages "more constructive reviews" through specific, actionable
   feedback.

**Source**: [NeurIPS 2019 Medium Post](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)

### 1.1.16 Unified Evaluation Framework (synthesis across venues)

**Technical Soundness / Correctness**:
- Are claims supported by evidence (theoretical proofs, experiments)?
- Are mathematical derivations correct?
- Are statistical methods appropriate?
- Are experimental designs valid?
- Are assumptions realistic and clearly stated?
- Have boundary conditions been tested?

**Novelty / Originality**:
- Is the problem new? Method new? Combination new?
- How does this differ from prior work?
- Is it a trivial extension or a significant departure?
- Are related works adequately cited and compared?
- "Originality does not necessarily require introducing an entirely new method" (NeurIPS 2025)

**Significance / Impact**:
- Does this advance the state of the art?
- Will others build on this work?
- Does it address an important problem?
- "State-of-the-art results are not required" (ICLR 2026)

**Clarity / Presentation**:
- Is the paper clearly written and well organized?
- Is there sufficient detail for reproduction by experts?

**Relevance**: Appropriate for the venue? Target audience interest?

**Experimental Rigor** (especially for robotics):
- Real robot vs. sim-only?
- Statistical significance and reproducibility?
- Multiple experiments varying substantially?
- Ablation studies?
- Appropriate baselines?
- Sim-to-real validation?

**Limitations and Honesty**:
- Limitations section?
- Honestly reported weaknesses?
- "Authors should be rewarded rather than punished for being up front about limitations" (NeurIPS)
- "Obvious shortcomings not reported by authors should be pointed out extensively" (CoRL)

### 1.1.17 What Distinguishes Accept from Reject

**Accept-Quality Papers**:
- Strong, clear contribution on at least one dimension
- Technically sound with well-supported claims
- Well-positioned relative to prior work
- Clear presentation enabling reproduction
- Significant rather than incremental results
- Honest about limitations
- **"Favor slightly flawed, impactful work over perfectly executed, low-impact work"** (HRI)

**Borderline Papers**:
- Technically correct, novel, relevant, clearly written, yet in a critical decision zone
- Significance becomes **"a highly subjective criterion based on 80% reviewer taste and 20% experience"**
- Area chairs consider strengths/weaknesses and their significance, not just average scores
- Even "good" papers can be pushed to borderline by identified issues
- Space constraints mean some sound papers must be rejected

**Reject-Quality Papers**:
- Technical flaws, weak evaluation, inadequate reproducibility
- Trivial variation on previous results
- Claims not supported by evidence
- Missing critical comparisons with prior work
- Poorly written
- Well-known results without new insight
- **"Technically correct but useless"** (Smith Category 4)

**Smith's Seven Categories (Accept/Reject Mapping)**:
- Categories 1-2: Clear accept (top ~10%)
- Category 3: Possible accept (10-30%)
- Categories 4-7: Reject

### 1.1.18 Robotics-Specific Standards

**Real-World Validation Expectations**:
- **IJRR**: "Results must be demonstrated by all relevant and applicable scientific means — be they mathematical proofs, statistically significant and reproducible experimental tests, field demonstrations, or whatever may be needed to convince a duly skeptical critical scientist."
- **CoRL Scope**: Must demonstrate relevance through explicitly addressing learning for physical robots OR testing on actual robotic systems
- Real robot experiments carry significantly more weight than simulation-only
- Simulation-only papers need strong justification for why real experiments were not possible

**Sim-to-Real Gap Standards**:
- Physical property sensitivity (center of mass, friction coefficients) must be acknowledged
- Paired simulation-real evaluation approaches preferred
- Visual realism gaps and dynamics gaps both matter
- Complex real-world tasks difficult to scale and replicate

**Practical Tips for Robotics Papers (Michael Milford)**:

*Paper Types*:
- **Type A**: Robot performing better at established tasks — emphasize performance delta
- **Type B**: Novel task/application/area — emphasize relevance to robotics field

*Three Contribution Types* (strength in one can offset weakness in others):
1. Novel theory
2. Performance breakthroughs
3. Self-evidently valuable new capability

*Key Advice*:
- **"Don't die on any unnecessary hills"** — make only claims essential to justifying your specific research direction
- Use real robots when possible; real-robot datasets otherwise
- Multiple experiments varying substantially prevent appearing as flukes
- Include one flagship experiment plus supporting data
- **"Candidly show your weaknesses"** so future researchers understand remaining gaps

**Robotics vs. General ML Differences**:
- Physical system validation carries unique weight
- Hardware limitations must be acknowledged
- Reproducibility has hardware cost and availability barriers
- Safety and ethical considerations for physical systems
- Domain-specific baselines may differ from standard ML benchmarks
- Timeliness of contributions matters (RA-L: "originality over maturity")

### 1.1.19 Common Rejection Reasons

**Technical Grounds**:
- Mathematical proofs unsound or incomplete
- Experimental design fundamentally flawed
- Results do not support claims
- Inappropriate statistical methods
- Missing ablation studies
- Insufficient baselines or unfair comparisons

**Novelty Grounds**:
- Trivial variation on existing work
- Well-known results without new insight
- Incremental rather than significant advance
- Missing critical related work showing overlap

**Presentation Grounds**:
- Too poorly written for technical evaluation (Smith Category 7)
- Paper not self-contained
- Insufficient detail for reproduction
- Disorganized or unclear logical flow

**Scope and Administrative**:
- Out of scope for venue
- Formatting violations / page limit exceeded
- Anonymity violations
- Dual submission detected
- Missing limitations section (where required)

**Robotics-Specific**:
- Simulation-only without justification
- Lack of comparison with relevant robotics baselines
- Failure to address practical deployment considerations
- Ignoring sim-to-real gap when claiming real-world applicability
- Testing only in highly controlled/simplified environments

### 1.1.20 Principles of Good Reviewing

**Constructive Adversarialism**:
- **RSS**: "Re-express the paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'"
- **COPE**: Be objective and constructive
- Corrective feedback points out errors; constructive feedback helps authors improve
- Number points of concern so authors can address them systematically

**Tone and Ethics**:
- **T-RO/RA-L**: "Any diminishing or disrespectful remark must be absolutely avoided"
- **CVPR**: Use third person ("the paper") not second person ("you")
- **Smith**: "Evaluations should target the paper itself, not the person"
- "The potential damage to authors' mental health and well-being when receiving an unfair and insensitive peer review should not be underestimated"

**Specificity and Evidence**:
- **NeurIPS**: "Do not make vague statements in your review, as they are unfairly difficult for authors to address"
- **NeurIPS**: "Superficial, uninformed reviews without evidence are worse than no review"
- Reference specific sections, figures, tables, page/line numbers
- "Write a courteous, informative, incisive, and helpful review that you would be proud to sign with your name" (CVPR)

**Balanced Assessment**:
- Start with positive aspects before constructive criticism
- Identify what you learned from the paper (RSS)
- List three contributions (NeurIPS 2019)
- Distinguish major issues from minor ones

**Actionability**:
- **NeurIPS 2019**: "What would the authors have to do for you to increase your score?"
- For favorable recommendations: list both necessary and suggested changes
- For rejection with salvageable work: suggest improvements and alternative venues
- "Not just noting deficiencies but also indicating how they can be mended" (RA-L)

### 1.1.21 Venue Standards Matrix (used by the review agent for calibration)

| Venue | Acceptance Rate | Expects Real Robot? | Formalization Required? | Insight Depth | Paper Type Emphasis |
|---|---|---|---|---|---|
| **IJRR** | ~20% (journal) | Strongly encouraged | Yes, deep | Maximum | Depth, completeness, thorough analysis |
| **T-RO** | ~25% (journal) | Strongly encouraged | Yes | High | Complete, mature work with broad evaluation |
| **RSS** | ~30% | Preferred | Preferred | High — values sharp, surprising insight | Novel insight; concise (8pp max) |
| **CoRL** | ~30% | Required for scope | Preferred | High | Learning + physical robots; emerging field |
| **RA-L** | ~40% | Expected | Helpful | Moderate | Timely, concise; originality over maturity |
| **ICRA** | ~45% | Preferred | Helpful | Moderate | Broad scope; solid contributions welcome |
| **IROS** | ~45% | Preferred | Helpful | Moderate | Systems and applications; breadth valued |

**Calibration Rules used by `adversarial-review` skill**:

**For IJRR/T-RO (journals)**:
- Apply ALL attack vectors at maximum depth
- Demand formal problem definition
- Expect comprehensive evaluation: real robot, multiple experiments, statistical rigor, ablations, failure analysis, comparisons
- "The quality level expected is at the absolute top of archival publications in robotics research" (IJRR)
- Length is not constrained — depth and completeness expected

**For RSS/CoRL (selective conferences)**:
- Prioritize attack vectors 3.1 (significance), 3.3 (challenge), and 3.4 (approach) — these venues value sharp insight over comprehensive evaluation
- Real-robot experiments expected; simulation-only is a serious weakness
- 8-page limit means density matters
- "Favor slightly flawed, impactful work over perfectly executed, low-impact work" (HRI principle, applicable here)

**For ICRA/IROS (broad conferences)**:
- Apply all attack vectors but with moderate thresholds
- Solid, incremental contributions acceptable if well-executed
- Systems-level contributions and applications valued
- The bar for novelty is lower; the bar for correctness remains high

**For RA-L (letters)**:
- Timeliness and originality weighted over maturity
- Conciseness expected — verbose papers are penalized
- Real-robot experiments expected
- "Originality over maturity" — promising early results acceptable

### 1.1.22 Appendix: Mapping to Venue Review Forms

This mapping tells the review agent how to translate the structured
findings into each venue's native review form.

| Review Guideline Section | RSS | CoRL | NeurIPS | ICML | ICLR | ICRA/IROS | T-RO/RA-L |
|---|---|---|---|---|---|---|---|
| 1. Summary | Paper Summary | Summary | Summary | Summary | Summary of contributions | Summary | Brief summary |
| 2. Chain Extraction | (in Justification) | (in Quality) | (in Strengths) | (in Claims & Evidence) | (in Strong/Weak points) | (in Detailed Review) | (in Overall Comments) |
| 3. Steel-Man | Points of Agreement + Learning Outcomes | (in Strengths) | Strengths | (in Other Aspects) | Strong points | (in Detailed Review) | (in Overall Comments) |
| 4. Fatal Flaws | Detailed Justification | Quality + Significance | Weaknesses | Claims & Evidence | Weak points | Detailed Review | Detailed items |
| 5. Serious Weaknesses | Detailed Justification | Quality assessment | Weaknesses | Other Aspects | Weak points | Detailed Review | Detailed items |
| 6. Minor Issues | Detailed Justification | (inline) | Weaknesses (minor) | Other Aspects | Suggestions | Detailed Review | Minor items list |
| 7. Questions | (in Justification) | (in review) | Questions | Questions for Authors | Clarifying questions | (in Detailed Review) | (in Overall Comments) |
| 8. Verdict | Quality Score (5-tier) + Impact | 6 dimensions scored | Overall (1-6) + Soundness/Presentation/Contribution (1-4) | Overall (1-5) | Overall {0,2,4,6,8,10} | Criteria assessments | Confidential recommendation |

### 1.1.23 Key Quotes That Drive the Review Agent

**On the Purpose of Review**:
> *"Editors and reviewers are not there to be inflexible judges; rather their role is to help authors write better papers."* — T-RO / RA-L

**On Evaluating Contributions**:
> *"Submissions bring value to the ICLR community when they convincingly demonstrate new, relevant, impactful knowledge — not contingent on benchmark dominance."* — ICLR 2026

> *"Originality does not necessarily require introducing an entirely new method."* — NeurIPS 2025

**On Limitations**:
> *"Honestly reported limitations should be treated kindly and with high appreciation. On the other hand, obvious shortcomings or flaws not reported by the authors should be pointed out extensively and be strongly reflected in your scores."* — CoRL

**On Impact vs. Perfection**:
> *"Favor slightly flawed, impactful work over perfectly executed, low-impact work."* — HRI 2026

**On Review Quality**:
> *"Superficial, uninformed reviews without evidence are worse than no review."* — NeurIPS

> *"Write a courteous, informative, incisive, and helpful review that you would be proud to sign with your name."* — CVPR

**On Balance**:
> *"Being too lenient produces poor scholarship and misinformation, while excessive criticism blocks legitimate research and damages careers."* — Smith

**On Understanding**:
> *"Re-express your paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'"* — RSS

**On Specificity**:
> *"Do not make vague statements in your review, as they are unfairly difficult for authors to address."* — NeurIPS

**On Robotics Quality**:
> *"Results must be demonstrated by all relevant and applicable scientific means — be they mathematical proofs, statistically significant and reproducible experimental tests, field demonstrations, or whatever may be needed to convince a duly skeptical critical scientist."* — IJRR

**On Subjectivity**:
> *"Significance is a highly subjective criterion based on 80% reviewer taste and 20% experience."* — NeurIPS 2023 Tutorial

### 1.1.24 Sources

**Official Venue Guidelines**:
- [RSS Review Process (2024)](https://roboticsconference.org/2024/reviewps/)
- [RSS Paper Review Form (2020)](https://roboticsconference.org/2019/12/04/review-form/)
- [RSS Call for Papers](https://roboticsconference.org/information/cfp/)
- [CoRL 2024 Instruction for Reviews](https://2024.corl.org/contributions/instruction-for-reviews)
- [CoRL 2023 Reviewer Guidelines](https://www.corl2023.org/reviewer-guidelines)
- [ICRA 2026 Call for Papers](https://2026.ieee-icra.org/contribute/call-for-icra-2026-papers-now-accepting-submissions/)
- [IROS Information for Reviewers](https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/information-for-reviewers)
- [T-RO Information](https://www.ieee-ras.org/publications/t-ro/)
- [IJRR Submission Guidelines](https://journals.sagepub.com/author-instructions/ijr)
- [RA-L Information for Reviewers](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-reviewers/)
- [HRI 2026 Reviewer Guidelines](https://humanrobotinteraction.org/2026/full-paper-reviewer-guidelines/)
- [NeurIPS 2024 Reviewer Guidelines](https://neurips.cc/Conferences/2024/ReviewerGuidelines)
- [NeurIPS 2025 Reviewer Guidelines](https://neurips.cc/Conferences/2025/ReviewerGuidelines)
- [ICML 2025 Reviewer Instructions](https://icml.cc/Conferences/2025/ReviewerInstructions)
- [ICLR 2026 Reviewer Guide](https://iclr.cc/Conferences/2026/ReviewerGuide)
- [CVPR 2022 Reviewer Tutorial](https://cvpr2022.thecvf.com/sites/default/files/2021-11/How%20to%20be%20a%20good%20reviewer-tutorials%20for%20cvpr2022%20reviewers.pptx.pdf)

**Foundational Texts**:
- [Alan Jay Smith, "The Task of the Referee" (1990)](https://www.cs.princeton.edu/~jrex/teaching/spring2005/fft/reviewing.html)
- [Smith PDF via PKU](https://cuibinpku.github.io/resources/reviewing-smith.pdf)
- [NeurIPS 2019 Reviewing Guidelines (Cortes/Larochelle)](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)
- [NeurIPS 2023 Tutorial: "What Can We Do About Reviewer #2?"](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/)

**Expert Advice and Guides**:
- [Michael Milford: Practical Tips for Writing Robotics Papers](https://michaelmilford.com/practical-tips-for-writing-robotics-conference-papers-that-get-accepted/)
- [COPE Ethical Guidelines for Peer Reviewers](https://publicationethics.org/guidance/guideline/ethical-guidelines-peer-reviewers)
- [Nature: How to Write a Thorough Peer Review](https://www.nature.com/articles/d41586-018-06991-0)
- [PLOS: How to Write a Peer Review](https://plos.org/resource/how-to-write-a-peer-review/)
- [AUTOLAB Resources (Ken Goldberg lab)](https://autolab.berkeley.edu/resources.shtml)
- [Stanford CS326 Review Guide](https://web.stanford.edu/class/cs326/review.html)
- [The Reality Gap in Robotics (arXiv)](https://arxiv.org/abs/2510.20808)

---

## 1.2 — Open-Source AI Research Agent Landscape

Source compilation from `guidelines/history/vibe_research_survey.md`.
This survey informed the (now-deferred) frontend plan. It is
preserved here for lineage and as reference if a future Phase-2
revives the visual dashboard.

### 1.2.1 Open-Source Research Agent Projects Evaluated

**GPT Researcher (github.com/assafelovic/gpt-researcher)**
- **Type**: Web app (two versions — lightweight FastAPI HTML/CSS/JS and production Next.js + React + TypeScript + Tailwind CSS)
- **Key UI patterns**: Single query input → real-time streaming progress via WebSocket/SSE, drag-and-drop local doc upload, multi-agent workflow triggering via LangGraph Cloud, `onResultsChange` callback for React integration, multi-format output (PDF, Word, Markdown)
- **What works**: Clean query-to-report workflow. NextJS frontend as reusable React component with `apiUrl`, `apiKey`, `defaultPrompt`, `onResultsChange` props. Docker deployment.
- **What doesn't**: Lightweight frontend is basic. Limited progress visualization documentation. No structured source evaluation/scoring. **Code quality: 2/10. Don't fork.** Multiple open XSS/RCE vulnerabilities, frontend issues stay open 12+ months. Study UX concepts only.
- **Relevance**: High for streaming progress pattern.

**STORM (github.com/stanford-oval/storm)**
- **Type**: Web app (Streamlit demo + hosted production at storm.genie.stanford.edu)
- **Key UI patterns**: Topic input → real-time research observation, hierarchical outline generation, full article generation with inline citations, **Co-STORM mind map visualization of collected knowledge**, discourse thread view of multi-agent conversation simulation, turn-based AI agent dialogue display
- **What works**: The mind map for Co-STORM is an excellent pattern for showing knowledge accumulation. 70K+ users on the hosted version. Discourse view makes agent reasoning transparent.
- **What doesn't**: Streamlit demo is minimal. Limited customization. **Code quality: 1/10. Throwaway.** 6 months stale, 2 contributors, open TLS vulnerability. Study the mind map data structure only.
- **Relevance**: Very high for the mind map / knowledge graph visualization pattern during research.

**PaperQA2 (github.com/Future-House/paper-qa)**
- **Type**: CLI only
- **Tech stack**: Python, Pydantic, LiteLLM, tantivy, httpx
- **Key patterns**: `pqa ask/search/view/index` commands, structured output (formatted_answer, answer, question, context with citation passages), automatic metadata enrichment (citation counts, retraction checks from Crossref/Semantic Scholar), bundled settings presets
- **What works**: Excellent answer quality with grounded citations. Good metadata integration. Clean programmatic API.
- **What doesn't**: No visual interface. No way to see the search/evaluation process.
- **Relevance**: Medium for UI (none), high for backend architecture. The structured answer format (question → context passages with citations → synthesized answer) is a good data model.

**Khoj (github.com/khoj-ai/khoj)**
- **Type**: Multi-platform (web, desktop, mobile, Obsidian plugin, Emacs, WhatsApp)
- **Tech stack**: Next.js 15 + React 18 + TypeScript + Radix UI + shadcn/ui + Tailwind + Mermaid + Excalidraw + KaTeX + markdown-it + Framer Motion + React Hook Form + Zod + Lucide React
- **Key patterns**: Chat-based primary interface, slash commands (/notes, /online, /image), deep research mode, document upload, custom agent configuration, chart/image/diagram generation inline, multi-format document support
- **What works**: Polished modern UI. Multi-platform approach means the web UI is well-tested. shadcn/ui + Radix gives accessible components. Mermaid for diagrams.
- **What doesn't**: Chat-centric UI may not be ideal for structured research workflows. No explicit paper evaluation/scoring interface. **AGPL-3.0 license forces open-sourcing any network-deployed modification.** Don't fork.
- **Relevance**: High for tech stack reference — the Next.js + shadcn/ui + Radix + Tailwind stack is a proven choice.

**OpenScholar (github.com/AkariAsai/OpenScholar)**
- **Type**: CLI + hosted demo (open-scholar.allen.ai)
- **Tech**: Python, Llama 3.1 8B, Contriever embeddings, Semantic Scholar API
- **Key patterns**: CLI-based `run.py`, simple query-and-answer interface on hosted demo, modular pipeline (retrieval → reranking → generation), citation attribution
- **What works**: State-of-the-art retrieval quality. Scientists preferred its responses over human experts 51% of the time. Good citation grounding.
- **What doesn't**: Minimal UI. No process visualization. No evaluation scoring visible to users.
- **Relevance**: Low for UI, high for understanding what the backend should produce.

**LatteReview (github.com/PouriaRouzrokh/LatteReview)**
- **Type**: Python library (no web UI)
- **Tech**: Python, Pandas, LiteLLM, async processing
- **Key patterns (programmatic)**:
  - **Multi-agent review** with customizable reviewer roles and expertise levels
  - **TitleAbstractReviewer**: 1-5 scoring + inclusion/exclusion criteria
  - **ScoringReviewer**: custom scoring by multiple agents
  - **AbstractionReviewer**: data extraction from abstracts/manuscripts
  - **Hierarchical review rounds** with filtering (junior reviewers → expert reviewers for disagreements)
  - Results as DataFrames with scoring metrics and reasoning transparency
- **What works**: Excellent multi-agent review workflow design. The hierarchical reviewer pattern (junior → expert) is a strong model. 1-5 scoring with criteria is exactly the rubric pattern needed.
- **What doesn't**: No visual interface. Output is CSV/DataFrame.
- **Relevance**: Very high for the evaluation/scoring data model and multi-agent review workflow. This is what a paper evaluation UI should display.

**LangGraph React Agent Studio (github.com/Ylang-Labs/langgraph-react-agent-studio)**
- **Type**: Full-stack web app
- **Tech**: React 19 + TypeScript + Tailwind + Radix UI; Python + FastAPI + LangGraph + LangChain; Redis (pub/sub), PostgreSQL, Docker
- **Key patterns**: Agent selection dashboard, real-time activity timeline with agent thought processes, tool execution visibility, WebSocket-powered streaming, conversation threading, live progress indicators
- **What works**: Production-quality real-time agent visualization. Redis pub/sub for streaming is robust. **The ActivityTimeline pattern is excellent.**
- **What doesn't**: **Code quality: 3/10.** 1 contributor, abandoned 9 months. Uses `window.location.reload()` as state management. Deeply LangGraph-coupled. Don't fork. Study the ActivityTimeline pattern (~130 lines).
- **Relevance**: Very high — closest example of a well-built agent dashboard with real-time state visualization.

### 1.2.2 Commercial Products (UI Pattern Analysis)

**Elicit (elicit.com)**
- **Key patterns**:
  - **Table-based results** — the core innovation. Papers as rows; users add columns for data extraction (intervention, outcomes, sample size, study design)
  - **Custom columns** — "Add Column" to specify what data to extract
  - **Column types**: Yes/No/Maybe (screening), Multiple-choice, Free-text extraction
  - **Cell citations** — click any cell to see supporting quotes
  - **Systematic Review workflow** — step-by-step guidance through search → screening → data extraction → report
  - Up to 20 columns, 1000 papers per table
- **What works**: **The table paradigm is extremely powerful for structured literature review.** Custom columns turn the AI into a structured data extraction tool. Citation transparency builds trust.
- **Relevance**: Very high. **The gold standard for paper evaluation interfaces.**

**Semantic Scholar (semanticscholar.org)**
- **Key patterns**: Minimalist search engine, **TLDR summaries** (AI-generated one-sentence paper summaries), Semantic Reader (augmented PDF with contextual citation cards), Research Feeds (personalized recommendations), **Highly Influential Citations** (filters citations by influence, not just count), citation graph navigation, quality indicators (citation counts, venue quality, study type badges)
- **What works**: TLDR summaries useful for scanning. Highly Influential Citations is a great filtering pattern. Clean, fast, free, widely used.
- **Relevance**: Medium. TLDR pattern and quality indicator badges are useful elements to adopt.

**Connected Papers (connectedpapers.com)**
- **Key patterns**:
  - **Force-directed graph** — papers as nodes, positioned by similarity (not direct citation)
  - **Node sizing** — larger bubbles = more citations
  - **Color gradient** — light to dark = older to newer
  - Hover preview, Prior Works view, Derivative Works view, influence highlighting, co-citation + bibliographic coupling
- **What works**: Immediately intuitive visualization. Similarity-based layout surfaces unexpected connections. Prior/Derivative Works views are powerful.
- **Relevance**: High for graph visualization. **The force-directed layout with size=citations and color=year is an excellent pattern.**

**ResearchRabbit (researchrabbit.ai)**
- **Key patterns**: Interactive bubble/node map, **color coding** (green = in collection, blue = suggested), hover interactions, column-based navigation (each column represents a search action, "hop back" to trace exploration), Collections with recommendations, author network view, drag-and-drop organization
- **What works**: **The color-coded bubble map (green=collected, blue=suggested) is an excellent pattern.** Column-based navigation preserves exploration history.
- **Relevance**: High. Collection + recommendation pattern and color-coded graph directly applicable.

**Consensus (consensus.app)**
- **Key patterns**: Search engine style, **Consensus Meter** (visual summary showing academic consensus, e.g., "85% of studies suggest Yes"), result tiles with paper title + extracted answer in grey text box + metadata, quality indicators, AI synthesis paragraph, detailed study view, 100+ language support
- **What works**: **The Consensus Meter is a unique and compelling pattern for showing aggregate research findings.** Result tiles with extracted answers (not just abstracts) are more useful than traditional search.
- **Relevance**: High. Consensus Meter pattern excellent for showing aggregate evaluation results.

**Litmaps (litmaps.com)**
- **Key patterns**: **Citation-based scatter plot** (X=publication year, Y=citation count), multiple seed papers, customizable axes, variable node size (based on metrics), import support (BibTeX, RIS, PubMed, Zotero), discovery feed
- **What works**: **The temporal scatter plot is more analytically useful than a force-directed graph for understanding research evolution.** Multiple seed papers give more comprehensive coverage.
- **Relevance**: Medium-high. Chronological citation visualization is a complementary pattern.

### 1.2.3 UI Pattern Categories and Recommendations

**A. Agent State Machine / Progress Visualization**

Best patterns observed:
1. **Activity timeline** (LangGraph Agent Studio) — vertical timeline with status indicators, reasoning, results
2. **SSE streaming with structured events** — typed events (step_start, step_update, waiting_human)
3. **AG-UI Protocol** — emerging standard with ~16 event types across 5 categories. Adopted by Microsoft, Oracle.
4. **useStream hook** (LangChain) — framework-agnostic React/Vue/Svelte hook for agent streams

**Recommended**: SSE or WebSocket streaming with structured event types. Collapsible activity timeline. Current state prominently displayed.

Key libraries: XState + Stately Studio (state machine definition), React Flow (DAG rendering), AG-UI Protocol (standardized agent events).

**B. Paper Evaluation / Scoring UI**

Best patterns:
1. **Elicit's table with custom columns** — papers as rows, criteria as columns, click cells for source citations
2. **LatteReview's multi-agent scoring** — 1-5 scale, multiple reviewers, hierarchical rounds
3. **Consensus quality indicators** — badges for study type, journal quality, citation count

**Recommended**: Analytic rubric table (papers × criteria), expandable cells for AI reasoning + quotes, radar or horizontal bar chart per criterion, quality indicator badges.

**C. Knowledge Graph / Paper Relationship Visualization**

Best patterns:
1. **Connected Papers' force-directed graph** — size=citations, color=year, position=similarity. Most intuitive.
2. **ResearchRabbit's interactive bubble map** — color=collection status, hover=preview, drag=organize
3. **Litmaps' temporal scatter** — X=year, Y=citations, lines=citation relationships. Most analytical.
4. **STORM's mind map** — hierarchical concept structure built progressively. Shows knowledge accumulation.

Key libraries: Sigma.js + graphology (large graphs, WebGL), Cytoscape.js (mature), Reagraph (WebGL React), React Flow (DAG), D3.js (maximum customization).

**Recommended**: Force-directed graph primary (Connected Papers style) with timeline/scatter secondary (Litmaps style). Progressive graph build during research (STORM pattern).

**D. Research Dashboard Design**

Best patterns:
1. **Elicit's systematic review workflow** — search → screen → extract → report
2. **GPT Researcher's query-to-report flow** — single input, streaming progress, formatted output
3. **Khoj's slash-command chat** — flexible but with structured outputs
4. **LangGraph Agent Studio's multi-panel** — agent selector + chat + activity timeline

**Recommended layout**:
- **Left panel**: Research configuration (query, parameters, rubric criteria)
- **Center panel**: Live agent activity feed / progress timeline (collapsible steps)
- **Right panel**: Knowledge graph building in real-time
- **Bottom/tab panel**: Paper evaluation table (Elicit-style)
- **Top bar**: Research phase indicator (Searching → Evaluating → Synthesizing → Complete)

### 1.2.4 Recommended Tech Stack (for future Phase-2)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | **Next.js 15+ (App Router)** | Used by Khoj, GPT Researcher. SSR + streaming support. |
| UI Components | **shadcn/ui + Radix UI** | Used by Khoj. Accessible, customizable, unopinionated. |
| Styling | **Tailwind CSS** | Used by all major projects. |
| State Management | **XState** (agent state) + **React hooks** (UI state) | XState for formal state machine. |
| Graph Visualization | **Cytoscape.js** or **Sigma.js** | Cytoscape for features, Sigma for performance. |
| Workflow Visualization | **React Flow** | For agent DAG/pipeline. |
| Diagrams | **Mermaid** | Good for auto-generated diagrams. |
| Charts | **Recharts** | 3.0 update in 2025. |
| Streaming | **SSE + useStream** or **AG-UI Protocol** | Standardized agent-to-UI. |
| Animations | **Framer Motion** | Smooth progressive disclosure. |
| Markdown | **markdown-it** or **react-markdown** | |
| Math | **KaTeX** | |
| Backend API | **FastAPI + WebSocket/SSE** | Python backend with streaming. |

### 1.2.5 Key Takeaways

1. **No single tool does everything well.** The best research agent UI would combine Elicit's table-based evaluation, Connected Papers' graph visualization, GPT Researcher's streaming progress, and STORM's progressive knowledge building.

2. **The table is the killer pattern for paper evaluation.** Elicit proved a spreadsheet-like interface with AI-populated columns is more useful than chat for structured literature review.

3. **Progressive knowledge visualization is underserved.** Most tools show a static graph after research. STORM's progressive mind map during research is the right pattern but poorly implemented (Streamlit limitations).

4. **Agent transparency matters.** Users want to see what the agent is doing in real-time, not just the final result.

5. **The AG-UI Protocol is emerging as a standard** for agent-to-frontend communication.

6. **The Next.js + shadcn/ui + Tailwind stack is the consensus choice** among well-funded open-source projects (Khoj, GPT Researcher production frontend).

### 1.2.6 CopilotKit — evaluated as potential framework

**CopilotKit** (30k stars, MIT) was evaluated separately as a
framework candidate for the deferred frontend:
- Provides real-time agent streaming (AG-UI protocol), chat UI,
  **generative UI** (agent invokes React components with structured
  data), human-in-the-loop hooks
- MIT license, active development, 86k weekly npm downloads
- AG-UI protocol explicitly supports custom Python backends without
  LangGraph
- **Code quality: 8/10. Production-grade.**

**Decision (at the time of the frontend plan, now deferred)**: Use
CopilotKit as framework + custom views (evaluation table, knowledge
graph) that CopilotKit's agent can invoke via generative UI.

**Fallback plan if CopilotKit AG-UI proved unreliable**: drop
CopilotKit, use raw SSE + custom React hooks (adds ~3 days of work).

---

## Round 2 — (placeholder)

When future surveys are conducted, they append here without
disturbing Round 1. Suggested topics if a Phase-2 frontend is
revived:

- Updated landscape of AG-UI / A2A / MCP ecosystem post-April 2026
- Practical CopilotKit integration experience with custom Python backends
- TanStack Table vs. AG Grid for rubric-dense data
- Cytoscape.js vs. Sigma.js for 500+ node knowledge graphs
- Survey of "research notebook" interfaces (Notion-style + structured data)

---

*This document is rewriteable. The append-only log lives in
`docs/LOGS.md`.*
