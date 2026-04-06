import React, { useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface VoiceAssistantProps {
    prompt: string;
    onSend: (text: string) => Promise<void>;
}

type VoiceState = 'idle' | 'listening' | 'processing';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionInstance = any;

/** Safe cross-browser getter for the SpeechRecognition constructor. */
function getSpeechRecognition(): SpeechRecognitionInstance | null {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const VoiceAssistant: React.FC<VoiceAssistantProps> = ({ prompt, onSend }) => {
    const [voiceState, setVoiceState] = useState<VoiceState>('idle');
    const [transcript, setTranscript] = useState('');
    const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
    // Keep a mutable ref to the latest transcript so `onend` captures it
    const transcriptRef = useRef('');

    const startListening = useCallback(() => {
        const SR = getSpeechRecognition();
        if (!SR) {
            alert('Voice input is not supported in this browser. Please try Chrome or Edge.');
            return;
        }

        const recognition = new SR();
        recognition.lang = 'en-IN'; // English (India) suits Rajesh Sharma persona
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognitionRef.current = recognition;
        transcriptRef.current = '';

        recognition.onstart = () => {
            setVoiceState('listening');
            setTranscript('');
        };

        recognition.onresult = (event: { results: SpeechRecognitionInstance }) => {
            const current = Array.from(event.results as Iterable<SpeechRecognitionInstance>)
                .map((r: SpeechRecognitionInstance) => r[0].transcript as string)
                .join('');
            transcriptRef.current = current;
            setTranscript(current);
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
        };

        recognition.onerror = () => {
            setVoiceState('idle');
            setTranscript('');
            transcriptRef.current = '';
        };

        recognition.start();
    }, [onSend]);

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop();
    }, []);

    const handleClick = () => {
        if (voiceState === 'idle') {
            startListening();
        } else if (voiceState === 'listening') {
            stopListening();
        }
    };

    const displayText = () => {
        if (voiceState === 'listening') return transcript || 'Listening…';
        if (voiceState === 'processing') return 'Sending to CareFlow…';
        return `"${prompt}"`;
    };

    return (
        <div className="fixed bottom-12 right-12 z-50">
            <motion.button
                key={`${prompt}-${voiceState}`}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                whileHover={{ scale: voiceState === 'idle' ? 1.05 : 1 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleClick}
                disabled={voiceState === 'processing'}
                className={`group relative flex items-center gap-4 px-6 py-4 rounded-full shadow-[0_12px_40px_rgba(0,88,189,0.2)] border border-white/20 transition-all ${
                    voiceState === 'listening'
                        ? 'bg-error text-white'
                        : 'bg-primary-container text-white'
                }`}
            >
                {/* Pulse dots / status indicator */}
                <div className="flex items-center gap-1.5">
                    {voiceState === 'listening' ? (
                        <>
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </>
                    ) : voiceState === 'processing' ? (
                        <Loader2 size={16} className="animate-spin" />
                    ) : (
                        <>
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                            <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
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
                        className="font-bold tracking-tight max-w-[240px] truncate"
                    >
                        {displayText()}
                    </motion.span>
                </AnimatePresence>

                {/* Mic icon */}
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center shrink-0">
                    {voiceState === 'listening' ? <MicOff size={20} /> : <Mic size={20} />}
                </div>
            </motion.button>
        </div>
    );
};

export default VoiceAssistant;
