/**
 * useAgentChat.ts — CareFlow Agent Chat Hook
 *
 * Manages a single ADK session per mount. Provides:
 *   - messages[]          : full chat history (user + assistant)
 *   - status              : 'idle' | 'streaming' | 'error'
 *   - sendMessage(text)   : sends to agent, streams response
 */

import { useState, useCallback, useRef } from 'react';
import { createSession, streamAgentResponse } from './agentApi';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant';
export type ChatStatus = 'idle' | 'streaming' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: Date;
}

export interface AgentActivity {
  agent: string;
  action: string;
  status: 'active' | 'done' | 'waiting';
  icon: string;
  color: string;
}

export interface UseAgentChatReturn {
  messages: ChatMessage[];
  status: ChatStatus;
  agentActivities: AgentActivity[];
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

const USER_ID = 'rajesh-sharma'; // Patient context matches agent's BOSS_INSTRUCTION

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, string> = {
  get_patient_medications: 'Checking medications',
  get_health_metrics: 'Fetching health data',
  get_recent_health_metrics: 'Fetching recent vitals',
  get_adherence_history: 'Checking medication adherence',
  check_drug_interactions: 'Checking drug interactions (openFDA)',
  search_medical_history: 'Searching medical records (RAG)',
  agentic_rag_search: 'Semantic search (HyDE + pgvector)',
  lookup_icd11_code: 'Looking up ICD-11 codes',
  send_email: 'Sending Gmail notification',
  send_escalation_alert: 'Escalating to caregiver',
  create_calendar_event: 'Creating calendar event',
  book_appointment: 'Booking appointment',
  generate_notification_message: 'Composing notification',
  dispatch_notification: 'Dispatching notification',
  calculate_trend: 'Analyzing health trends',
  check_food_drug_interaction: 'Checking food-drug interactions',
  transfer_to_agent: 'Routing to specialist agent',
};

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>('idle');
  const [agentActivities, setAgentActivities] = useState<AgentActivity[]>([]);

  // Session is created lazily on first sendMessage
  const sessionIdRef = useRef<string | null>(null);
  const sessionReadyRef = useRef<Promise<string> | null>(null);

  /** Ensures a session exists (idempotent). Returns the session ID. */
  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionIdRef.current) return sessionIdRef.current;

    if (!sessionReadyRef.current) {
      const newSessionId = generateId();
      sessionReadyRef.current = createSession(USER_ID, newSessionId).then((id) => {
        sessionIdRef.current = id;
        return id;
      });
    }

    return sessionReadyRef.current;
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || status === 'streaming') return;

      // Add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setStatus('streaming');

      // Placeholder for the streaming assistant message
      const assistantMsgId = generateId();
      const assistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setAgentActivities([{ agent: 'root_agent', action: 'Analyzing your message...', status: 'active', icon: '', color: '' }]);

      try {
        const sessionId = await ensureSession();
        const seenAgents = new Set<string>();

        for await (const event of streamAgentResponse(USER_ID, sessionId, trimmed)) {
          // Track agent activities
          if (event.type === 'agent_activity') {
            if (event.author && !seenAgents.has(event.author)) {
              seenAgents.add(event.author);
              setAgentActivities(prev => {
                const updated = prev.map(a => ({ ...a, status: 'done' as const }));
                return [...updated, { agent: event.author!, action: event.toolCall ? (TOOL_LABELS[event.toolCall] || event.toolCall) : 'Processing...', status: 'active' as const, icon: '', color: '' }];
              });
            } else if (event.toolCall) {
              setAgentActivities(prev => {
                const updated = [...prev];
                if (updated.length > 0) {
                  updated[updated.length - 1] = { ...updated[updated.length - 1], action: TOOL_LABELS[event.toolCall!] || event.toolCall! };
                }
                return updated;
              });
            }
          }

          if (event.type === 'text_delta' && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: m.content + event.content! }
                  : m,
              ),
            );
          } else if (event.type === 'error') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: event.content ?? 'An error occurred.' }
                  : m,
              ),
            );
            setStatus('error');
            return;
          }
        }

        setStatus('idle');
        // Mark all agent activities as done
        setAgentActivities(prev => prev.map(a => ({ ...a, status: 'done' as const })));
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Unknown error';
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: `Error: ${errMsg}` }
              : m,
          ),
        );
        setStatus('error');
      }
    },
    [status, ensureSession],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setStatus('idle');
    // Reset session so next message gets a fresh one
    sessionIdRef.current = null;
    sessionReadyRef.current = null;
  }, []);

  return { messages, status, agentActivities, sendMessage, clearMessages };
}
