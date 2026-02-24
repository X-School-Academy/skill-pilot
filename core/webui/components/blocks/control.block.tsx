import React, { useState, useEffect, useRef, memo } from "react"
import MarkdownRenderer from './MarkdownRenderer';

const ControlBlock = (props: any) => {

    const [isHidden, setIsHidden] = useState(false)
    const [feedback, setFeedback] = useState('')
    const [isDisable, setIsDisable] = useState(false)
    const [showRef, setShowRef] = useState(false)
    const ref = useRef<HTMLDivElement>(null)
    const spinnerRef = useRef<HTMLImageElement | null>(null);
    const [error, setError] = useState('')

    const callbackRef = useRef(false);

    let hint = '';
    let content = props.content;
    const hintEnd = props.content.lastIndexOf("\\```")

    if (hintEnd != -1 ) {
        hint = props.content.substring(0, hintEnd + 4).replaceAll('\\```', '```')
        content = props.content.substring(hintEnd + 4)
    }

    const [showHint, setShowHint] = useState(false)

    const getChildren = () => {
        if (props.content.trim().length == 0)
        {
            if(props.action == 'continue')
                return <div>Press the button below to continue.</div>
            else if (props.action == 'submit')
                return <div>You have successfully reached the end of this AI-powered mentoring course. Now, please submit it to indicate that you have finished this course.</div>
                
        }
        return <MarkdownRenderer linkTarget='_blank' markdown={content}></MarkdownRenderer>
    }


    useEffect(() => {
        if(props.lastStep && props.index && props.lastStep  > props.index) {
            setIsDisable(true)
            setShowRef(true)
            //console.log(`${props.lastStep}, ${props.index}`)
        }

        ref.current!.style.opacity = '1'

        if(props.action == 'nestEnd') {
            if(callbackRef.current) return
            callbackRef.current = true
            props.callback(props.index, 1)
        }

    }, [])

    if (isHidden) {
        return null
    }

    return (
        <div ref={ref} style={{opacity: 0, transition: 'opacity 1s ease-in-out'}}>
            { getChildren()}
            {props.action == 'submit' && 
                <div  className='w-full'>
                    <textarea className='w-full h-40 border-2 border-black rounded p-2 mt-3 mb-5' onChange={(e) => {
                        setFeedback(e.target.value)
                    }} value={feedback}  placeholder="Please leave your feedback here"></textarea>
                </div>
            }
            {
                props.action == 'continue' ?
                <>
                  <div className="flex gap-5 items-end">

                    <button disabled={isDisable} onClick={async (e) => {
                        e.preventDefault()

                        let self = e.currentTarget
                        if(isDisable) {
                            return
                        }

                        if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
                            return
                        }
                        spinnerRef.current?.classList.remove('hidden')

                        setError('')
                        let ret = await props.sendCommand()
                        spinnerRef.current?.classList.add('hidden')

                        if(ret !== true) {    
                            setError(ret)
                            if(!props.warning) {
                                return
                            }
                        }

                        setIsDisable(true)

                        //console.log(`C: ${props.lastStep}, ${props.index}`)

                        //setIsHidden(true)

                        if(callbackRef.current) return
                        callbackRef.current = true
                        props.callback(props.index, 1)
                        
                    }} className={`w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4 ${isDisable && 'disabled:opacity-25'}`}>
                        <span>Continue</span>
                        <div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
                    </button> {!isDisable && props.timeLeft > 0 && `About ${props.timeLeft} minutes left for the rest.`}
                  </div>

                    {error && <div style={{color: 'red', margin: 10}}>
                        {error}
                    </div>}
                    {error && hint && <a href="#" onClick={(e)=> {
                            e.preventDefault()
                            setShowHint(!showHint)
                        }}>Show Hint?</a>}
                    {error && showHint && <MarkdownRenderer linkTarget='_blank' markdown={hint}></MarkdownRenderer>}
                    {(error || showRef) && props.refInfo && 
                        ( props.refInfo.startsWith("http")?<div>If you need help for this topic, please check this {props.refInfo.includes('youtube')?'video':'url'}: <a href={props.refInfo} target="_blank">props.refInfo</a></div>
                        :(
                            props.refInfo=="ai"? "If you need help for this topic, please use the AI prompts section above.":props.refInfo
                        ))
                    }
                </>:
                (
                    (props.action == 'submit' || props.action == 'use_skill') && 
                    <>
                         <div  className='w-full'>
                            <textarea className='w-full h-40 border-2 border-black rounded p-2 mt-3 mb-5' onChange={(e) => {
                                setFeedback(e.target.value)
                            }} value={feedback}  placeholder={props.action == 'use_skill' ? "Please enter your request here" : "Please leave your feedback here"}></textarea>
                        </div>
                        <div className="flex gap-5 items-end">
                            <button disabled={isDisable} onClick={async (e) => {
                                e.preventDefault()
                                if(isDisable) {
                                    return
                                }

                                if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
                                    return
                                }

                                if(feedback.trim().length == 0) {
                                    setError(props.action == 'use_skill' ? 'Please enter your request before using the skill.' : 'Please leave your feedback before submitting.')
                                    return
                                }

                                if (props.action == 'use_skill') {
                                    const skillName = props.skill_name || 'unknown-skill';
                                    const prompt = `Use agent skill ${skillName}, as user's request below: ${feedback}`;
                                    window.location.href = `/?new_session=true&prompt=${encodeURIComponent(prompt)}`;
                                    return;
                                }

                                spinnerRef.current?.classList.remove('hidden')
        
                                setError('')
                                let ret = await props.sendCommand(feedback)
                                spinnerRef.current?.classList.add('hidden')

                                if(ret !== true) {    
                                    setError(ret)
                                    return
                                }
        
                                setIsDisable(true)
        
                                if(callbackRef.current) return
                                callbackRef.current = true
                                props.callback(props.index, 1)

                            }} className={`w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4 ${isDisable && 'disabled:opacity-25'}`}>
                                <span>{props.action == 'use_skill' ? 'Use Agent Skill' : 'Submit'}</span>
                                <div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
                            </button>
                        </div>
                    </>
                )
            }
            <style jsx>{`
                .loader {
                    border: 3px solid #f3f3f3;
                    border-radius: 50%;
                    border-top: 3px solid #3498db;
                    width: 20px;
                    height: 20px;
                    -webkit-animation: spin 2s linear infinite; /* Safari */
                    animation: spin 2s linear infinite;
                    }
                    
                    /* Safari */
                    @-webkit-keyframes spin {
                    0% { -webkit-transform: rotate(0deg); }
                    100% { -webkit-transform: rotate(360deg); }
                    }
                    
                    @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                    }
                }
            `}</style>
        </div>
    )

}

export default memo(ControlBlock)