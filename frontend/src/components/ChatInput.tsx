import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, Square, ArrowUp, Mic, MicOff, Loader2, Bot, X, FileText, Image as ImageIcon } from 'lucide-react';
import clsx from 'clsx';
import { transcribeAudio } from '../api/client';

export interface Attachment {
    name: string;
    type: string;
    content: string; // base64
}

interface Props {
    onSend: (text: string, attachments?: Attachment[]) => void;
    disabled?: boolean;
    isSending?: boolean;
    onStop?: () => void;
    secretaryMode?: boolean;
    onSecretaryModeChange?: (enabled: boolean) => void;
}

export const ChatInput: React.FC<Props> = ({ onSend, disabled, isSending, onStop, secretaryMode, onSecretaryModeChange }) => {
    const [text, setText] = useState("");
    const [files, setFiles] = useState<Attachment[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [recording, setRecording] = useState(false);
    const [transcribing, setTranscribing] = useState(false);
    const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
    const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
    const [volume, setVolume] = useState(0);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const rafRef = useRef<number>();

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if ((text.trim() || files.length > 0) && !disabled) {
            onSend(text, files);
            setText("");
            setFiles([]);
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles: Attachment[] = [];
            for (let i = 0; i < e.target.files.length; i++) {
                const file = e.target.files[i];
                if (file.size > 5 * 1024 * 1024) { // 5MB limit
                    alert(`File ${file.name} is too large (max 5MB)`);
                    continue;
                }

                try {
                    const base64 = await convertToBase64(file);
                    newFiles.push({
                        name: file.name,
                        type: file.type,
                        content: base64 as string
                    });
                } catch (err) {
                    console.error("Error reading file", err);
                }
            }
            setFiles(prev => [...prev, ...newFiles]);
            // Reset input so same file can be selected again if needed
            e.target.value = '';
        }
    };

    const convertToBase64 = (file: File) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    // Auto-grow textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
        }
    }, [text]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopRecordingInternal();
        };
    }, []);

    const stopRecordingInternal = () => {
        if (recorder && recorder.state !== "inactive") {
            recorder.stop();
        }
        if (mediaStream) {
            mediaStream.getTracks().forEach(t => t.stop());
        }
        if (analyserRef.current) {
            analyserRef.current.disconnect();
            analyserRef.current = null;
        }
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        setVolume(0);
        setMediaStream(null);
        setRecorder(null);
        setRecording(false);
    };

    const startRecording = async () => {
        if (!navigator.mediaDevices || !window.MediaRecorder) {
            alert("Voice input is not supported in this browser.");
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            const preferredMime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
            const mediaRecorder = preferredMime
                ? new MediaRecorder(stream, { mimeType: preferredMime })
                : new MediaRecorder(stream);
            const chunks: Blob[] = [];
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                }
            };
            mediaRecorder.onstop = async () => {
                setRecording(false);
                if (chunks.length === 0) return;
                const blob = new Blob(chunks, { type: preferredMime || 'audio/webm' });
                setTranscribing(true);
                try {
                    const res = await transcribeAudio(blob);
                    setText(prev => prev ? `${prev} ${res.data.text}` : res.data.text);
                } catch (err) {
                    console.error("Transcription failed", err);
                    alert("Не вдалося розпізнати аудіо, спробуйте ще раз.");
                } finally {
                    setTranscribing(false);
                }
            };
            mediaRecorder.start();
            setRecorder(mediaRecorder);
            setRecording(true);
            setMediaStream(stream);

            // Volume visualization
            const audioCtx = new AudioContext();
            const source = audioCtx.createMediaStreamSource(stream);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            analyserRef.current = analyser;
            const dataArray = new Uint8Array(analyser.frequencyBinCount);

            const tick = () => {
                analyser.getByteTimeDomainData(dataArray);
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    const v = (dataArray[i] - 128) / 128;
                    sum += v * v;
                }
                const rms = Math.sqrt(sum / dataArray.length);
                setVolume(Math.min(1, rms * 4)); // normalize to 0..1-ish
                rafRef.current = requestAnimationFrame(tick);
            };
            tick();

            // Auto stop after 30 seconds
            setTimeout(() => {
                if (mediaRecorder.state === "recording") {
                    mediaRecorder.stop();
                }
            }, 30000);
        } catch (err) {
            console.error("Microphone error", err);
            alert("Не вдалося отримати доступ до мікрофона.");
        }
    };

    const stopRecording = () => {
        stopRecordingInternal();
    };

    return (
        <div className="w-full max-w-4xl mx-auto px-2 sm:px-4 pb-4 sm:pb-6 pt-2">
            {files.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 px-1">
                    {files.map((file, i) => (
                        <div key={i} className="relative group bg-gray-800 border border-gray-700 rounded-lg p-2 pr-8 flex items-center gap-2">
                            {file.type.startsWith('image/') ? (
                                <ImageIcon size={16} className="text-blue-400" />
                            ) : (
                                <FileText size={16} className="text-gray-400" />
                            )}
                            <span className="text-xs text-gray-200 truncate max-w-[150px]">{file.name}</span>
                            <button
                                onClick={() => removeFile(i)}
                                className="absolute right-1 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-red-400 rounded-full hover:bg-white/5"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            <div className={clsx(
                "relative flex items-end gap-2 bg-gray-800/80 backdrop-blur-xl border border-white/10 rounded-2xl sm:rounded-3xl p-2 shadow-2xl shadow-black/20 transition-all duration-200",
                "focus-within:border-primary-500/30 focus-within:ring-1 focus-within:ring-primary-500/20"
            )}>
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    className="hidden"
                    multiple
                />

                {/* Attachment Button */}
                <button
                    className="p-3 text-gray-400 hover:text-gray-200 hover:bg-white/5 rounded-full transition-colors mb-0.5"
                    title="Add attachment"
                    onClick={() => fileInputRef.current?.click()}
                >
                    <Paperclip size={20} />
                </button>

                {/* Secretary Mode Toggle */}
                {onSecretaryModeChange && (
                    <button
                        onClick={() => onSecretaryModeChange(!secretaryMode)}
                        className={clsx(
                            "p-3 rounded-full transition-colors mb-0.5",
                            secretaryMode
                                ? "text-emerald-400 bg-emerald-400/10 hover:bg-emerald-400/20"
                                : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                        )}
                        title={secretaryMode ? "Secretary Mode ON" : "Secretary Mode OFF"}
                    >
                        <Bot size={20} />
                    </button>
                )}

                <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message..."
                    disabled={disabled}
                    rows={1}
                    className="flex-1 bg-transparent border-none focus:ring-0 text-gray-100 placeholder:text-gray-500 resize-none py-3.5 max-h-[200px] scrollbar-hide"
                    style={{ minHeight: '52px' }}
                />

                {/* Mic Button */}
                <button
                    type="button"
                    onClick={() => recording ? stopRecording() : startRecording()}
                    disabled={disabled || isSending || transcribing}
                    className={clsx(
                        "p-3 rounded-full mb-0.5 transition-all duration-200 flex items-center justify-center",
                        recording ? "bg-red-600 text-white animate-pulse" : "bg-gray-700 text-gray-300 hover:bg-gray-600",
                        (disabled || isSending || transcribing) && "opacity-50 cursor-not-allowed"
                    )}
                    title={recording ? "Зупинити запис" : "Голосове введення"}
                >
                    {transcribing ? <Loader2 className="animate-spin" size={18} /> : recording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>

                {/* Volume meter */}
                {recording && (
                    <div className="h-12 w-2 bg-gray-700 rounded-full overflow-hidden flex items-end">
                        <div
                            className="w-full bg-red-500 transition-all duration-75"
                            style={{ height: `${Math.round(volume * 100)}%` }}
                        />
                    </div>
                )}

                {/* Send / Stop Button */}
                {isSending ? (
                    <button
                        onClick={onStop}
                        className="p-3 rounded-full mb-0.5 transition-all duration-200 flex items-center justify-center bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/20"
                        title="Зупинити генерацію"
                    >
                        <Square size={18} />
                    </button>
                ) : (
                    <button
                        onClick={() => handleSubmit()}
                        disabled={(!text.trim() && files.length === 0) || disabled}
                        className={clsx(
                            "p-3 rounded-full mb-0.5 transition-all duration-200 flex items-center justify-center",
                            (text.trim() || files.length > 0) && !disabled
                                ? "bg-primary-600 text-white hover:bg-primary-500 shadow-lg shadow-primary-900/20 scale-100"
                                : "bg-gray-700 text-gray-500 cursor-not-allowed"
                        )}
                    >
                        <ArrowUp size={20} />
                    </button>
                )}
            </div>

            <div className="text-center mt-2">
                <p className="text-[10px] text-gray-500">
                    AI can make mistakes. Please verify important information.
                </p>
            </div>
        </div>
    );
};

