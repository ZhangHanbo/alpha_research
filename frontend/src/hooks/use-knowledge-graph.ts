"use client";

import { useEffect, useCallback } from "react";
import { useResearchStore } from "./use-research-store";
import { getGraphNodes, getGraphEdges } from "@/lib/api";

export function useKnowledgeGraph() {
  const { graphNodes, graphEdges, setGraphData } = useResearchStore();

  const refresh = useCallback(async () => {
    try {
      const [nodes, edges] = await Promise.all([
        getGraphNodes(),
        getGraphEdges(),
      ]);
      setGraphData(nodes, edges);
    } catch (err) {
      console.error("Failed to fetch graph data:", err);
    }
  }, [setGraphData]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { nodes: graphNodes, edges: graphEdges, refresh };
}
