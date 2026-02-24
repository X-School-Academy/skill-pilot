import React, { useState, useEffect, useRef, memo } from "react"
import sleep from 'sleep-promise'
import RJSON from 'relaxed-json';
import logger from '../../libs/logger';
import { ClipboardIcon } from '@heroicons/react/24/solid'

import SyntaxHighlighterBase from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

const SyntaxHighlighter = SyntaxHighlighterBase as unknown as React.ComponentType<any>;

const BashBlock = (props: any) => {
    const [content, setContent] = useState<string>('')
    const callbackRef = useRef(false);

    const ref = useRef<HTMLDivElement>(null)
    const commentsRef = useRef('')

    let meta: any = {}
    try {
      meta = RJSON.parse(props.meta ?? "{}")
    } catch (e: any) {
      logger.error(e.message)
    }

    useEffect(() => {
        const init = async () => {

            setContent(props.content)
            await sleep(1)
            ref.current!.style.opacity = '1'

            if(meta.during) await sleep(meta.during)
            

            if (props.callback) {
                if(callbackRef.current) return
                callbackRef.current = true
                props.callback(props.index, 1)

                // Terminal integration removed.
            }
        }
        init()
    }, [])

    return <div ref={ref} style={{ opacity: 0, transition: 'opacity 1s ease-in-out'}}>
            {/*<a href="javascript: void(0)" className="no-underline"><PaperAirplaneIcon className="w-6 h-6 inline mx-2 opacity-80 text-primary-blue"/>Shown on the right-side tab window in Visual Studio Code</a>*/}
       {
            content.split('\n').map((line, index) => {

                if (line.indexOf("#") == 0) {
                    if(commentsRef.current) commentsRef.current += '\n'
                    commentsRef.current += line
                    line = ''
                }

                if (!line) return null

                let comments = commentsRef.current
                commentsRef.current = ''

                return <div key={index} className="flex flex-row items-end">
                    <div style={{flex: 1, color: 'rgb(248, 248, 242)', backgroundColor: 'rgb(43, 43, 43)', borderRadius: '0.375rem', margin: '5px 0', padding: '5px 10px'}}>
                        {comments && comments.split('\n').map((row, idx) => 
                        <div key={idx}>
                            <SyntaxHighlighter language="bash" customStyle={{margin: 0, padding: 3}} style={a11yDark}>
                            {row}&nbsp;
                            </SyntaxHighlighter>
                        </div>)
                        }
                        <div className="flex flex-row">
                            <div style={{flex: 1,  marginTop: 5}}>
                                <SyntaxHighlighter language="bash" customStyle={{margin: 0, padding: 3}} style={a11yDark}>
                                {line}
                                </SyntaxHighlighter>
                            </div>
                            <div>
                                <ClipboardIcon className="w-6 h-6 hover:opacity-60 opacity-80 cursor-pointer inline select-none mx-1"  title="Copy to clipboard" onClick={() => {
                                     navigator.clipboard.writeText(line).then(function() {
                                    }).catch(function(err) {
                                        console.error('Error in copying text: ', err);
                                    });
                                }}></ClipboardIcon>
                            </div>
                        </div>
                    </div>
                </div>
            })
       }
    </div>
}

export default memo(BashBlock)
