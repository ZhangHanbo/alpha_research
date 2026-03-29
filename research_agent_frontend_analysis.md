# Frontend Analysis: AI Research Agent & Literature Review Tools

## 1. Open-Source Research Agent Projects

### GPT Researcher (github.com/assafelovic/gpt-researcher)
- **Type**: Web app (two versions)
- **Tech stack**:
  - Lightweight: HTML/CSS/JS served by FastAPI (port 8000)
  - Production: Next.js + React + TypeScript + Tailwind CSS (port 3000)
- **Key UI patterns**:
  - Single query input box with report source dropdown (web vs. local docs)
  - Real-time streaming progress of research tasks via WebSocket/SSE
  - Drag-and-drop file upload for local document research
  - Environment variable configuration panel
  - Multi-agent workflow triggering (via LangGraph Cloud)
  - `onResultsChange` callback for progress tracking in the React component
  - Output in multiple formats (PDF, Word, Markdown)
- **What works well**: Clean query-to-report workflow. The NextJS frontend is packaged as a reusable React component (`GPTResearcher`) with props for `apiUrl`, `apiKey`, `defaultPrompt`, and `onResultsChange`. Docker deployment makes it easy to spin up.
- **What doesn't work well**: The lightweight frontend is very basic. Documentation lacks detail on actual progress visualization UI. No structured evaluation/scoring of individual sources.
- **Relevance**: High. Closest model to an autonomous research agent with a web UI. The streaming progress pattern is directly applicable.

### STORM (github.com/stanford-oval/storm)
- **Type**: Web app (Streamlit demo + production hosted app)
- **Tech stack**:
  - Demo: Streamlit (Python) in `frontend/demo_light/`
  - Production: Hosted at storm.genie.stanford.edu (Vercel-deployed, likely Next.js)
- **Key UI patterns**:
  - Topic input -> real-time research observation
  - Hierarchical outline generation display
  - Full article generation with inline citations
  - Co-STORM mode: dynamic mind map visualization of collected knowledge
  - Discourse thread view showing multi-agent conversation simulation
  - Turn-based display of AI agent dialogue
- **What works well**: The mind map for Co-STORM is an excellent pattern for showing how knowledge accumulates. The discourse view makes agent reasoning transparent. 70K+ users on the hosted version suggests the UX works.
- **What doesn't work well**: Streamlit demo is minimal and not production-grade. Limited customization of research process.
- **Relevance**: Very high. The mind map / knowledge graph visualization during research is exactly what a research agent needs. The discourse thread pattern could show agent state transitions.

### PaperQA2 (github.com/Future-House/paper-qa)
- **Type**: CLI only (no web UI)
- **Tech stack**: Python, Pydantic, LiteLLM, tantivy (search engine), httpx
- **Key UI patterns**:
  - CLI commands: `pqa ask`, `pqa search`, `pqa view`, `pqa index`
  - Structured output: formatted_answer, answer, question, context (with citation passages)
  - Automatic metadata enrichment: citation counts, retraction checks from Crossref/Semantic Scholar
  - Bundled settings presets (high_quality, fast, wikicrow)
- **What works well**: Excellent answer quality with grounded citations. Good metadata integration (retraction checks, citation counts). Clean programmatic API.
- **What doesn't work well**: No visual interface at all. No way to see the search/evaluation process. Pure CLI means no dashboard or progress visualization.
- **Relevance**: Medium for UI patterns (none), but high for backend architecture. The structured answer format (question -> context passages with citations -> synthesized answer) is a good data model for a frontend.

### Khoj (github.com/khoj-ai/khoj)
- **Type**: Multi-platform (web app, desktop, mobile, Obsidian plugin, Emacs, WhatsApp)
- **Tech stack**:
  - Frontend: Next.js 15 + React 18 + TypeScript
  - UI components: Radix UI + shadcn/ui + Tailwind CSS
  - Visualization: Mermaid (diagrams), Excalidraw (drawing)
  - Math: KaTeX
  - Markdown: markdown-it with syntax highlighting
  - Animations: Framer Motion
  - Forms: React Hook Form + Zod
  - Icons: Lucide React
