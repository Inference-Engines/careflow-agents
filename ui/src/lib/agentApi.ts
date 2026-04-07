/**
 * agentApi.ts — CareFlow ADK API 클라이언트 / ADK API Client
 *
 * 모든 요청은 /api/*로 전송되며, 개발 시 Vite 프록시, 프로덕션(Cloud Run)에서는
 * FastAPI가 직접 서빙한다. SSE 스트리밍으로 에이전트 활동을 실시간 수신.
 *
 * All requests go to /api/* — proxied by Vite in dev, served directly by
 * FastAPI in production (Cloud Run). SSE streaming enables real-time
 * agent activity tracking (tool calls, sub-agent routing).
 */

const APP_NAME = 'careflow';

/** ADK로부터 수신하는 SSE 이벤트 타입 / SSE event types from ADK */
export interface AgentEvent {
  /** text_delta: 텍스트 청크, turn_complete: 응답 완료, agent_activity: 에이전트 동작 */
  type: 'text_delta' | 'turn_complete' | 'error' | 'agent_activity';
  content?: string;
  author?: string;
  toolCall?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Session
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Creates a new ADK session. Returns the session ID.
 * Call once per user interaction session (stored in the hook).
 */
export async function createSession(userId: string, sessionId: string): Promise<string> {
  const res = await fetch('/api/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_name: APP_NAME, user_id: userId, session_id: sessionId }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create session: ${res.status} — ${err}`);
  }

  const data = await res.json();
  return data.id ?? sessionId;
}

// ─────────────────────────────────────────────────────────────────────────────
// Streaming Run
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 에이전트에 메시지를 전송하고 SSE 스트림을 비동기 이터러블로 반환.
 * Sends a message to the agent and yields SSE events as an async iterable.
 *
 * @param userId    - 환자 ID (AlloyDB patient_id와 일치)
 * @param sessionId - ADK 세션 ID (useAgentChat에서 지연 생성)
 * @param message   - 사용자 입력 텍스트 (음성 전사 또는 직접 입력)
 * @yields {AgentEvent} - text_delta | agent_activity | turn_complete | error
 *
 * SSE 파싱 전략 / SSE Parsing Strategy:
 * 프록시 서버가 ADK 응답을 "data: {...}\n\n" 형식의 SSE 라인으로 변환하여 전송.
 * 각 라인을 JSON 파싱 후 에이전트 활동(author, toolCall)과 모델 텍스트를 분리.
 * 최종 모델 텍스트는 마지막에 한 번 emit (중간 서브에이전트 텍스트 제외).
 */
export async function* streamAgentResponse(
  userId: string,
  sessionId: string,
  message: string,
): AsyncIterable<AgentEvent> {
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_name: APP_NAME,
      user_id: userId,
      session_id: sessionId,
      new_message: {
        role: 'user',
        parts: [{ text: message }],
      },
      streaming: true,
    }),
  });

  if (!res.ok || !res.body) {
    const err = await res.text();
    yield { type: 'error', content: `Agent error: ${res.status} — ${err}` };
    return;
  }

  // ── 듀얼 파싱: SSE + JSON array 모두 지원 / Dual parsing ──────────────
  // ADK 응답이 SSE("data: {...}\n") 또는 JSON array("[{...}]")로 올 수 있음.
  // 전체 수신 후 파싱하여 최종 모델 텍스트를 추출한다.
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let fullBody = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    fullBody += decoder.decode(value, { stream: true });
  }

  // 모든 이벤트를 flat array로 수집 / Collect all events
  const events: any[] = [];
  const trimmedBody = fullBody.trim();

  // Case 1: JSON array — "[{...}, {...}]"
  if (trimmedBody.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmedBody);
      if (Array.isArray(parsed)) events.push(...parsed);
    } catch { /* fallback to line parsing */ }
  }

  // Case 2: SSE lines — "data: {...}\ndata: {...}\n"
  if (events.length === 0) {
    for (const line of fullBody.split('\n')) {
      const t = line.trim();
      if (!t || t === 'data: [DONE]') continue;
      const jsonStr = t.startsWith('data: ') ? t.slice(6) : t;
      try { events.push(JSON.parse(jsonStr)); } catch { /* skip */ }
    }
  }

  // 이벤트 처리: 에이전트 활동 + 최종 모델 텍스트 추출
  let lastModelText = '';

  for (const event of events) {
    if (event.author) {
      yield { type: 'agent_activity' as const, author: event.author };
    }
    if (event.content?.parts) {
      for (const part of event.content.parts) {
        if (part.functionCall || part.function_call) {
          const fc = part.functionCall || part.function_call;
          yield { type: 'agent_activity' as const, author: event.author, toolCall: fc.name };
        }
        // 모델 텍스트 캡처 — role 체크 완화 (서브에이전트도 포함)
        if (part.text && (!event.content.role || event.content.role === 'model')) {
          lastModelText = part.text;
        }
      }
    }
  }

  if (lastModelText) {
    yield { type: 'text_delta' as const, content: lastModelText };
  }
  yield { type: 'turn_complete' as const };
}
