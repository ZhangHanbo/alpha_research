'use client';

import { useState, useMemo, Fragment } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getExpandedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ExpandedState,
} from '@tanstack/react-table';
import type { Evaluation, RubricScore } from '@/lib/types';
import { cn } from '@/lib/utils';

const DIMENSIONS = [
  { key: 'significance', label: 'Significance' },
  { key: 'formalization', label: 'Formalization' },
  { key: 'technical', label: 'Technical' },
  { key: 'rigor', label: 'Rigor' },
  { key: 'representation', label: 'Representation' },
  { key: 'generalization', label: 'Generalization' },
  { key: 'practical', label: 'Practical' },
] as const;

const CONFIDENCE_ICON: Record<string, string> = { high: '▲', medium: '●', low: '▼' };

function scoreColor(score: number): string {
  if (score <= 2) return 'text-red-600 dark:text-red-400';
  if (score === 3) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-green-600 dark:text-green-400';
}

function ScoreCell({ rs }: { rs: RubricScore | undefined }) {
  if (!rs) return <span className="text-muted-foreground">—</span>;
  return (
    <span className={cn('font-medium tabular-nums', scoreColor(rs.score))}>
      {rs.score}
      <span className="ml-1 text-[10px] opacity-70" title={`${rs.confidence} confidence`}>
        {CONFIDENCE_ICON[rs.confidence] ?? '●'}
      </span>
    </span>
  );
}

function ExpandedDetail({ evaluation }: { evaluation: Evaluation }) {
  return (
    <div className="grid gap-4 px-4 py-3 sm:grid-cols-2 lg:grid-cols-3">
      {DIMENSIONS.map(({ key, label }) => {
        const rs = evaluation.rubric_scores[key];
        if (!rs) return null;
        return (
          <div key={key} className="rounded-md border p-3 text-sm">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-semibold">{label}</span>
              <ScoreCell rs={rs} />
            </div>
            <p className="mb-2 text-xs leading-relaxed text-muted-foreground">{rs.reasoning}</p>
            {rs.evidence.length > 0 && (
              <ul className="list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
                {rs.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

const columnHelper = createColumnHelper<Evaluation>();

function buildColumns() {
  return [
    columnHelper.display({
      id: 'expander',
      header: () => null,
      cell: ({ row }) => (
        <button
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground h-7 w-7"
          onClick={row.getToggleExpandedHandler()}
          aria-label={row.getIsExpanded() ? 'Collapse row' : 'Expand row'}
        >
          {row.getIsExpanded() ? '▾' : '▸'}
        </button>
      ),
      size: 36,
    }),
    columnHelper.accessor((r) => r.title ?? r.paper_id, {
      id: 'title',
      header: 'Paper',
      cell: (info) => (
        <span className="line-clamp-2 max-w-xs font-medium" title={info.getValue()}>
          {info.getValue()}
        </span>
      ),
      size: 280,
    }),
    ...DIMENSIONS.map((dim) =>
      columnHelper.accessor((r) => r.rubric_scores[dim.key]?.score ?? 0, {
        id: dim.key,
        header: dim.label,
        cell: (info) => <ScoreCell rs={info.row.original.rubric_scores[dim.key]} />,
        size: 100,
      }),
    ),
    columnHelper.accessor('human_review_flags', {
      header: 'Flags',
      cell: (info) => {
        const flags = info.getValue();
        if (!flags?.length) return null;
        return (
          <div className="flex flex-wrap gap-1">
            {flags.map((f) => (
              <span
                key={f}
                className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold border-yellow-300 bg-yellow-50 text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
              >
                {f}
              </span>
            ))}
          </div>
        );
      },
      size: 160,
    }),
  ];
}

interface EvaluationTableProps {
  evaluations: Evaluation[];
}

export function EvaluationTable({ evaluations }: EvaluationTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const columns = useMemo(() => buildColumns(), []);

  const table = useReactTable({
    data: evaluations,
    columns,
    state: { sorting, globalFilter, expanded },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onExpandedChange: setExpanded,
    getRowCanExpand: () => true,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  });

  return (
    <div className="space-y-2">
      {/* Filter row */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Search papers..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="h-9 w-full max-w-sm rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <span className="text-xs text-muted-foreground">
          {table.getFilteredRowModel().rows.length} of {evaluations.length} papers
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full caption-bottom text-sm">
          <thead className="border-b bg-muted/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className={cn(
                      'h-10 px-3 text-left align-middle font-medium text-muted-foreground',
                      header.column.getCanSort() && 'cursor-pointer select-none hover:text-foreground',
                    )}
                    style={{ width: header.getSize() }}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' ↑', desc: ' ↓' }[header.column.getIsSorted() as string] ?? ''}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <Fragment key={row.id}>
                <tr
                  className={cn(
                    'border-b transition-colors hover:bg-muted/50',
                    row.getIsExpanded() && 'bg-muted/30',
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2 align-middle">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
                {row.getIsExpanded() && (
                  <tr className="border-b bg-muted/20">
                    <td colSpan={row.getVisibleCells().length}>
                      <ExpandedDetail evaluation={row.original} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {table.getFilteredRowModel().rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-muted-foreground">
                  No evaluations found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