- **Key UI patterns**:
  - Chat-based primary interface (similar to ChatGPT/Claude)
  - Slash commands (/notes, /online, /image) for granular control
  - Deep research mode that searches documents and internet
  - Document upload and management
  - Custom agent configuration
  - Chart, image, and diagram generation inline
  - Multi-format document support (PDF, Markdown, Notion, Word)
- **What works well**: Polished, modern UI with excellent component library choices. Multi-platform approach means the web UI is well-tested. shadcn/ui + Radix gives accessible, customizable components. Mermaid for diagrams is clever.
- **What doesn't work well**: Chat-centric UI may not be ideal for structured research workflows. No explicit paper evaluation/scoring interface. Deep research feature doesn't expose its state machine to the user.
- **Relevance**: High for tech stack reference. The Next.js + shadcn/ui + Radix + Tailwind stack is a proven modern choice. Mermaid for diagram rendering is useful.

### OpenScholar (github.com/AkariAsai/OpenScholar)
- **Type**: CLI + hosted demo (open-scholar.allen.ai)
- **Tech stack**: Python (inference pipeline), Llama 3.1 8B, Contriever embeddings, Semantic Scholar API
- **Key UI patterns**:
  - CLI-based: `run.py` with configuration flags
  - Hosted demo has a simple query-and-answer interface
  - Modular pipeline: retrieval -> reranking -> generation
  - Citation attribution and post-hoc refinement
- **What works well**: State-of-the-art retrieval quality. Scientists preferred its responses over human experts 51% of the time. Good citation grounding.
- **What doesn't work well**: Minimal UI. No process visualization. No evaluation scoring visible to users.
- **Relevance**: Low for UI patterns, high for understanding what the backend should produce.

### LatteReview (github.com/PouriaRouzrokh/LatteReview)
- **Type**: Python library (no web UI)
- **Tech stack**: Python, Pandas, LiteLLM, async processing
- **Key UI patterns** (programmatic):
  - Multi-agent review with customizable reviewer roles and expertise levels
  - TitleAbstractReviewer: 1-5 scoring + inclusion/exclusion criteria
  - ScoringReviewer: custom scoring by multiple agents
  - AbstractionReviewer: data extraction from abstracts/manuscripts
  - Hierarchical review rounds with filtering (junior reviewers -> expert reviewers for disagreements)
  - Results as DataFrames with scoring metrics and reasoning transparency
- **What works well**: Excellent multi-agent review workflow design. The hierarchical reviewer pattern (junior -> expert) is a strong model. 1-5 scoring with criteria is exactly the rubric pattern needed.
- **What doesn't work well**: No visual interface. Output is just CSV/DataFrame.
- **Relevance**: Very high for the evaluation/scoring data model and multi-agent review workflow, even though there's no UI. This is what a paper evaluation UI should display.

### LangGraph React Agent Studio (github.com/Ylang-Labs/langgraph-react-agent-studio)
- **Type**: Full-stack web app
- **Tech stack**:
  - Frontend: React 19 + TypeScript + Tailwind CSS + Radix UI
  - Backend: Python + FastAPI + LangGraph + LangChain
  - Infrastructure: Redis (pub/sub streaming), PostgreSQL, Docker
- **Key UI patterns**:
  - Agent selection dashboard (Deep Researcher, Chatbot, Math Agent, MCP Agent)
  - Real-time activity timeline showing agent thought processes
  - Tool execution visibility with results displayed inline
  - WebSocket-powered streaming updates
  - Conversation threading
  - Live progress indicators during agent operations
- **What works well**: Production-quality real-time agent visualization. Redis pub/sub for streaming is robust. The activity timeline pattern is excellent for showing agent state.
- **Relevance**: Very high. This is the closest example of a well-built agent dashboard with real-time state visualization.

---

## 2. Commercial Products (UI Pattern Analysis)

### Elicit (elicit.com)
- **Type**: Web app (SaaS)
- **Key UI patterns**:
  - **Search box**: Simple "Ask a research question" input
  - **Table-based results**: The core innovation. Papers are displayed as rows; users add columns for data extraction (intervention, outcomes, sample size, study design, etc.)
  - **Custom columns**: "Add Column" to specify what data to extract from each paper
  - **Column types**: Yes/No/Maybe (screening), Multiple-choice, Free-text extraction
  - **Cell citations**: Click any cell to see supporting quotes from the paper
  - **Systematic Review workflow**: Step-by-step guidance through search -> screening -> data extraction -> report
  - **Chat with Papers**: Conversational interface for uploaded documents
  - **AI-suggested criteria**: System suggests screening criteria and extraction fields based on research question
  - Up to 20 columns, 1000 papers per table
