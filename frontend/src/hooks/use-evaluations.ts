"use client";

import { useEffect, useCallback } from "react";
import { useResearchStore } from "./use-research-store";
import { getEvaluations } from "@/lib/api";

export function useEvaluations(params?: {
  cycle_id?: string;
  mode?: string;
}) {
  const { evaluations, setEvaluations } = useResearchStore();

  const refresh = useCallback(async () => {
    try {
      const data = await getEvaluations(params);
      setEvaluations(data);
    } catch (err) {
      console.error("Failed to fetch evaluations:", err);
    }
  }, [params?.cycle_id, params?.mode, setEvaluations]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { evaluations, refresh };
}
