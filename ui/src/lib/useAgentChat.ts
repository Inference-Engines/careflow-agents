/**
 * useAgentChat.ts — CareFlow 에이전트 채팅 훅 / Agent Chat Hook
 *
 * 컴포넌트 마운트 당 하나의 ADK 세션을 관리하는 React 커스텀 훅.
 * 지연 세션 생성(lazy init), SSE 스트리밍, 에이전트 활동 추적을 캡슐화.
 *
 * Custom React hook that manages one ADK session per component mount.
 * Encapsulates lazy session creation, SSE streaming, and real-time
 * agent activity tracking (which sub-agent is active, what tool is called).
 *
 * @returns {UseAgentChatReturn}
 *   - messages[]        : 전체 채팅 이력 (user + assistant)
 *   - status            : 'idle' | 'streaming' | 'error'
 *   - agentActivities[] : 실시간 에이전트 활동 (도구 호출, 서브에이전트 라우팅)
 *   - sendMessage(text) : 에이전트에 메시지 전송 + 스트리밍 응답 수신
 *   - clearMessages()   : 채팅 초기화 + 세션 리셋
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { createSession, streamAgentResponse } from './agentApi';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant';
export type ChatStatus = 'idle' | 'streaming' | 'error';

/** 채팅 메시지 / Chat message (user or assistant) */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** 스트리밍 중에는 점진적으로 누적됨 / Accumulates incrementally during streaming */
  content: string;
  timestamp: Date;
}

/** 에이전트 활동 상태 — UI에서 실시간 파이프라인 표시용 / Agent activity for real-time pipeline display */
export interface AgentActivity {
  agent: string;
  action: string;
  /** active: 현재 실행 중, done: 완료, waiting: 대기 중 */
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

// ── 도구 라벨 매핑 / Tool Label Mapping ─────────────────────────────────────
// 에이전트가 호출하는 도구명을 사용자 친화적 라벨로 변환.
// Maps internal tool names to user-friendly labels for the activity feed.

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
  // ── 매 세션 새 대화 시작 / Fresh conversation per session ──────────────
  // 새로고침 시 깨끗한 대화 시작. 세션 내에서는 메시지 유지.
  // Start fresh on page load. Messages persist within the session only.
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>('idle');
  /** 실시간 에이전트 파이프라인 상태 / Real-time agent pipeline status */
  const [agentActivities, setAgentActivities] = useState<AgentActivity[]>([]);

  // ── 지연 세션 생성 / Lazy Session Initialization ──────────────────────
  // 첫 메시지 전송 시에만 ADK 세션을 생성하여 불필요한 API 호출 방지.
  // ADK session is created only on first message to avoid unnecessary API calls.
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
        // ── 에이전트 활동 추적 / Agent Activity Tracking ────────────────
        // seenAgents로 중복 방지. 새 에이전트 등장 시 이전 항목을 'done'으로 전환.
        // seenAgents prevents duplicates. Previous entries marked 'done' on new agent.
        const seenAgents = new Set<string>();

        for await (const event of streamAgentResponse(USER_ID, sessionId, trimmed)) {
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
