/**
 * useSpeechSynthesis.ts — CareFlow TTS Hook
 *
 * Browser Web Speech Synthesis API wrapper.
 * Provides speak/stop controls for reading agent responses aloud.
 */

import { useState, useCallback, useEffect, useRef } from 'react';

export interface UseSpeechSynthesisReturn {
    /** Whether TTS is supported in this browser */
    supported: boolean;
    /** Whether speech is currently playing */
    speaking: boolean;
    /** The id of the message currently being spoken (null if none) */
    speakingMessageId: string | null;
    /** Start speaking the given text, associated with a message id */
    speak: (text: string, messageId: string) => void;
    /** Stop any current speech */
    stop: () => void;
}

/**
 * Strip markdown formatting for cleaner TTS output.
 * Removes headers, bold, italic, links, images, code blocks, etc.
 */
function stripMarkdown(text: string): string {
    return text
        .replace(/#{1,6}\s+/g, '')           // headers
        .replace(/\*\*(.+?)\*\*/g, '$1')     // bold
        .replace(/\*(.+?)\*/g, '$1')         // italic
        .replace(/__(.+?)__/g, '$1')         // bold alt
        .replace(/_(.+?)_/g, '$1')           // italic alt
        .replace(/~~(.+?)~~/g, '$1')         // strikethrough
        .replace(/`{1,3}[^`]*`{1,3}/g, '')  // inline code / code blocks
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
        .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')  // images
        .replace(/^\s*[-*+]\s+/gm, '')       // list markers
        .replace(/^\s*\d+\.\s+/gm, '')       // numbered lists
        .replace(/\n{2,}/g, '. ')            // double newlines to pause
        .replace(/\n/g, ' ')                 // single newlines to space
        .trim();
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
    const [supported, setSupported] = useState(true);
    const [speaking, setSpeaking] = useState(false);
    const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    useEffect(() => {
        if (typeof window === 'undefined' || !window.speechSynthesis) {
            setSupported(false);
        }
    }, []);

    const stop = useCallback(() => {
        if (typeof window !== 'undefined' && window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        setSpeaking(false);
        setSpeakingMessageId(null);
        utteranceRef.current = null;
    }, []);

    const speak = useCallback((text: string, messageId: string) => {
        if (typeof window === 'undefined' || !window.speechSynthesis) return;

        // If already speaking this message, stop it (toggle behavior)
        if (speakingMessageId === messageId) {
            stop();
            return;
        }

        // Stop any current speech first
        window.speechSynthesis.cancel();

        const cleanText = stripMarkdown(text);
        if (!cleanText) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
            setSpeaking(true);
            setSpeakingMessageId(messageId);
        };

        utterance.onend = () => {
            setSpeaking(false);
            setSpeakingMessageId(null);
            utteranceRef.current = null;
        };

        utterance.onerror = () => {
            setSpeaking(false);
            setSpeakingMessageId(null);
            utteranceRef.current = null;
        };

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
    }, [speakingMessageId, stop]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (typeof window !== 'undefined' && window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    return { supported, speaking, speakingMessageId, speak, stop };
}
