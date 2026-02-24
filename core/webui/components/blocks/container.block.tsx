import React, { useState, useEffect, useRef, memo } from "react"

const ContainerBlock = (props: any) => {
    //props.containerType: 0 - cpu, 1 - gpu

    const [isDisable, setIsDisable] = useState(false)
    const [descriptionText, setDescriptionText] = useState(`Please click the button below to start your JuniorIT.AI cloud development container. It will take from a few seconds and up to 2 minutes depending on the cloud development container availability.`)
    const [buttonText, setButtonText] = useState('Start')
    const ref = useRef<HTMLDivElement>(null)
    const spinnerRef = useRef<HTMLImageElement | null>(null)
    const timerRef = useRef<any>(null)
    const counterDownRef = useRef(120)
    const containerInfo = useRef<any>({})
    const [error, setError] = useState('')
    const [selectedContainerType, setSelectedContainerType] = useState(props.containerType)

    const callbackRef = useRef(false);

    useEffect(()=>{

        return ()=>{
            if(timerRef.current) {
                clearInterval(timerRef.current)
                timerRef.current = null
            }
        }

    }, [])
    
    return (
        <div ref={ref}>
            {selectedContainerType > 0 && <div className="my-5">
                <label className="text-primary-blue font-medium" htmlFor="gpuContainerType">Select GPU Development Environment</label>
                    <select
                        id="gpuContainerType"
                        className="w-full h-10 border-primary-blue text-primary-blue font-medium bg-white"
                        value={selectedContainerType}
                        onChange={(e) => {
                            setSelectedContainerType(parseInt(e.target.value))
                            if(e.target.value == '1') {
                                setDescriptionText(`Please click the button below to start your JuniorIT.AI cloud development container.`)
                            } if(e.target.value == '2') {
                                setDescriptionText(`Please click the button below to start your JuniorIT.AI cloud development container.`)
                            }  else {
                                setDescriptionText(`Please click the button below to start your cloud development container.`)
                            }
                        }}>
                            <option value="1">JuniorIT.AI GPU Container</option>
                            <option value="2">Kaggle notebook</option>
                            <option value="3">Linux x86_64 with NVIDIA GPU</option>
                    </select>
                
            </div>}
            
            <div className="my-5">
                {descriptionText}
            </div> 
        
            <div className="flex gap-5 items-end">

                <button disabled={isDisable} onClick={async (e) => {
                    e.preventDefault()

                    if(isDisable) {
                        return
                    }

                    if(buttonText == 'Start') {
                        spinnerRef.current?.classList.remove('hidden')
                        setDescriptionText(`Please wait, we are currently provisioning a cloud development container for you.`)
                        props.createContainer(selectedContainerType)
                        if(timerRef.current) return

                        counterDownRef.current = 120

                        timerRef.current = setInterval(()=> {
                            setButtonText(`Ready in ${counterDownRef.current}s`)

                            counterDownRef.current --

                            if(counterDownRef.current < 5) counterDownRef.current = 20;
                            if(counterDownRef.current % 5 != 0) {
                                return
                            }

                            let container = props.createContainer(selectedContainerType)
                            if(!container) return

                            console.log(container.info)

                            containerInfo.current = JSON.parse(container.info)

                            if(container.status == 'request-no-gpu') {

                                clearInterval(timerRef.current)
                                timerRef.current = null
                                setIsDisable(false)

                                setButtonText('Start')

                                spinnerRef.current?.classList.add('hidden')

                                setDescriptionText(`There is no JuniorIT.AI GPU container available at the moment. Please select another option or try again later.`)
 
                                return;
                            }
        
                            if(container.status && ['created', 'online'].includes(container.status) && containerInfo.current.url) {
                                if(props.containerType === 0) {
                                    setDescriptionText(`JuniorIT.AI cloud development container is ready for you, please click the button below to launch it.`)
                                } else {
                                    setDescriptionText(`Your cloud development container is ready for you, please click the button below to launch it.`)
                                }

                                setButtonText('Launch')
                                clearInterval(timerRef.current)
                                timerRef.current = null
                                setIsDisable(false)

                                spinnerRef.current?.classList.add('hidden')
                            }
                        }, 1000)

                        setIsDisable(true)

                        return
                    } else if(buttonText == 'Launch') {
                        if (window.self == window.top) {
                            window.open(containerInfo.current.url)
                        } else {
                            const message = {type: 'open_code', url: containerInfo.current.url };
                            window.parent.postMessage(message, "*");
                        }
                    } else {
                        return
                    }

                    if(callbackRef.current) return
                    callbackRef.current = true
                    props.callback(props.index, 1)
                    
                }} className={`w-auto rounded whitespace-nowrap h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4 ${isDisable && 'disabled:opacity-25'}`}>
                    <span>{buttonText}</span>
                    <div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
                </button>
            </div>

        {error && 
        <div style={{color: 'red', margin: 10}}>
            {error}
        </div>}
  
            
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

export default memo(ContainerBlock)