- **What works well**: The table paradigm is extremely powerful for structured literature review. Custom columns turn the AI into a structured data extraction tool. Citation transparency (click to see source quotes) builds trust. The systematic review workflow provides guardrails.
- **What doesn't work well**: The table can become unwieldy with many columns. No graph/network visualization of paper relationships. Limited real-time progress visibility during extraction.
- **Relevance**: Very high. The table-based evaluation UI with custom extraction columns is the gold standard for paper evaluation interfaces. The cell-level citation transparency is essential.

### Semantic Scholar (semanticscholar.org)
- **Type**: Web app (free)
- **Key UI patterns**:
  - **Minimalist search engine style**: Clean search box, structured results
  - **TLDR summaries**: AI-generated one-sentence paper summaries on results page
  - **Semantic Reader**: Augmented PDF reader with contextual citation cards and highlighted sections
  - **Research Feeds**: Personalized paper recommendations
  - **Highly Influential Citations**: Filters citations by influence, not just count
  - **Related Papers / Cited By**: Navigation through citation graph
  - **Quality indicators**: Citation counts, journal quality, study type badges
  - **Intelligent ranking**: AI models rank by influence + recency + topic relevance
- **What works well**: TLDR summaries are immediately useful for scanning. Highly Influential Citations is a great filtering pattern. Clean, fast interface. Free and widely used.
- **What doesn't work well**: No autonomous research capability. No synthesis or evaluation scoring. Individual paper view, not comparative.
- **Relevance**: Medium. The TLDR pattern and quality indicator badges are useful UI elements to adopt. The Semantic Reader's contextual citations are a good pattern.

### Connected Papers (connectedpapers.com)
- **Type**: Web app
- **Key UI patterns**:
  - **Force-directed graph**: Papers as nodes, positioned by similarity (not direct citation)
  - **Node sizing**: Larger bubbles = more citations
  - **Color gradient**: Light to dark = older to newer publications
  - **Hover preview**: Summary panel on right side when hovering a node
  - **Prior Works view**: Shows seminal papers most cited by the graph
  - **Derivative Works view**: Shows papers that cite the graph papers
  - **Influence highlighting**: Selecting a prior work highlights all graph papers that cite it (blue)
  - **Co-citation + bibliographic coupling**: Algorithm for similarity
- **What works well**: Immediately intuitive visualization. The similarity-based layout (not just citations) surfaces unexpected connections. Prior/Derivative Works views are powerful for understanding a field's evolution. Very fast.
- **What doesn't work well**: Single seed paper limitation. No text-based evaluation. No scoring. Static snapshot, no progressive building.
- **Relevance**: High for graph visualization patterns. The force-directed layout with size=citations and color=year is an excellent pattern to adopt for paper relationship display.

### ResearchRabbit (researchrabbit.ai)
- **Type**: Web app
- **Key UI patterns**:
  - **Interactive bubble/node map**: Papers as bubbles with connecting lines
  - **Color coding**: Green = in your collection, Blue = suggested papers not yet added
  - **Hover interactions**: Highlights connections and shows title/abstract/author preview
  - **Column-based navigation**: Each column represents a search/browse action, allowing "hop back" to trace exploration path
  - **Collections**: Intelligent paper playlists that generate recommendations
  - **Adaptive recommendations**: Algorithm learns from exploration patterns
  - **Author network view**: Visualize author relationships
  - **Drag-and-drop organization**: Rearrange nodes to customize view
- **What works well**: The color-coded bubble map (green=collected, blue=suggested) is an excellent pattern for distinguishing known vs. discovered papers. Column-based navigation preserves exploration history. Collections that generate recommendations are powerful.
- **What doesn't work well**: Can be overwhelming for beginners. Dense visualizations with many papers become cluttered. No AI synthesis or evaluation scoring.
- **Relevance**: High. The collection + recommendation pattern and the color-coded graph are directly applicable. The column-based exploration history is a unique pattern worth considering.

