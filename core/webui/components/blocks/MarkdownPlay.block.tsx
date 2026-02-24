import React, { useState, useEffect, useRef, memo } from "react"
//import Markdown from 'react-markdown'
import sleep from 'sleep-promise'
import RJSON from 'relaxed-json';
import logger from '../../libs/logger';
import MarkdownRenderer, { Markdown } from './MarkdownRenderer';

const MarkdownPlay = (props: any) => {
    const [markdownContent, setMarkdownContent] = useState<string>('')
    const callbackRef = useRef(false);

    const ref = useRef<HTMLDivElement>(null)

    let meta: any = {}
    try {
      meta = RJSON.parse(props.meta ?? "{}")
    } catch (e: any) {
      logger.error(e.message, props.meta)
    }

    useEffect(() => {
        const init = async () => {
            if (props.effect == 'typing') {
                ref.current!.style.opacity = '1'
                ref.current!.style.transition = ''
                for (let i = 0; i < props.content.length; i++) {
                    setMarkdownContent(props.content.substring(0, i))
                    await sleep(15)
                }
            } else {
                setMarkdownContent(props.content)
                await sleep(1)
                ref.current!.style.opacity = '1'

                if(meta.during) await sleep(meta.during)
            }

            if (props.callback) {
                if(callbackRef.current) return
                callbackRef.current = true
                props.callback(props.index, 1)
            }
        }
        init()
    }, [])

    return <div ref={ref} style={{ opacity: 0, transition: 'opacity 1s ease-in-out'}}>
       {
         meta.type == 'code'? 
           <Markdown >{`\`\`\`\n${markdownContent}\n\`\`\``}</Markdown> 
         :
          <MarkdownRenderer linkTarget='_blank' markdown={markdownContent}></MarkdownRenderer>
       }
    </div>
}

export default memo(MarkdownPlay)