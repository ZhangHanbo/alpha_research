# Comprehensive Reference: Research Paper Review Standards for Top Robotics & AI Venues

This document compiles reviewer guidelines, evaluation criteria, scoring rubrics, and expert advice from top robotics and AI conferences/journals. It is intended to inform the design of an adversarial review agent for robotics research.

---

## TABLE OF CONTENTS

1. [Venue-Specific Reviewer Guidelines](#1-venue-specific-reviewer-guidelines)
   - 1.1 RSS (Robotics: Science and Systems)
   - 1.2 CoRL (Conference on Robot Learning)
   - 1.3 ICRA (IEEE International Conference on Robotics and Automation)
   - 1.4 IROS (IEEE/RSJ International Conference on Intelligent Robots and Systems)
   - 1.5 T-RO (IEEE Transactions on Robotics)
   - 1.6 IJRR (International Journal of Robotics Research)
   - 1.7 RA-L (IEEE Robotics and Automation Letters)
   - 1.8 HRI (ACM/IEEE International Conference on Human-Robot Interaction)
   - 1.9 NeurIPS
   - 1.10 ICML
   - 1.11 ICLR
   - 1.12 CVPR
2. [Foundational Texts on Reviewing](#2-foundational-texts-on-reviewing)
   - 2.1 Alan Jay Smith -- "The Task of the Referee"
   - 2.2 NeurIPS 2023 Tutorial -- "What Can We Do About Reviewer #2?"
   - 2.3 NeurIPS 2019 -- Corinna Cortes / Hugo Larochelle Guidelines
3. [Unified Evaluation Framework](#3-unified-evaluation-framework)
4. [What Distinguishes Accept from Reject](#4-what-distinguishes-accept-from-reject)
5. [Robotics-Specific Standards](#5-robotics-specific-standards)
6. [Common Rejection Reasons](#6-common-rejection-reasons)
7. [Principles of Good Reviewing](#7-principles-of-good-reviewing)
8. [Key Quotes and Principles](#8-key-quotes-and-principles)
9. [Sources](#9-sources)

---

## 1. VENUE-SPECIFIC REVIEWER GUIDELINES

### 1.1 RSS (Robotics: Science and Systems)

**Review Form (8 components):**

1. **Expertise Assessment**: Reviewer rates familiarity with subject matter
2. **Paper Summary**: Must "re-express your paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'"
3. **Points of Agreement**: Identification of consensus areas, particularly non-standard ones
4. **Learning Outcomes**: What insights the reviewer gained from the paper
5. **Quality Score** (5-tier):
   - **Excellent**: Standout papers from the past year
   - **Very Good**: Solid, important contributions
   - **Good**: Flawed but valuable
   - **Fair**: Developing but incomplete
   - **Poor**: Requires substantial revision
6. **Impact Checkbox**: Whether the work differs meaningfully from typical submissions with potential community influence
7. **Detailed Justification**: Thorough analysis of strengths, weaknesses, contributions, impact potential, and improvement suggestions
8. **Confidential Comments**: Optional notes for the papers committee only

**Process**: Two-stage process with threshold decision in Round 1. Papers receiving at least one recommendation of Weak Accept (WA) or higher advance to revision (3 weeks). Recommendations: Accept (A), Weak Accept (WA), Weak Reject (WR), Reject (R). Round 2 results are either Accept with Minor Revisions or Reject.

**Key Policy**: Maximum 8 pages excluding references. "This is a ceiling, not a floor, and reviewers are likely to look favorably upon papers that are not unnecessarily long or verbose."

**Desk Rejection Criteria**: Incomplete submissions (placeholder titles, abruptly ending papers), non-anonymized papers, formatting errors, out of scope, not in English.

Sources: [RSS Review Process](https://roboticsconference.org/2024/reviewps/), [RSS Review Form](https://roboticsconference.org/2019/12/04/review-form/)

---

### 1.2 CoRL (Conference on Robot Learning)

**Six Evaluation Dimensions:**

1. **Originality**: Are the problems or methods new? Is it a novel combination of well-known techniques? Evaluate novelty, differentiation from prior work, citation adequacy.
2. **Quality**: Technical soundness, whether claims receive empirical or theoretical support, methodological appropriateness, completeness.
3. **Clarity**: Organization, readability, sufficient detail for expert reproduction.
4. **Significance**: Practical impact, likelihood of adoption, advancement of state-of-the-art, theoretical/experimental uniqueness.
5. **Relevance**: Does the paper address robot learning? Does it apply or improve a learning-based method or learned model? Is it evaluated in simulation, on real robots, or both? Will the CoRL audience be interested?
6. **Limitations**: Papers must include a limitations section. "Honestly reported limitations should be treated kindly and with high appreciation." Unreported obvious flaws warrant strong criticism.

**Scope Requirements**: Submissions must demonstrate relevance through either:
- Explicitly addressing a learning question for physical robots, OR
- Testing proposed solutions on actual robotic systems

**Reviewer Qualifications**: Minimum 3 first-author publications in major robotics venues (CoRL, RSS, ICRA, IROS, IJRR, TRO, RAL) and core ML venues (NeurIPS, ICML, AIStats, JMLR, PAMI).

**Key Principle**: "Be constructive and concrete; be courteous and respectful. Start with the positive aspects, suggest improvements, and accept diverse views in a discussion." Avoid blanket rejections based on single factors (lack of novelty alone, missing datasets, absence of theorems).

Sources: [CoRL 2024 Instructions](https://2024.corl.org/contributions/instruction-for-reviews), [CoRL 2023 Guidelines](https://www.corl2023.org/reviewer-guidelines)

---

### 1.3 ICRA (IEEE International Conference on Robotics and Automation)

**Evaluation Criteria**: Originality, significance, technical quality, and clarity of presentation.

**Review Board Structure**: Editor-in-Chief (EiC), Senior Editors, ~400 Associate Editors, and several hundred Reviewers. Each paper is assigned to one Editor and one AE, with a minimum of two high-quality reviews per paper.

**Process**: Rigorous peer review with plagiarism checks, formatting adherence, and page limit verification. Each paper assigned to expert reviewers who are specialists in the relevant field.

**AI Policy**: Generative AI tools may not be listed as authors. AI-generated content must be disclosed in acknowledgments with specific sections identified.

Source: [ICRA 2026 Call for Papers](https://2026.ieee-icra.org/contribute/call-for-icra-2026-papers-now-accepting-submissions/)

---

### 1.4 IROS (IEEE/RSJ International Conference on Intelligent Robots and Systems)

**Structure**: IROS Conference Paper Review Board (ICPRB) consists of EiC, 27 Senior Editors, ~400 Associate Editors, and several hundred Reviewers. Each paper gets minimum two high-quality reviews.

**Review Requirements**:
- Minimum 1,200 non-white character threshold per review (to ensure substantive feedback)
- Must include: confidence statement, criteria assessments, potential confidential statement to ICPRB, and detailed review describing contribution and justifying overall assessment

**Conflict of Interest**: Co-author, student/advisor relationship, co-authored paper or close collaboration in previous 5 years, same institution at department/division level.

Source: [IROS Information for Reviewers](https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/information-for-reviewers)

---

### 1.5 T-RO (IEEE Transactions on Robotics)

**Key Principle**: "Editors and reviewers are not there to be inflexible judges; rather their role is to help authors write better papers."

**Suggested Evaluation Areas**:
- Paper contribution and significance
- Clarity of explanation and organization
- Purpose statement in introduction
- Reference completeness and relevance
- Technical soundness
- Paper length and condensation possibilities

**Review Format**:
1. Brief summary demonstrating comprehension
2. Overall comments summarizing opinion (excluding publication recommendation in author-visible section)
3. Detailed list of minor items (grammar, notation, figure improvements)
4. Confidential comments for Editorial Board only

**Critical Instructions**:
- Do not identify yourself within review text
- Avoid explicit acceptance/rejection statements in author comments
- Provide specific, detailed feedback with references to similar work
- Comment on multimedia attachments regarding consistency and technical quality
- AI-generated review content is prohibited (grammar enhancement tools acceptable with disclosure)

**Reviewer Obligation**: By submitting to T-RO, authors agree to provide up to 3 high-quality reviews of other T-RO submissions if called upon.

Source: [T-RO Information](https://www.ieee-ras.org/publications/t-ro/), [IEEE RAS Review Process](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-reviewers/)

---

### 1.6 IJRR (International Journal of Robotics Research)

**Quality Standard**: "The quality level expected in a paper to appear in IJRR is at the absolute top of archival publications in robotics research."

**Publication Criteria**: IJRR only publishes work of archival value which advances science and technology. To do so it must be:
- **Original**: Novel contribution
- **Solid**: Results demonstrated by all relevant scientific means -- mathematical proofs, statistically significant and reproducible experimental tests, field demonstrations, "or whatever may be needed to convince a duly skeptical critical scientist"
- **Useful to others**: Practical and/or theoretical impact

**Specific Standards**:
- Results should represent a **significant rather than incremental advance**
- Results must be **verified appropriately** according to the topic
- **Experimental results are strongly encouraged**
- Must include **up-to-date literature review** and **meaningful comparisons with previous work**
- Application of theoretical advances to real problems and data is encouraged
- Code and data sharing highly recommended for reproducibility
- **No a priori space limit**: "A paper should be as long as necessary, but no longer"

**Reviewer Qualifications**: Only researchers who have already published in prestigious robotics journals. Graduate students should not be assigned reviews.

**Review Process**: Single-blind, minimum two expert reviewers.

Source: [IJRR Submission Guidelines](https://journals.sagepub.com/author-instructions/ijr)

---

### 1.7 RA-L (IEEE Robotics and Automation Letters)

**Quality Standard**: "A RA Letter is a timely and concise account of innovative research ideas and application results." Comparable to short papers in T-RO or T-ASE, though "the requirement of timeliness favours originality over maturity."

**Review Principles**:
- "Review comments and recommendation reports should be constructive in their criticism, not just noting deficiencies but also indicating how they can be mended"
- "Any diminishing or disrespectful remark must be absolutely avoided"

**Review Format**:
1. Summary of paper's main contributions (in reviewer's own words)
2. Evaluation of related work coverage
3. Assessment of strengths and weaknesses with constructive suggestions
4. Specific editing recommendations (figures, typos, clarity)
5. Overall evaluation and recommendation summary

**Key Evaluation Questions**:
- What is the paper's contribution?
- Does it explain significance clearly?
- Is writing and organization adequate?
- Does the introduction state purpose?
- Are references relevant and complete?
- Is the technical approach sound?
- Is length appropriate?

**Timeline**: 30 days to review original manuscripts, 14 days for re-reviews. Publication within 6 months from submission -- no exceptions.

**Process**: Double-anonymous review (as of February 2025).

Source: [RA-L Information for Reviewers](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-reviewers/)

---

### 1.8 HRI (ACM/IEEE International Conference on Human-Robot Interaction)

**Overall Rating Scale** (5-point, note inverted):
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

**Suggested Review Structure**:
1. Summary: Brief overview of work and findings
2. Strengths/Weaknesses: Bulleted or paragraph format
3. Detailed Comments: Expand on assessment with track-specific criteria
4. Suggestions for Improvement: Concrete, actionable steps
5. Recommendation: Clear statement supporting numeric score

**Key Philosophy**: "Favor slightly flawed, impactful work over perfectly executed, low-impact work."

**Track-Specific Evaluation**: Five tracks (User Studies, Design, Technical, System, Theory & Methods) with track-specific expectations.

**Target acceptance rate**: ~25%.

Source: [HRI 2026 Reviewer Guidelines](https://humanrobotinteraction.org/2026/full-paper-reviewer-guidelines/)

---

### 1.9 NeurIPS

**Review Form (11 sections):**

1. **Summary**: Brief overview authors would recognize (not for critique)
2. **Strengths & Weaknesses**: Four-dimensional assessment
3. **Questions**: Points addressable during rebuttal
4. **Limitations**: Adequacy of author's limitations discussion
5. **Ethical Concerns**: Flag for ethics review if needed
6. **Soundness Rating** (1-4): Technical claims, experimental and research methodology
7. **Presentation Rating** (1-4): Writing clarity and contextualization
8. **Contribution Rating** (1-4): Research area significance
9. **Overall Score** (1-10 for 2024; 1-6 for 2025)
10. **Confidence Score** (1-5)
11. **Code of Conduct Acknowledgment**

**Four Evaluation Dimensions:**
- **Originality**: Novelty, task/method newness, differentiation from prior work, citation adequacy. "Does not necessarily require introducing an entirely new method." Novel insights from evaluating existing approaches count.
- **Quality**: Technical soundness, claim support, methodology appropriateness, completeness, author honesty about strengths/weaknesses
- **Clarity**: Writing quality, organization, reader informativeness, reproducibility sufficiency
- **Significance**: Result importance, likelihood of use/building upon, state-of-art advancement, unique contributions

**NeurIPS 2024 Overall Score (1-10):**
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

**NeurIPS 2025 Overall Score (1-6):**
- 6: Strong Accept -- "Technically flawless paper with groundbreaking impact"
- 5: Accept -- "Technically solid paper, with high impact on at least one sub-area"
- 4: Borderline Accept -- "Reasons to accept outweigh reasons to reject"
- 3: Borderline Reject -- "Reasons to reject outweigh reasons to accept"
- 2: Reject -- "Technical flaws, weak evaluation, inadequate reproducibility"
- 1: Strong Reject -- "Well-known results or unaddressed ethical considerations"

**Confidence Scale (1-5):**
- 5: Absolutely certain
- 4: Confident
- 3: Fairly confident
- 2: Willing to defend (likely gaps)
- 1: Educated guess

**Critical Instructions**:
- "Do not make vague statements in your review, as they are unfairly difficult for authors to address."
- "Superficial, uninformed reviews without evidence are worse than no review."
- "Authors should be rewarded rather than punished for being up front about" limitations.
- "3-5 actionable points where author responses could change your opinion."

**NeurIPS 2019 Innovation (Cortes/Larochelle era)**:
- Reviewers must "list three things this paper contributes" to encourage reflection on strengths
- Must answer: "What would the authors have to do for you to increase your score?"

Sources: [NeurIPS 2024 Guidelines](https://neurips.cc/Conferences/2024/ReviewerGuidelines), [NeurIPS 2025 Guidelines](https://neurips.cc/Conferences/2025/ReviewerGuidelines), [NeurIPS 2019 Medium Post](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)

---

### 1.10 ICML

**Review Form Sections:**

1. **Summary**: Objective overview without critique
2. **Claims and Evidence**: Whether claims have clear, convincing support; method/evaluation criteria appropriateness
3. **Relation to Prior Works**: Contextualize within broader literature
4. **Other Aspects**: Originality, significance, clarity, strengths, weaknesses
5. **Questions for Authors**: Only where responses would materially change evaluation
6. **Ethical Issues**: Discrimination/bias, inappropriate applications, privacy, legal compliance
7. **Code of Conduct**: Affirm adherence

**Overall Recommendation Scale (1-5):**
- 5: Strong Accept
- 4: Accept
- 3: Weak Accept (leaning toward acceptance)
- 2: Weak Reject (leaning toward rejection)
- 1: Reject

**Application-Driven Paper Guidance**:
- Assess whether approaches address real-world problem requirements
- Encourage use-informed datasets with proper documentation
- Consider non-ML approaches alongside ML baselines
- Accept novel method combinations, datasets, or evaluation frameworks
- Value impact on important applications, not solely ML community advancement

**Key Principles**:
- "Review papers as you would wish yours reviewed"
- "Read carefully, critically, and empathetically"
- Recognize varied forms of originality: creative combinations, removed assumptions, real-world applications
- AI tools prohibited for writing reviews
- Must explicitly acknowledge authors' rebuttals

Source: [ICML 2025 Reviewer Instructions](https://icml.cc/Conferences/2025/ReviewerInstructions)

---

### 1.11 ICLR

**Core Evaluation Framework (4 key questions):**

1. **Research Question**: What is the specific question/problem tackled?
2. **Motivation & Context**: Is the approach well-motivated and properly situated in existing literature?
3. **Evidence & Validity**: Do results support claims with scientific rigor?
4. **Significance**: Does it contribute new knowledge and sufficient value? "State-of-the-art results are not required."

**Review Structure Requirements:**
- Summary of claimed contributions (positive, constructive tone)
- Comprehensive strong and weak points
- Clear initial recommendation (accept/reject) with key justifications
- Supporting arguments
- Clarifying questions for authors
- Constructive improvement suggestions (labeled as non-decision factors)

**Overall Rating (ICLR 2026):** {0, 2, 4, 6, 8, 10}
**Overall Rating (ICLR 2024-2025):** {1, 3, 5, 6, 8, 10}

**Contribution Value**: "Submissions bring value to the ICLR community when they convincingly demonstrate new, relevant, impactful knowledge" across empirical, theoretical, or practitioner domains -- not contingent on benchmark dominance.

**Quality Enforcement**: Late or low-quality reviews trigger penalties: author-reviewers lose access to their own paper reviews until completing assignments; persistently poor reviewers face desk rejection of their submissions.

**LLM Disclosure**: Reviewers must disclose any LLM usage; non-disclosure risks desk rejection of their own papers.

Source: [ICLR 2026 Reviewer Guide](https://iclr.cc/Conferences/2026/ReviewerGuide)

---

### 1.12 CVPR

**Key Principles from CVPR Reviewer Tutorial:**

- **Be Specific and Concrete**: Avoid vague statements like "the paper is interesting." Provide detailed feedback referencing specific sections, figures, and tables.
- **Embrace Novel Ideas**: "Look for what is good or stimulating in the paper, and embrace novel, brave concepts, even if they have not been tested on many datasets."
- **Maintain Tone**: "A harshly written review will be resented by the authors." Use third person ("the paper") not second person ("you").
- **Structure**: Explain key ideas, contributions, and significance. Clearly explain why the paper should be accepted or not. Final justification should show how strengths and weaknesses were weighed.
- **Be Generous**: "The most valuable comments in a review are those that help the authors understand the shortcomings of their work and how they might improve it."

Source: [CVPR 2022 Reviewer Tutorial](https://cvpr2022.thecvf.com/sites/default/files/2021-11/How%20to%20be%20a%20good%20reviewer-tutorials%20for%20cvpr2022%20reviewers.pptx.pdf)

---

## 2. FOUNDATIONAL TEXTS ON REVIEWING

### 2.1 Alan Jay Smith -- "The Task of the Referee" (1990)

Published in IEEE Computer, Vol. 23, 1990, pp. 65-71. One of the most cited guides on paper reviewing in computer science.

**Core Referee Task**: Evaluate in a timely manner whether a paper makes a sufficient contribution, determining:
1. Is the work **correct**?
2. Is the problem studied and results obtained **new and significant**?
3. Is the quality of **presentation** satisfactory?
4. What **revisions** are necessary/desirable?

**Seven-Category Paper Classification:**
1. Major results; very significant (<1% of submissions)
2. Good, solid, interesting work; definite contribution (<10%)
3. Minor but positive contribution to knowledge (10-30%)
4. Technically correct but useless ("sophisticated analyses of flying pigs")
5. Neither elegant nor useful, but factually accurate
6. Wrong and misleading
7. Too poorly written for technical evaluation

**Evaluation Framework:**

*Novelty and Significance:*
- Is the problem real and clearly stated?
- Has this work been done previously?
- Is it "a trivial variation on or extension of previous results"?
- Is the problem obsolete or lacking general applicability?

*Methodological Validity:*
- Are assumptions realistic and clearly presented?
- Is the approach sufficient for the stated purpose?
- Can the method be understood clearly, or is it obscured by mathematical formulas?

*Correctness Assessment:*
- Are mathematical proofs sound?
- Are statistical methods appropriate?
- Do results align with stated assumptions and observed facts?
- Have boundary conditions been properly tested?

*Presentation Quality:*
- Does the abstract accurately represent the paper?
- Is the logical flow clear and organized?
- Is technical content understandable to qualified readers?
- Are figures, tables, and references appropriate?

**Report Structure:**
1. Brief recommendation statement with justifications
2. 1-5 sentence summary demonstrating understanding
3. Assessment of research validity and significance
4. Evaluation of work quality (methodology, techniques, accuracy, presentation)
5. Clear overall recommendation with adequate supporting discussion

**Key Principles:**
- "Being too lenient produces poor scholarship and misinformation, while excessive criticism blocks legitimate research and damages careers."
- Evaluate against the specific publication's average standards, not personal benchmarks.
- Target the paper, not the person. Remain "objective and fair" since "the more psychologically acceptable the review, the more useful it will be."
- For rejection: explain why. For favorable: list both necessary and suggested changes.
- Avoid detailed critique of "a badly flawed paper that can never be made publishable" when "fatal and uncorrectable flaws" exist.

Source: [Full text via Princeton](https://www.cs.princeton.edu/~jrex/teaching/spring2005/fft/reviewing.html), [PDF](https://cuibinpku.github.io/resources/reviewing-smith.pdf)

---

### 2.2 NeurIPS 2023 Tutorial -- "What Can We Do About Reviewer #2?"

Presented by Nihar B. Shah (CMU). Panelists: Alice Oh (NeurIPS 2022 PC), Hugo Larochelle (EIC, TMLR), Andrew McCallum (OpenReview), Mausam.

**Key Findings on Peer Review:**
- Provides a scientific lens on systemic issues in peer review
- Addresses inherent challenges through experiments on peer-review processes across disciplines
- Discusses viable solutions and important open problems
- Significance is "a highly subjective criterion based on 80% reviewer taste and 20% experience"
- Even for "good" papers, it is "rather easy to come up with issues that push it into borderline status"

Source: [Tutorial Page](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/), [Slides PDF](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/TutorialSlides2023.pdf)

---

### 2.3 NeurIPS 2019 Guidelines (Cortes/Larochelle Era)

**Two Key Innovations:**

1. **Contributions Assessment**: Reviewers must "list three things this paper contributes" -- theoretical, methodological, algorithmic, or empirical. For each, "briefly state the level of significance." Rationale: encourages reviewers to "actively reflect on the strengths of a submission, and not merely focus on finding issues or weaknesses."

2. **Constructive Improvement Guidance**: Reviewers answer: "What would the authors have to do for you to increase your score?" Encourages "more constructive reviews" through specific, actionable feedback.

Source: [NeurIPS 2019 Medium Post](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)

---

## 3. UNIFIED EVALUATION FRAMEWORK

Synthesizing across all venues, the core evaluation dimensions are:

### 3.1 Technical Soundness / Correctness
- Are claims supported by evidence (theoretical proofs, experiments)?
- Are mathematical derivations correct?
- Are statistical methods appropriate and properly applied?
- Are experimental designs valid?
- Are assumptions realistic and clearly stated?
- Have boundary conditions been tested?

### 3.2 Novelty / Originality
- Is the problem new? Is the method new? Is the combination new?
- How does this differ from prior work?
- Is it a trivial extension or a significant departure?
- Are related works adequately cited and compared?
- Note: "Originality does not necessarily require introducing an entirely new method" (NeurIPS 2025)

### 3.3 Significance / Impact
- Does this advance the state of the art?
- Will others build on this work?
- Does it address an important problem?
- What is the potential for scientific and technological impact?
- Note: "State-of-the-art results are not required" (ICLR 2026)

### 3.4 Clarity / Presentation
- Is the paper clearly written and well organized?
- Is there sufficient detail for reproduction by experts?
- Does the abstract accurately represent the paper?
- Are figures, tables, and references appropriate?

### 3.5 Relevance
- Is the paper appropriate for the venue?
- Will the target audience be interested?
- Does it address the venue's core topics?

### 3.6 Experimental Rigor (especially for robotics)
- Real robot experiments vs. simulation-only?
- Statistical significance and reproducibility?
- Multiple experiments varying substantially?
- Ablation studies?
- Comparison with appropriate baselines?
- Sim-to-real transfer validation?

### 3.7 Limitations and Honesty
- Does the paper include a limitations section?
- Are weaknesses honestly reported?
- "Authors should be rewarded rather than punished for being up front about limitations" (NeurIPS)
- "Obvious shortcomings not reported by the authors should be pointed out extensively" (CoRL)

---

## 4. WHAT DISTINGUISHES ACCEPT FROM REJECT

### Accept-Quality Papers:
- Strong, clear contribution on at least one dimension (novelty, performance, new capability)
- Technically sound with claims well-supported
- Well-positioned relative to prior work
- Clear presentation enabling reproduction
- Results that are significant rather than incremental
- Honest about limitations
- "Favor slightly flawed, impactful work over perfectly executed, low-impact work" (HRI)

### Borderline Papers:
- Technically correct, novel, relevant, and clearly written, yet in a critical decision zone
- Significance becomes "a highly subjective criterion based on 80% reviewer taste and 20% experience"
- Area chairs consider strengths/weaknesses and their significance, not just average scores
- Even "good" papers can be pushed to borderline by identified issues
- Space constraints mean some sound papers must be rejected

### Reject-Quality Papers:
- Technical flaws, weak evaluation, inadequate reproducibility
- Trivial variation on or extension of previous results
- Claims not supported by evidence
- Missing critical comparisons with prior work
- Poorly written to the point of obscuring technical content
- Well-known results presented without significant new insight
- "Technically correct but useless" (Smith Category 4)

### Smith's Seven Categories (Accept/Reject Mapping):
- Categories 1-2: Clear accept (top ~10% of submissions)
- Category 3: Possible accept (10-30%)
- Categories 4-7: Reject

---

## 5. ROBOTICS-SPECIFIC STANDARDS

### 5.1 Real-World Validation Expectations
- **IJRR**: "Results must be demonstrated by all relevant and applicable scientific means -- be they mathematical proofs, statistically significant and reproducible experimental tests, field demonstrations, or whatever may be needed to convince a duly skeptical critical scientist."
- **CoRL Scope**: Must demonstrate relevance through explicitly addressing learning for physical robots OR testing on actual robotic systems
- Real robot experiments carry significantly more weight than simulation-only results
- Simulation-only papers need strong justification for why real experiments were not possible

### 5.2 Sim-to-Real Gap Standards
- Physical property sensitivity (center of mass, friction coefficients) must be acknowledged
- Paired simulation-real evaluation approaches preferred
- Visual realism gaps and dynamics gaps both matter
- Complex real-world tasks are difficult to scale and replicate with sufficient reproducibility

### 5.3 Practical Tips for Robotics Papers (Michael Milford)

**Paper Types:**
- Type A: Robot performing better at established tasks -- emphasize performance delta
- Type B: Novel task/application/area -- emphasize relevance to robotics field

**Three Contribution Types** (strength in one can offset weakness in others):
1. Novel theory
2. Performance breakthroughs
3. Self-evidently valuable new capability

**Key Advice:**
- "Don't die on any unnecessary hills" -- make only claims essential to justifying your specific research direction
- Use real robots when possible; real-robot datasets otherwise
- Multiple experiments varying substantially prevent appearing as flukes
- Include one flagship experiment plus supporting data
- "Candidly show your weaknesses" so future researchers understand remaining gaps
- Mediocre performance across all three contribution types is difficult to sell

### 5.4 Robotics vs. General ML Differences
- Physical system validation carries unique weight
- Hardware limitations and real-world conditions must be acknowledged
- Reproducibility has hardware cost and availability barriers
- Safety and ethical considerations for physical systems
- Domain-specific baselines may differ from standard ML benchmarks
- Timeliness of contributions matters (especially RA-L: "originality over maturity")

---

## 6. COMMON REJECTION REASONS

### 6.1 Technical Grounds
- Mathematical proofs unsound or incomplete
- Experimental design fundamentally flawed
- Results do not support claims
- Inappropriate statistical methods
- Missing ablation studies
- Insufficient baselines or unfair comparisons

### 6.2 Novelty Grounds
- Trivial variation on existing work
- Well-known results without new insight
- Incremental rather than significant advance
- Missing critical related work showing overlap

### 6.3 Presentation Grounds
- Too poorly written for technical evaluation (Smith Category 7)
- Paper not self-contained
- Insufficient detail for reproduction
- Disorganized or unclear logical flow

### 6.4 Scope and Administrative
- Out of scope for venue
- Formatting violations / page limit exceeded
- Anonymity violations
- Dual submission detected
- Missing limitations section (where required)

### 6.5 Robotics-Specific
- Simulation-only without justification when real experiments are expected
- Lack of comparison with relevant robotics baselines
- Failure to address practical deployment considerations
- Ignoring sim-to-real gap when claiming real-world applicability
- Testing only in highly controlled/simplified environments

---

## 7. PRINCIPLES OF GOOD REVIEWING

### 7.1 Constructive Adversarialism
- **RSS**: "Re-express the paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'"
- **COPE**: Be objective and constructive; appreciate the reciprocal nature of peer review
- Corrective feedback points out errors; constructive feedback helps authors improve
- "Good peer-review feedback should give precise description and specific recommendations to avoid ambiguity"
- Number points of concern so authors can address them systematically

### 7.2 Tone and Ethics
- **T-RO/RA-L**: "Any diminishing or disrespectful remark must be absolutely avoided"
- **CVPR**: Use third person ("the paper") not second person ("you")
- **Smith**: "Evaluations should target the paper itself, not the person"
- **COPE Principles**: Respect confidentiality, have required expertise, do not use the process for academic advantage, be objective and constructive
- "The potential damage to authors' mental health and well-being when receiving an unfair and insensitive peer review should not be underestimated"

### 7.3 Specificity and Evidence
- **NeurIPS**: "Do not make vague statements in your review, as they are unfairly difficult for authors to address"
- **NeurIPS**: "Superficial, uninformed reviews without evidence are worse than no review"
- Reference specific sections, figures, tables, page/line numbers
- Back up opinions with concrete examples and suggestions
- "Write a courteous, informative, incisive, and helpful review that you would be proud to sign with your name" (CVPR)

### 7.4 Balanced Assessment
- Start with positive aspects before constructive criticism
- Identify what you learned from the paper (RSS)
- List three contributions (NeurIPS 2019)
- "Actively reflect on the strengths of a submission, and not merely focus on finding issues or weaknesses"
- Distinguish major issues from minor ones

### 7.5 Actionability
- **NeurIPS 2019**: "What would the authors have to do for you to increase your score?"
- For favorable recommendations: list both necessary and suggested changes
- For rejection with salvageable work: suggest improvements and alternative venues
- "Not just noting deficiencies but also indicating how they can be mended" (RA-L)

### 7.6 Calibration
- **NeurIPS**: Best practices -- "Be thoughtful, be fair, be useful, be flexible, be timely"
- Evaluate against the specific venue's standards, not personal benchmarks (Smith)
- Assess your own confidence honestly
- Be willing to update your opinion based on new information (rebuttals, discussion)

### 7.7 Nature's Three-Reading Approach
1. First reading: Overall understanding and first impressions
2. Second reading: Detailed technical evaluation
3. Third reading: Presentation and clarity
- Classify comments as major or minor flaws
- Structure report as inverted pyramid (most important at top)

---

## 8. KEY QUOTES AND PRINCIPLES

**On the Purpose of Review:**
> "Editors and reviewers are not there to be inflexible judges; rather their role is to help authors write better papers." -- T-RO / RA-L

**On Evaluating Contributions:**
> "Submissions bring value to the ICLR community when they convincingly demonstrate new, relevant, impactful knowledge -- not contingent on benchmark dominance." -- ICLR 2026

> "State-of-the-art results are not required." -- ICLR 2026

> "Originality does not necessarily require introducing an entirely new method." -- NeurIPS 2025

**On Limitations:**
> "Honestly reported limitations should be treated kindly and with high appreciation. On the other hand, obvious shortcomings or flaws not reported by the authors should be pointed out extensively and be strongly reflected in your scores." -- CoRL

> "Authors should be rewarded rather than punished for being up front about limitations." -- NeurIPS

**On Impact vs. Perfection:**
> "Favor slightly flawed, impactful work over perfectly executed, low-impact work." -- HRI 2026

**On Review Quality:**
> "Superficial, uninformed reviews without evidence are worse than no review." -- NeurIPS

> "Write a courteous, informative, incisive, and helpful review that you would be proud to sign with your name." -- CVPR

**On Balance:**
> "Being too lenient produces poor scholarship and misinformation, while excessive criticism blocks legitimate research and damages careers." -- Smith

**On Understanding:**
> "Re-express your paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'" -- RSS

**On Specificity:**
> "Do not make vague statements in your review, as they are unfairly difficult for authors to address." -- NeurIPS

**On Robotics Quality:**
> "Results must be demonstrated by all relevant and applicable scientific means -- be they mathematical proofs, statistically significant and reproducible experimental tests, field demonstrations, or whatever may be needed to convince a duly skeptical critical scientist." -- IJRR

**On Subjectivity:**
> "Significance is a highly subjective criterion based on 80% reviewer taste and 20% experience." -- NeurIPS 2023 Tutorial

**On Borderline Decisions:**
> "Even for 'good' papers, it is rather easy to come up with issues that push it into borderline status." -- Conference decision analysis

---

## 9. SOURCES

### Official Venue Guidelines
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
- [CVPR 2019 How to Write Good Reviews](https://deeplearning.lipingyang.org/wp-content/uploads/2019/03/How-to-Review-for-CVPR.pptx.pdf)

### Foundational Texts
- [Alan Jay Smith, "The Task of the Referee" (1990)](https://www.cs.princeton.edu/~jrex/teaching/spring2005/fft/reviewing.html)
- [Smith PDF via PKU](https://cuibinpku.github.io/resources/reviewing-smith.pdf)
- [NeurIPS 2019 Reviewing Guidelines (Cortes/Larochelle)](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)
- [NeurIPS 2023 Tutorial: "What Can We Do About Reviewer #2?"](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/)

### Expert Advice and Guides
- [Michael Milford: Practical Tips for Writing Robotics Papers](https://michaelmilford.com/practical-tips-for-writing-robotics-conference-papers-that-get-accepted/)
- [The-Good-Reviewer Workshop @ ICRA 2026](https://alejandrofontan.github.io/The-Good-Reviewer-ICRA26/)
- [COPE Ethical Guidelines for Peer Reviewers](https://publicationethics.org/guidance/guideline/ethical-guidelines-peer-reviewers)
- [Nature: How to Write a Thorough Peer Review](https://www.nature.com/articles/d41586-018-06991-0)
- [PLOS: How to Write a Peer Review](https://plos.org/resource/how-to-write-a-peer-review/)
- [Daniel Takeshi: My Paper Reviewing Load](https://danieltakeshi.github.io/2022/04/23/paper-reviewing-load/)
- [AUTOLAB Resources (Ken Goldberg lab)](https://autolab.berkeley.edu/resources.shtml)
- [Stanford CS326 Review Guide](https://web.stanford.edu/class/cs326/review.html)
- [The Reality Gap in Robotics (arXiv)](https://arxiv.org/abs/2510.20808)
