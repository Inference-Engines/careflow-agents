import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Icon } from '@iconify/react';
import { motion, AnimatePresence } from 'motion/react';

interface VoiceAssistantProps {
    prompt: string;
    onSend: (text: string) => Promise<void>;
}

type VoiceState = 'idle' | 'listening' | 'processing';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionInstance = any;

function getSpeechRecognition(): SpeechRecognitionInstance | null {
    if (typeof window === 'undefined') return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SRClass = w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
    return SRClass;
}

/** Check browser support without instantiating */
function isSpeechRecognitionSupported(): boolean {
    return getSpeechRecognition() !== null;
}

const VoiceAssistant: React.FC<VoiceAssistantProps> = ({ prompt, onSend }) => {
    const [voiceState, setVoiceState] = useState<VoiceState>('idle');
    const [transcript, setTranscript] = useState('');
    const [supported, setSupported] = useState(true);
    const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
    const transcriptRef = useRef('');

    // Check browser support on mount
    useEffect(() => {
        setSupported(isSpeechRecognitionSupported());
    }, []);

    const startListening = useCallback(() => {
        const SR = getSpeechRecognition();
        if (!SR) {
            setSupported(false);
            alert('Voice input is not supported in this browser. Please use Chrome or Edge.');
            return;
        }

        // Stop any existing recognition instance first
        if (recognitionRef.current) {
            try { recognitionRef.current.abort(); } catch { /* ignore */ }
            recognitionRef.current = null;
        }

        const recognition = new SR();
        recognition.lang = 'en-IN';
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognitionRef.current = recognition;
        transcriptRef.current = '';

        recognition.onstart = () => {
            setVoiceState('listening');
            setTranscript('');
        };

        recognition.onresult = (event: { results: SpeechRecognitionInstance; resultIndex: number }) => {
            let finalTranscript = '';
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }
            const current = finalTranscript || interimTranscript;
            if (current) {
                transcriptRef.current = current;
                setTranscript(current);
            }
        };

        recognition.onend = async () => {
            setVoiceState('processing');
            const final = transcriptRef.current;
            if (final.trim()) {
                await onSend(final.trim());
            }
            setVoiceState('idle');
            setTranscript('');
            transcriptRef.current = '';
            recognitionRef.current = null;
        };

        recognition.onerror = (event: { error: string }) => {
            console.warn('[CareFlow STT] Recognition error:', event.error);
            // 'no-speech' is expected when user doesn't speak — not a real error
            if (event.error === 'no-speech') {
                setVoiceState('idle');
                setTranscript('');
                transcriptRef.current = '';
                recognitionRef.current = null;
                return;
            }
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                alert('Microphone access was denied. Please allow microphone access and try again.');
                setSupported(false);
            }
            setVoiceState('idle');
            setTranscript('');
            transcriptRef.current = '';
            recognitionRef.current = null;
        };

        try {
            recognition.start();
        } catch (err) {
            console.error('[CareFlow STT] Failed to start recognition:', err);
            setVoiceState('idle');
            recognitionRef.current = null;
        }
    }, [onSend]);

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop();
    }, []);

    // Cleanup recognition on unmount
    useEffect(() => {
        return () => {
            if (recognitionRef.current) {
                try { recognitionRef.current.abort(); } catch { /* ignore */ }
                recognitionRef.current = null;
            }
        };
    }, []);

    const handleClick = () => {
        if (!supported) {
            alert('Voice input is not supported in this browser. Please use Chrome or Edge.');
            return;
        }
        if (voiceState === 'idle') startListening();
        else if (voiceState === 'listening') stopListening();
    };

    const displayText = () => {
        if (voiceState === 'listening') return transcript || 'Listening…';
        if (voiceState === 'processing') return 'Sending to CareFlow…';
        return `"${prompt}"`;
    };

    // Listen for sidebar voice CTA event
    useEffect(() => {
        const handler = () => {
            if (voiceState === 'idle') startListening();
        };
        window.addEventListener('careflow:voice-start', handler);
        return () => window.removeEventListener('careflow:voice-start', handler);
    }, [voiceState, startListening]);

    const isListening = voiceState === 'listening';
    const isProcessing = voiceState === 'processing';

    return (
        <div className="fixed bottom-24 lg:bottom-10 right-6 z-50">
            {/* Glow pulse ring — shows when listening */}
            {isListening && (
                <span
                    className="absolute inset-0 rounded-full bg-error/30 animate-pulse-ring pointer-events-none"
                    style={{ borderRadius: '9999px' }}
                />
            )}

            <motion.button
                key={`${prompt}-${voiceState}`}
                initial={{ scale: 0.88, opacity: 0, y: 8 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                whileHover={voiceState === 'idle' ? { scale: 1.04 } : undefined}
                whileTap={{ scale: 0.96 }}
                onClick={handleClick}
                disabled={isProcessing}
                transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                className={[
                    'relative flex items-center gap-3 pl-5 pr-2 py-2 rounded-full',
                    'border border-white/25 shadow-[0_16px_48px_-8px_rgba(28,110,242,0.28)]',
                    'transition-colors duration-300',
                    isListening
                        ? 'bg-error text-white'
                        : 'bg-primary text-white',
                ].join(' ')}
            >
                {/* Pulse dots or spinner */}
                <div className="flex items-center gap-1">
                    {isProcessing ? (
                        <Icon icon="solar:refresh-circle-bold" width={16} className="animate-spin opacity-90" />
                    ) : isListening ? (
                        <>
                            <span className="w-1 h-3 rounded-full bg-white/80 animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1 h-4 rounded-full bg-white animate-bounce" style={{ animationDelay: '100ms' }} />
                            <span className="w-1 h-2.5 rounded-full bg-white/70 animate-bounce" style={{ animationDelay: '200ms' }} />
                        </>
                    ) : (
                        <>
                            <span className="w-1 h-2 rounded-full bg-white/60 animate-pulse" style={{ animationDelay: '0s' }} />
                            <span className="w-1 h-3 rounded-full bg-white/80 animate-pulse" style={{ animationDelay: '0.2s' }} />
                            <span className="w-1 h-1.5 rounded-full bg-white/60 animate-pulse" style={{ animationDelay: '0.4s' }} />
                        </>
                    )}
                </div>

                {/* Label */}
                <AnimatePresence mode="wait">
                    <motion.span
                        key={voiceState + transcript.slice(0, 8)}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.2 }}
                        className={[
                            'tracking-tight max-w-[220px] truncate leading-none',
                            voiceState === 'idle'
                                ? 'text-xs font-medium text-white/60'
                                : 'text-sm font-semibold',
                        ].join(' ')}
                    >
                        {displayText()}
                    </motion.span>
                </AnimatePresence>

                {/* Nested icon container — Supanova CTA spec */}
                <div className="btn-icon-wrap ml-1">
                    <Icon
                        icon={isListening ? 'solar:microphone-slash-bold' : 'solar:microphone-bold'}
                        width={16}
                    />
                </div>
            </motion.button>
        </div>
    );
};

export default VoiceAssistant;
