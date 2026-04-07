/**
 * agentApi.ts — CareFlow ADK API Client
 *
 * All requests go to /api/* which is proxied to the FastAPI server
 * in dev (via vite.config.ts) and served directly in production (Cloud Run).
 */

const APP_NAME = 'careflow';

export interface AgentEvent {
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
 * Sends a message to the agent and returns an async iterable of text deltas.
 * Each yielded string is a chunk of the agent's streamed response.
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

  // Parse the SSE / newline-delimited JSON stream from ADK
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === 'data: [DONE]') continue;

      // SSE format: "data: {...}"
      const jsonStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed;
      try {
        const event = JSON.parse(jsonStr);

        // Emit agent activity events (author + tool calls)
        if (event.author) {
          yield { type: 'agent_activity', author: event.author };
        }

        // ADK emits events with a `content` field containing parts
        if (event.content?.parts) {
          for (const part of event.content.parts) {
            if (part.text) {
              yield { type: 'text_delta', content: part.text, author: event.author };
            }
            if (part.function_call) {
              yield { type: 'agent_activity', author: event.author, toolCall: part.function_call.name };
            }
          }
        }

        if (event.turn_complete === true) {
          yield { type: 'turn_complete' };
        }
      } catch {
        // Skip malformed lines silently
      }
    }
  }

  yield { type: 'turn_complete' };
}
