import React, { useRef, useCallback, useState } from 'react';
import { MicrophoneIcon} from "@heroicons/react/24/solid";
import MarkdownRenderer from './MarkdownRenderer';

export const AudioResponse = (props: any) => {

    const audioStarted = useRef(0);
    const audioEnded = useRef(0);
    const micRef = useRef<any | null>(null);
    const spinnerRef = useRef<HTMLImageElement | null>(null);
    const callbackRef = useRef(false);
    const [showAudio, setShowAudio] = useState(false)
    const [error, setError] = useState('')
    const [suggestion, setSuggestion] = useState('')

    const handleData = async (formData: FormData) => {
        try {
            if (spinnerRef.current && !spinnerRef.current.classList.contains("hidden")) {
                return;
            }
            spinnerRef.current?.classList.remove("hidden");
            
            spinnerRef.current?.classList.add("hidden");
        } catch (error) {
            console.log(error);
            setError(`Oops! Something went wrong. Please try again.`);
            spinnerRef.current?.classList.add("hidden");
        }
    }

    const onTranscribe = async (blob: Blob) => {
        if (audioEnded.current - audioStarted.current < 3000) {
            console.log("audio too short", audioEnded.current - audioStarted.current);
            return {
                blob,
                text: "NO",
            };
        }

        console.log(
            "blob sent to server",
            blob.size,
            audioEnded.current - audioStarted.current
        );

        const formData = new FormData();
        formData.append("file", blob, "audio.mp3");
        formData.append("fromLang", props.fromLang);
        formData.append("toLang", props.toLang);
        formData.append("action", "response");
        formData.append("content", props.content);
        handleData(formData);

        return {
            blob,
            text: "OK",
        };
    };

    return (
        <div className="flex flex-col gap-3">
            <div>
                <MarkdownRenderer markdown={props.content}></MarkdownRenderer>
            </div>
            { showAudio && <audio controls>
                <source src={props.audioUrl} type="audio/mpeg" />
                Your browser does not support the audio element.
            </audio>
            }
            <div className="audio-response">
            <button
                ref={micRef}
                className="select-none"
                onContextMenu={(e) => e.preventDefault()}
                >
                <MicrophoneIcon className="w-7 h-7 text-primary-blue hover:text-red cursor-pointer select-none" />
                <div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
                </button>
            </div>
            {error &&<>
             <div style={{color: 'red'}}>
                {error}
            </div>
            <MarkdownRenderer markdown={suggestion}></MarkdownRenderer>
            </>
            }
        
            <style jsx>{`
                .audio-response {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 1rem 0;
                    gap: 1rem;
                }

                .loader {
                    border: 3px solid #7dbde8;
                    border-radius: 50%;
                    border-top: 3px solid #3498db;
                    width: 20px;
                    height: 20px;
                    -webkit-animation: spin 2s linear infinite; /* Safari */
                    animation: spin 2s linear infinite;
                }

                /* Safari */
                @-webkit-keyframes spin {
                    0% {
                    -webkit-transform: rotate(0deg);
                    }
                    100% {
                    -webkit-transform: rotate(360deg);
                    }
                }

                @keyframes spin {
                    0% {
                    transform: rotate(0deg);
                    }
                    100% {
                    transform: rotate(360deg);
                    }
                }

                .heart {
                    color: #e00;
                    animation: beat 0.25s infinite alternate;
                    transform-origin: center;
                }
        
                @keyframes beat {
                    0% {
                        transform: scale(0.8);
                    }
                    100% {
                        transform: scale(1.2);
                    }
                }
            `}</style>
        </div>
    );
}