### Consensus (consensus.app)
- **Type**: Web app (SaaS)
- **Key UI patterns**:
  - **Search engine style**: Query input -> results list
  - **Consensus Meter**: Visual summary showing academic consensus (e.g., "85% of studies suggest Yes") with a gauge/bar visualization
  - **Result tiles**: Paper title at top, extracted answer in grey text box, metadata below
  - **Quality indicators**: Citation count, journal quality badge, study type label
  - **Dark/Compact modes**: UI customization
  - **AI synthesis**: Summary paragraph at top of results aggregating findings
  - **Detailed study view**: Metadata + summaries + quality indicators + citation counts + publication links all in one view
  - **100+ language support**
- **What works well**: The Consensus Meter is a unique and compelling pattern for showing aggregate research findings. Result tiles with extracted answers (not just abstracts) are more useful than traditional search. Quality indicators are well-integrated.
- **What doesn't work well**: Limited to yes/no type research questions for the meter. No network visualization. No deep customization of evaluation criteria.
- **Relevance**: High. The Consensus Meter pattern is excellent for showing aggregate evaluation results. Quality indicator badges and extracted-answer tiles are patterns to adopt.

### Litmaps (litmaps.com)
- **Type**: Web app
- **Key UI patterns**:
  - **Citation-based scatter plot**: X-axis = publication year, Y-axis = citation count
  - **Multiple seed papers**: Unlike Connected Papers, allows multiple starting points
  - **Customizable axes**: Change what X/Y represent
  - **Variable node size**: Based on different metrics (references, connectivity, etc.)
  - **Import support**: BibTeX, RIS, PubMed files, Zotero integration
  - **Discovery feed**: Automated alerts for new papers in your map area
- **What works well**: The temporal scatter plot is more analytically useful than a force-directed graph for understanding research evolution. Multiple seed papers give more comprehensive coverage. Customizable axes are powerful.
- **What doesn't work well**: Less intuitive than Connected Papers' similarity graph. Can look like a cluttered scatter plot with many papers.
- **Relevance**: Medium-high. The chronological citation visualization is a complementary pattern to force-directed graphs.

---

## 3. UI Pattern Categories & Recommendations

### A. Agent State Machine / Progress Visualization

**Best patterns observed**:
1. **Activity timeline** (LangGraph Agent Studio): Vertical timeline showing each agent step with status indicators, reasoning, and results. Most informative pattern.
2. **SSE streaming with structured events** (LangGraph + FastAPI pattern): Backend emits typed events (step_start, step_update, waiting_human) that the frontend renders as progress indicators.
3. **AG-UI Protocol**: Emerging standard with ~16 event types across 5 categories (Lifecycle, Text Messages, Tool Calls, State Management, Special). Adopted by Microsoft, Oracle. Worth building on.
4. **useStream hook** (LangChain): Framework-agnostic React/Vue/Svelte/Angular hook for consuming agent streams. Handles messages, tool calls, interrupts, history, branching, disconnect/reconnect.

**Recommended approach**: Use SSE or WebSocket streaming with structured event types. Display as a collapsible activity timeline/log. Show current state prominently with a state indicator badge. Allow expanding each step to see details.

**Key libraries**:
- **XState** + Stately Studio: For defining and visualizing state machines. Has drag-and-drop editor and VS Code extension.
- **React Flow**: For node-based workflow visualization (DAG of agent steps).
- **AG-UI Protocol**: For standardized agent-to-frontend event streaming.

### B. Paper Evaluation / Scoring UI

**Best patterns observed**:
1. **Elicit's table with custom columns**: Papers as rows, evaluation criteria as columns. Click cells for source citations. Best for structured comparison.
2. **LatteReview's multi-agent scoring**: 1-5 scale per criterion, multiple reviewers, hierarchical rounds. Good data model.
3. **Consensus quality indicators**: Badges for study type, journal quality, citation count. Good for at-a-glance assessment.

**Recommended approach**:
- Analytic rubric table (papers x criteria matrix) with numerical scores
- Each cell expandable to show AI reasoning and source quotes
- Aggregate score with breakdown visualization (radar chart or horizontal bar chart per criterion)
- Quality indicator badges (study type, citation count, recency, relevance) on paper cards

### C. Knowledge Graph / Paper Relationship Visualization

