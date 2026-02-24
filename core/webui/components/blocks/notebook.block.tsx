import React, { useState, useEffect, useRef, memo } from "react"
import sleep from 'sleep-promise'
import RJSON from 'relaxed-json';
import yaml from 'js-yaml';
import logger from '../../libs/logger';
import MarkdownRenderer from './MarkdownRenderer';
import { DocumentDuplicateIcon, DocumentArrowDownIcon, ClipboardIcon, QuestionMarkCircleIcon} from '@heroicons/react/24/solid'

import SyntaxHighlighterBase from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

const SyntaxHighlighter = SyntaxHighlighterBase as unknown as React.ComponentType<any>;

interface BlockElementProps {
    key: any,
    block: any,
    lang: string,
    file: string,
    bookType: string,
    sendCode: any
}

const BlockElement = (props: BlockElementProps) => {
    const [showPrompt, setShowPrompt] = useState(false)

    return <div className="flex flex-row items-end">
        <div className="w-full">
            <div className="flex flex-row">
                <div style={{flex: 1,  marginTop: 5}}><MarkdownRenderer markdown={props.block.instruction}/></div>
            </div>

            <div style={{ position: 'relative', margin: '5px 0', padding: '5px 10px', borderRadius: '0.375rem', color: 'rgb(248, 248, 242)', backgroundColor: 'rgb(43, 43, 43)'}}>
                <div style={{flex: 1,  marginTop: 5}}>
                    <SyntaxHighlighter language={props.lang}  style={a11yDark}>
                    {props.block.code}
                    </SyntaxHighlighter>
                </div>
                <div style={{position: 'absolute', top: 5, right: 5}}>
                    <DocumentDuplicateIcon className="w-6 h-6  hover:opacity-60 opacity-80 cursor-pointer inline select-none mx-1" title="Copy to file" onClick={() => {
                         if (props.sendCode) {
                            props.sendCode(props.bookType, props.file, props.lang, props.block.code, false)
                         }
                    }}></DocumentDuplicateIcon>

                    {props.bookType == 'notebook' &&
                        <DocumentArrowDownIcon className="w-6 h-6 hover:opacity-60 opacity-80 cursor-pointer inline select-none mx-1" title="Copy to file & execute" onClick={() => {
                            if (props.sendCode) {
                                props.sendCode(props.bookType, props.file, props.lang, props.block.code, true)
                            }
                        }}></DocumentArrowDownIcon>
                    }

                    <ClipboardIcon className="w-6 h-6 hover:opacity-60 opacity-80 cursor-pointer inline select-none mx-1"  title="Copy to clipboard" onClick={() => {
                         navigator.clipboard.writeText(props.block.code).then(function() {
                        }).catch(function(err) {
                            console.error('Error in copying text: ', err);
                        });
                    }}></ClipboardIcon>

                    <QuestionMarkCircleIcon className="w-6 h-6 hover:opacity-60 opacity-80 cursor-pointer inline select-none mx-1"  title="Ask AI for assistance" onClick={() => {
                        setShowPrompt(!showPrompt);
                    }}></QuestionMarkCircleIcon>
                </div>
            </div>

            {showPrompt && <div className="w-full flex flex-col items-center mt-5">
                <MarkdownRenderer markdown={`\`\`\`markdown {type:chat}
${props.block.prompt}

${props.block.code}
\`\`\``}></MarkdownRenderer>
             <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50 select-none" onClick={() => {
                    setShowPrompt(false);
                }}>close</button>
            </div>}
        </div>
    </div>
}

const NotebookBlock = (props: any) => {
    const callbackRef = useRef(false);

    const ref = useRef<HTMLDivElement>(null)

    const file = props.file;
    const bookType = props.bookType; // codeBook, notebook
    const lang = props.lang;

    const blocks: any = yaml.load(props.yml);

    let meta: any = {}
    try {
      meta = RJSON.parse(props.meta ?? "{}")
    } catch (e: any) {
      logger.error(e.message)
    }

    useEffect(() => {
        const init = async () => {

            await sleep(1)
            ref.current!.style.opacity = '1'

            if(meta.during) await sleep(meta.during)
            

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
            blocks.map((block: any, index: any) => <BlockElement key={index} block={block} lang={lang} file={file} bookType={bookType} sendCode={props.sendCode}></BlockElement>)
       }
    </div>
}

export default memo(NotebookBlock)
