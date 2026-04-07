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

  // ── SSE 증분 파싱 / Incremental SSE Parsing ──────────────────────────
  // 프록시가 "data: {...}\n\n" 형식으로 전송. 버퍼에 누적 후 줄 단위로 파싱.
  // Proxy emits "data: {...}\n\n" lines. Buffer accumulates, parse line-by-line.
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  // 마지막 모델 텍스트만 최종 응답으로 사용 (서브에이전트 중간 출력 무시)
  // Only the last model text becomes the final response (skip sub-agent output)
  let lastModelText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === 'data: [DONE]') continue;

      const jsonStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed;
      try {
        const event = JSON.parse(jsonStr);

        // ── 에이전트 활동 실시간 전달 / Yield agent activities in real-time ──
        if (event.author) {
          yield { type: 'agent_activity' as const, author: event.author };
        }

        if (event.content?.parts) {
          for (const part of event.content.parts) {
            if (part.functionCall || part.function_call) {
              const fc = part.functionCall || part.function_call;
              yield { type: 'agent_activity' as const, author: event.author, toolCall: fc.name };
            }
            if (part.text && event.content.role === 'model') {
              lastModelText = part.text;
            }
          }
        }
      } catch {
        // skip malformed lines
      }
    }
  }

  // Emit final text
  if (lastModelText) {
    yield { type: 'text_delta' as const, content: lastModelText };
  }

  yield { type: 'turn_complete' as const };
}