**Best patterns observed**:
1. **Connected Papers' force-directed graph**: Size=citations, color=year, position=similarity. Most intuitive.
2. **ResearchRabbit's interactive bubble map**: Color=collection status, hover=preview, drag=organize.
3. **Litmaps' temporal scatter**: X=year, Y=citations, lines=citation relationships. Most analytical.
4. **STORM's mind map**: Hierarchical concept structure built progressively during research. Shows knowledge accumulation.

**Key libraries**:
- **Sigma.js** + graphology: Best for large graphs with many nodes. WebGL-rendered.
- **Cytoscape.js**: Full-featured graph library with layout algorithms. Most mature.
- **Reagraph**: WebGL graph visualization purpose-built for React.
- **React Flow**: Good for DAG/workflow graphs (agent steps), less ideal for citation networks.
- **D3.js force-directed**: Maximum customization but more work.

**Recommended approach**: Force-directed graph as the primary view (Connected Papers style) with a timeline/scatter view as secondary (Litmaps style). Build the graph progressively during research to show knowledge accumulation (STORM pattern).

### D. Research Dashboard Design

**Best patterns observed**:
1. **Elicit's systematic review workflow**: Step-by-step guided process (search -> screen -> extract -> report)
2. **GPT Researcher's query-to-report flow**: Single input, streaming progress, formatted output
3. **Khoj's slash-command chat**: Flexible but with structured outputs (diagrams, charts)
4. **LangGraph Agent Studio's multi-panel**: Agent selector + chat + activity timeline

**Recommended approach for a research agent dashboard**:
- **Left panel**: Research configuration (query, parameters, rubric criteria)
- **Center panel**: Live agent activity feed / progress timeline (collapsible steps)
- **Right panel**: Knowledge graph building in real-time
- **Bottom/tab panel**: Paper evaluation table (Elicit-style) with scores filling in as agent evaluates
- **Top bar**: Research phase indicator (Searching -> Evaluating -> Synthesizing -> Complete)

---

## 4. Recommended Tech Stack

Based on the most successful projects analyzed:

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | **Next.js 15+ (App Router)** | Used by Khoj, GPT Researcher. SSR + streaming support. |
| UI Components | **shadcn/ui + Radix UI** | Used by Khoj. Accessible, customizable, not opinionated. |
| Styling | **Tailwind CSS** | Used by all major projects. Fast iteration. |
| State Management | **XState** (agent state) + **React hooks** (UI state) | XState for formal state machine, hooks for simple UI state. |
| Graph Visualization | **Cytoscape.js** or **Sigma.js** | Cytoscape for features, Sigma for performance. |
| Workflow Visualization | **React Flow** | For showing agent DAG/pipeline. |
| Diagrams | **Mermaid** | Used by Khoj. Good for auto-generated diagrams. |
| Charts | **Recharts** | Major 3.0 update in 2025. Good React integration. |
| Streaming | **SSE + useStream** or **AG-UI Protocol** | Standardized agent-to-UI communication. |
| Animations | **Framer Motion** | Used by Khoj. Smooth transitions for progressive disclosure. |
| Markdown | **markdown-it** or **react-markdown** | For rendering research reports. |
| Math | **KaTeX** | If needed for scientific content. |
| Backend API | **FastAPI + WebSocket/SSE** | Python backend with streaming support. |

---

## 5. Key Takeaways

1. **No single tool does everything well.** The best research agent UI would combine Elicit's table-based evaluation, Connected Papers' graph visualization, GPT Researcher's streaming progress, and STORM's progressive knowledge building.

2. **The table is the killer pattern for paper evaluation.** Elicit proved that a spreadsheet-like interface with AI-populated columns is more useful than chat for structured literature review.

3. **Progressive knowledge visualization is underserved.** Most tools show a static graph after research. STORM's progressive mind map during research is the right pattern but poorly implemented (Streamlit limitations).

4. **Agent transparency matters.** LangGraph Agent Studio and GPT Researcher show that users want to see what the agent is doing in real-time, not just the final result.

5. **The AG-UI Protocol is emerging as a standard** for agent-to-frontend communication. Building on it future-proofs the streaming architecture.

6. **The Next.js + shadcn/ui + Tailwind stack is the consensus choice** among well-funded open-source projects (Khoj, GPT Researcher production frontend).
