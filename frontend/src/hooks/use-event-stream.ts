"use client";

import { useCallback, useRef } from "react";
import { useResearchStore } from "./use-research-store";
import { getStreamUrl } from "@/lib/api";
import type { AgentEvent } from "@/lib/types";

export function useEventStream() {
  const esRef = useRef<EventSource | null>(null);
  const store = useResearchStore();

  const handleEvent = useCallback(
    (event: AgentEvent) => {
      const { type, data } = event;
      switch (type) {
        case "step_started":
          store.addStep({
            id: data.step as string,
            name: data.step as string,
            status: "running",
            startTime: Date.now(),
            events: [event],
          });
          break;
        case "step_finished":
          store.updateStep(data.step as string, {
            status: "completed",
            endTime: Date.now(),
          });
          store.addEventToStep(data.step as string, event);
          break;
        case "activity":
        case "tool_call":
        case "tool_result":
          if (data.step) {
            store.addEventToStep(data.step as string, event);
          }
          break;
        case "run_finished":
          store.setAgentStatus("completed");
          break;
        case "error":
          store.setAgentStatus("error");
          break;
      }
    },
    [store]
  );

  const connect = useCallback(() => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource(getStreamUrl());
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data));
      } catch {
        /* ignore parse errors */
      }
    };
    es.onerror = () => {
      store.setAgentStatus("error");
      es.close();
      esRef.current = null;
    };
    return es;
  }, [handleEvent, store]);

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  return { connect, disconnect };
}
