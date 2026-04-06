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

export interface UseAgentChatReturn {
  messages: ChatMessage[];
  status: ChatStatus;
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

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>('idle');

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

      try {
        const sessionId = await ensureSession();

        for await (const event of streamAgentResponse(USER_ID, sessionId, trimmed)) {
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

  return { messages, status, sendMessage, clearMessages };
}
