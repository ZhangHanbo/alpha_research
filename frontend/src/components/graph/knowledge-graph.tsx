'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape, { type Core, type EventObject } from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import type { GraphNode, GraphEdge } from '@/lib/types';

// Register the cose-bilkent layout once at module level
cytoscape.use(coseBilkent as never);

// ── Color palette by approach_type ──────────────────────────────
const APPROACH_COLORS: Record<string, string> = {
  'tactile sensing': '#6366f1',
  'reinforcement learning': '#f59e0b',
  'imitation learning': '#10b981',
  'planning': '#ef4444',
  'manipulation': '#3b82f6',
  'vision-language': '#8b5cf6',
};
const DEFAULT_NODE_COLOR = '#64748b';

function nodeColor(approachType: string | null): string {
  if (!approachType) return DEFAULT_NODE_COLOR;
  const key = approachType.toLowerCase();
  for (const [pattern, color] of Object.entries(APPROACH_COLORS)) {
    if (key.includes(pattern)) return color;
  }
  return DEFAULT_NODE_COLOR;
}

function nodeSize(score: number | null): number {
  if (score == null) return 30;
  return 30 + ((Math.min(Math.max(score, 1), 5) - 1) / 4) * 30;
}

// ── Edge style by relation_type ─────────────────────────────────
function edgeStyle(relationType: GraphEdge['relation_type']) {
  switch (relationType) {
    case 'extends':
    case 'cites':
      return { lineStyle: 'solid', lineColor: '#94a3b8' };
    case 'same_task':
    case 'same_method':
      return { lineStyle: 'dashed', lineColor: '#94a3b8' };
    case 'contradicts':
      return { lineStyle: 'dashed', lineColor: '#ef4444' };
    case 'supersedes':
      return { lineStyle: 'solid', lineColor: '#f59e0b' };
    default:
      return { lineStyle: 'solid', lineColor: '#94a3b8' };
  }
}

// ── Props ───────────────────────────────────────────────────────
interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function KnowledgeGraph({ nodes, edges }: KnowledgeGraphProps) {
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  // Build cytoscape elements from props
  const elements = useMemo(() => {
    const cyNodes = nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.title.length > 40 ? n.title.slice(0, 37) + '...' : n.title,
        fullTitle: n.title,
        year: n.year,
        venue: n.venue,
        score: n.score,
        approachType: n.approach_type,
        nodeColor: nodeColor(n.approach_type),
        nodeSize: nodeSize(n.score),
      },
    }));

    const cyEdges = edges.map((e, i) => {
      const style = edgeStyle(e.relation_type);
      return {
        data: {
          id: `e-${i}`,
          source: e.source,
          target: e.target,
          relationType: e.relation_type,
          lineStyle: style.lineStyle,
          lineColor: style.lineColor,
        },
      };
    });

    return [...cyNodes, ...cyEdges];
  }, [nodes, edges]);

  // Layout config
  const layout = useMemo(
    () => ({
      name: 'cose-bilkent',
      animate: true,
      animationDuration: 500,
      nodeRepulsion: 8000,
      idealEdgeLength: 120,
      edgeElasticity: 0.45,
      nestingFactor: 0.1,
      gravity: 0.25,
      numIter: 2500,
      tile: true,
    }),
    [],
  );

  // Stylesheet for cytoscape
  const stylesheet = useMemo<cytoscape.StylesheetStyle[]>(
    () => [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          width: 'data(nodeSize)',
          height: 'data(nodeSize)',
          'background-color': 'data(nodeColor)',
          'font-size': '10px',
          'text-wrap': 'wrap',
          'text-max-width': '100px',
          'text-valign': 'bottom',
          'text-margin-y': 6,
          color: '#e2e8f0',
          'border-width': 0,
          'overlay-opacity': 0,
        },
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': '#fbbf24',
          'border-opacity': 1,
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.5,
          'line-style': 'data(lineStyle)' as never,
          'line-color': 'data(lineColor)',
          'target-arrow-color': 'data(lineColor)',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.8,
          'curve-style': 'bezier',
          opacity: 0.7,
        },
      },
    ],
    [],
  );

  const handleCy = useCallback(
    (cy: Core) => {
      // Avoid re-binding if same instance
      if (cyRef.current === cy) return;
      cyRef.current = cy;

      cy.on('tap', 'node', (evt: EventObject) => {
        const data = evt.target.data();
        setSelected({
          id: data.id,
          title: data.fullTitle,
          year: data.year ?? null,
          venue: data.venue ?? null,
          score: data.score ?? null,
          approach_type: data.approachType ?? null,
        });
      });

      cy.on('tap', (evt: EventObject) => {
        if (evt.target === cy) {
          setSelected(null);
        }
      });
    },
    [],
  );

  // ── Empty state ───────────────────────────────────────────────
  if (nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p className="text-sm">No graph data yet. Run a research cycle to populate the knowledge graph.</p>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      {/* Graph canvas */}
      <div className="flex-1 min-h-0">
        <CytoscapeComponent
          elements={elements}
          layout={layout as never}
          stylesheet={stylesheet}
          cy={handleCy}
          className="h-full w-full"
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {/* Selected node info card */}
      {selected && (
        <div className="absolute bottom-4 left-4 right-4 rounded-lg border bg-card p-4 shadow-lg">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold text-card-foreground">
                {selected.title}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                {selected.year && <span>{selected.year}</span>}
                {selected.venue && (
                  <span className="rounded bg-muted px-1.5 py-0.5">{selected.venue}</span>
                )}
                {selected.approach_type && (
                  <span className="rounded bg-muted px-1.5 py-0.5">{selected.approach_type}</span>
                )}
                {selected.score != null && (
                  <span className="font-medium text-card-foreground">
                    Score: {selected.score.toFixed(1)}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted"
            >
              <span className="sr-only">Close</span>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 1l12 12M13 1L1 13" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
