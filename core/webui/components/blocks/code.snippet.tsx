import React, { useEffect, useRef, useState, memo } from "react";
import {basicSetup} from "codemirror"
import { EditorState } from "@codemirror/state"
import { EditorView, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, keymap, dropCursor, rectangularSelection, crosshairCursor } from "@codemirror/view"
import { history, indentWithTab } from "@codemirror/commands"
//import { javascript } from "@codemirror/lang-javascript"
//import { javascript, typescript } from "@codemirror/legacy-modes/mode/javascript"
import { python } from "@codemirror/lang-python"
import { php } from "@codemirror/lang-php"
import { json } from "@codemirror/lang-json"
import { rust } from "@codemirror/lang-rust"
import { markdown } from "@codemirror/lang-markdown"
import { java } from "@codemirror/lang-java"
import { bracketMatching, defaultHighlightStyle, foldGutter, StreamLanguage, indentOnInput, syntaxHighlighting, HighlightStyle } from "@codemirror/language";
import { autocompletion, closeBrackets } from "@codemirror/autocomplete";
import { dart, kotlin } from "@codemirror/legacy-modes/mode/clike"
import { swift } from "@codemirror/legacy-modes/mode/swift"
import { highlightSelectionMatches } from "@codemirror/search";
import styled from 'styled-components';
import logger from '../../libs/logger';
import MarkdownRenderer, { Markdown } from './MarkdownRenderer';
import { draculaHighlightStyle } from '@ddietr/codemirror-themes/dracula'
import { tags } from '@lezer/highlight';
import { useTranslation } from 'next-i18next'
import RJSON from 'relaxed-json'
//import Markdown from 'react-markdown'
import { PaperClipIcon } from '@heroicons/react/24/solid'
import { useSelector } from "react-redux";
import { ReduxStoreState } from "../../types/store";
import {  getHeader } from "../../libs/auth-header";
import { apiUrl } from "../../libs/api-base";
import { dispatchLlmStatus, getClientId, getSelectedProvider } from "../../libs/llm";

const config = {
  name: 'dracula',
  dark: true,
  background: '#282A36',
  foreground: '#F8F8F2',
  selection: '#ef4146',
  selectionMatch: '#ef414644',
  cursor: '#F8F8F2',
  dropdownBackground: '#282A36',
  dropdownBorder: '#191A21',
  activeLine: '#44475A00',
  matchingBracket: '#ef4146',
  keyword: '#FF79C6',
  storage: '#FF79C6',
  variable: '#F8F8F2',
  parameter: '#F8F8F2',
  function: '#50FA7B',
  string: '#F1FA8C',
  constant: '#BD93F9',
  type: '#8BE9FD',
  class: '#8BE9FD',
  number: '#BD93F9',
  comment: '#909cc3',
  heading: '#BD93F9',
  invalid: '#FF5555',
  regexp: '#F1FA8C',
};
const _draculaTheme = EditorView.theme({
  '&': {
    color: config.foreground,
    backgroundColor: config.background,
  },
  '.cm-content': { caretColor: config.cursor },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: config.cursor },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': { backgroundColor: config.selection + ' !important'},
  '.cm-panels': { backgroundColor: config.dropdownBackground, color: config.foreground },
  '.cm-panels.cm-panels-top': { borderBottom: '2px solid black' },
  '.cm-panels.cm-panels-bottom': { borderTop: '2px solid black' },
  '.cm-searchMatch': {
    backgroundColor: config.dropdownBackground,
    outline: `1px solid ${config.dropdownBorder}`
  },
  '.cm-searchMatch.cm-searchMatch-selected': {
    backgroundColor: config.selectionMatch
  },
  '.cm-activeLine': { backgroundColor: config.activeLine, border: '1px dotted #44475A' },
  '.cm-selectionMatch': { backgroundColor: config.selectionMatch },
  '&.cm-focused .cm-matchingBracket, &.cm-focused .cm-nonmatchingBracket': {
    backgroundColor: config.matchingBracket,
    outline: 'none'
  },
  '.cm-gutters': {
    backgroundColor: config.background,
    color: config.foreground,
    border: 'none'
  },
  '.cm-activeLineGutter': { backgroundColor: config.background },
  '.cm-foldPlaceholder': {
    backgroundColor: 'transparent',
    border: 'none',
    color: config.foreground
  },
  '.cm-tooltip': {
    border: `1px solid ${config.dropdownBorder}`,
    backgroundColor: config.dropdownBackground,
    color: config.foreground,
  },
  '.cm-tooltip .cm-tooltip-arrow:before': {
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent'
  },
  '.cm-tooltip .cm-tooltip-arrow:after': {
    borderTopColor: config.foreground,
    borderBottomColor: config.foreground,
  },
  '.cm-tooltip-autocomplete': {
    '& > ul > li[aria-selected]': {
      background: config.selection,
      color: config.foreground,
    }
  }
}, { dark: config.dark });

const _draculaHighlightStyle = HighlightStyle.define([
  { tag: tags.keyword, color: config.keyword },
  { tag: [tags.name, tags.deleted, tags.character, tags.macroName], color: config.variable },
  { tag: [tags.propertyName], color: config.function },
  { tag: [tags.processingInstruction, tags.string, tags.inserted, tags.special(tags.string)], color: config.string },
  { tag: [tags.function(tags.variableName), tags.labelName], color: config.function },
  { tag: [tags.color, tags.constant(tags.name), tags.standard(tags.name)], color: config.constant },
  { tag: [tags.definition(tags.name), tags.separator], color: config.variable },
  { tag: [tags.className], color: config.class },
  { tag: [tags.number, tags.changed, tags.annotation, tags.modifier, tags.self, tags.namespace], color: config.number },
  { tag: [tags.typeName], color: config.type, fontStyle: config.type },
  { tag: [tags.operator, tags.operatorKeyword], color: config.keyword },
  { tag: [tags.url, tags.escape, tags.regexp, tags.link], color: config.regexp },
  { tag: [tags.meta, tags.comment], color: config.comment },
  { tag: tags.strong, fontWeight: 'bold' },
  { tag: tags.emphasis, fontStyle: 'italic' },
  { tag: tags.link, textDecoration: 'underline' },
  { tag: tags.heading, fontWeight: 'bold', color: config.heading },
  { tag: [tags.atom, tags.bool, tags.special(tags.variableName)], color: config.variable },
  { tag: tags.invalid, color: config.invalid },
  { tag: tags.strikethrough, textDecoration: 'line-through' },
]);

const theme = [
  _draculaTheme,
  syntaxHighlighting(_draculaHighlightStyle),
];

interface Props {
  lang: string;
  meta: string;
  source: string;
  codes: string;
  readOnly?: boolean;
  noActions?: boolean;
  cancelCallback: () => void;
  saveCallback: (code: string) => void;
}

let Log = styled.div`
font-family:system-ui;font-size:14px; margin: 10px 0;
`

let Pre = styled.pre`
color: black;
margin-top: 0px !important;
border: 1px solid #cccccc55 !important;
background-color: white !important;
white-space: pre-wrap !important;
`

const CodeSnippet = (props: Props) => {

  const user = useSelector((state: ReduxStoreState) =>  state.user.user);
  const apiServerToken = useSelector((state: ReduxStoreState) =>  state.apiServerToken.apiServerToken);

  const editorRef = useRef<HTMLDivElement | null>(null);
  const spinnerRef = useRef<HTMLImageElement | null>(null);
  const fixSpinnerRef = useRef<HTMLImageElement | null>(null);

  const extraInfoRef = useRef<HTMLTextAreaElement | null>(null);

  const [editView, setEditView] = useState<EditorView | null>(null);
  const [output, setOutput] = useState("");
  const [sourceCode, setSourceCode] = useState(props.codes);

  const [chatDone, setChatDone] = useState(true);

  const [outputElements, setOutputElements] = useState<any[]>([]);


  const { t } = useTranslation('common')

  let meta: any = {}
  try {
    meta = RJSON.parse(props.meta ?? "{}")
  } catch (e: any) {
    logger.error(e.message)
  }

  if (!meta.api) meta.api = null

  let supported = true

  let extensions = [
    basicSetup,
    EditorView.lineWrapping,
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    history(),
    foldGutter(),
    //drawSelection(),
    dropCursor(),
    indentOnInput(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    rectangularSelection(),
    crosshairCursor(),
    //highlightActiveLine(),
    highlightSelectionMatches(),
    EditorState.allowMultipleSelections.of(false),
    keymap.of([indentWithTab]),
  ];

  switch (props.lang) {
    case 'javascript':
      //extensions.push(lineNumbers())
      //extensions.push(javascript({ typescript: false }))
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(javascript)]
      extensions.push(lineNumbers())
      extensions.push(java())
      break
    case 'typescript':
      //extensions.push(javascript({ typescript: true }))
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(typescript)]
      extensions.push(lineNumbers())
      extensions.push(java())
      break
    case 'python':
      extensions.push(lineNumbers())
      extensions.push(python())
      break
    case 'markdown':
      extensions.push(markdown())
      break
    case 'php':
      extensions.push(lineNumbers())
      extensions.push(php({ plain: true }))
      break
    case 'java':
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(java)]
      break
    case 'kotlin':
      extensions = [...extensions, lineNumbers(), StreamLanguage.define(kotlin)]
      break
    case 'swift':
      extensions = [...extensions, lineNumbers(), StreamLanguage.define(swift)]
      break
    case 'json':
      extensions.push(lineNumbers())
      extensions.push(json())
      break
    case 'objc':
    case 'objective-c':
    case 'c':
    case 'cpp':
    case 'c++':
    case 'go':
    case 'dart':
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      break
    case 'rs':
    case 'rust':
      extensions.push(lineNumbers())
      extensions.push(rust())
      break
    default:
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      supported = false
  }

  supported = true

  extensions.push(theme)

  if (props.readOnly || meta.readOnly) {
    extensions.push(EditorView.editable.of(false))
  }

  const state = EditorState.create({
    doc: props.codes,
    extensions
  });

  useEffect(() => {
    if (editorRef == null || editorRef.current == null) {
      return;
    }

    viewRef.current = new EditorView({ state, parent: editorRef.current });

    setEditView(viewRef.current);

    return () => {
      viewRef?.current?.destroy();
    };
    
  },[])


  useEffect(() => {

    if (editView == null) return

    let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: sourceCode }, 
          selection: {
              anchor: sourceCode.length,
              head: sourceCode.length
          }, 
          scrollIntoView:true  
        })
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })

  }, [sourceCode])

  useEffect(() => {

    if (editView == null) return

    let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: props.codes } })
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })

  }, [props.codes])


  const viewRef = useRef<any | null>(null);

  const handleRun = async (isComplete: boolean) => {

    let code = viewRef?.current.state.doc.toString()

    if (code.length < 2) return

    if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
      return
    }
    if (fixSpinnerRef.current && !fixSpinnerRef.current.classList.contains('hidden')) {
      return
    }

    if(isComplete)
      spinnerRef.current?.classList.remove('hidden')
    else
      fixSpinnerRef.current?.classList.remove('hidden')

    setOutput("")
    try {

      let dataReceived = false
      let chatResponse = "";

      let lang = props.lang
      let message = code

      let src = props.source.toLowerCase()

      if (src.indexOf('dart lang') > -1) {
        lang = 'dart'
      } else if (src.indexOf('kotlin lang') > -1) {
        lang = 'kotlin'
      } else if (src.indexOf('swift lang') > -1) {
        lang = 'swift'
      } else if (src.indexOf('java lang') > -1) {
        lang = 'java'
      } else if (src.indexOf('python lang') > -1) {
        lang = 'python'
      } else if (src.indexOf('php lang') > -1) {
        lang = 'php'
      } else if (src.indexOf('javascript lang') > -1) {
        lang = 'javascript'
      } else if (src.indexOf('typescript lang') > -1) {
        lang = 'typescript'
      } else if (src.indexOf('objective-c lang') > -1) {
        lang = 'objective-c'
      } else if (src.indexOf('objc lang') > -1) {
        lang = 'objective-c'
      } else if (src.indexOf('c lang') > -1) {
        lang = 'c'
      } else if (src.indexOf('c++ lang') > -1) {
        lang = 'c++'
      } else if (src.indexOf('go lang') > -1) {
        lang = 'go'
      } else if (src.indexOf('rust lang') > -1) {
        lang = 'rust'
      }

      // axios not work for stream in browser
      const provider = getSelectedProvider();
      const clientId = getClientId();
      dispatchLlmStatus(true);
      const response = await fetch(apiUrl('/rest/code_v1'), {
        method: "POST",
        // headers: {
        //   "Content-Type": "application/json", 'Authorization': `Bearer ${localStorage.getItem('token')}`
        // },
        headers: getHeader(user.id, apiServerToken),
        body: JSON.stringify({
          lang,
          meta: props.meta,
          snippet: true,
          extraInfo: extraInfoRef.current?.value,
          message,
          provider,
          client_id: clientId,
        })
      });
      const reader = response.body!.getReader();

      let currentBlockIndex = 0
      let currentBlockType = 'markdown'
      let currentBlockLang = ''
      let currentBlockData = ''
      const _currentBlock = <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>;

      setOutputElements((_) => ([_currentBlock]))

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        if (!dataReceived) {
          setOutput('')
          setOutputElements([])
          setChatDone(false)
          dataReceived = true
        }

        let data = new TextDecoder("utf-8").decode(value!);
        if (data == "[-DONE-]") {

        } else if (data == "[-ERROR-]") {
          setOutput("Error-1!")
        } else if (data == "[-LIMIT-]") {
          setOutput("Daily limit is reached!")
        } else {
          chatResponse += data

          while (true) { // start processing chat response
            if (currentBlockType == 'markdown') {
              let codeBlockStart = chatResponse.indexOfRegex(/```[a-z\+\-]*\n/)
              if (chatResponse.length > 15 && codeBlockStart[0] == -1) {

                currentBlockData += chatResponse.substring(0, chatResponse.length - 15)
                chatResponse = chatResponse.substring(chatResponse.length - 15)

                const _currentBlockIndex = currentBlockIndex
                const _currentBlock = <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>;
                setOutputElements((prevElements) => {
                  prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
                  let newElements = [...prevElements, _currentBlock]
                  return newElements
                })

                break

              } else if (codeBlockStart[0] >= 0) {
                if (codeBlockStart[0] > 0) { // write out all markdown before code block
                  currentBlockData += chatResponse.substring(0, codeBlockStart[0])

                  const _currentBlockIndex = currentBlockIndex
                  const _currentBlock = <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>;
                  setOutputElements((prevElements) => {
                    prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
                    let newElements = [...prevElements, _currentBlock]
                    return newElements
                  })
                }

                currentBlockIndex++
                currentBlockData = ''
                currentBlockLang = codeBlockStart[1].trim().replace('```', '')
                //const _currentBlock = <CodeMirrorBlock key={currentBlockIndex} codes={currentBlockData} lang={currentBlockLang} meta="{}"></CodeMirrorBlock>
                currentBlockType = 'code'
                //setOutputElements((prevElements) => ([...prevElements, _currentBlock]))
                setSourceCode(currentBlockData)

                chatResponse = chatResponse.substring(codeBlockStart[0] + codeBlockStart[1].length)

                continue

              } else {
                break
              }
            } else {
              let codeBlockEnd = chatResponse.indexOfRegex(/```/)
              if (chatResponse.length >= 3 && codeBlockEnd[0] == -1) {
                currentBlockData += chatResponse.substring(0, chatResponse.length - 3)
                chatResponse = chatResponse.substring(chatResponse.length - 3)

                const _currentBlockIndex = currentBlockIndex
                //const _currentBlock = <CodeMirrorBlock key={currentBlockIndex} codes={currentBlockData} lang={currentBlockLang} meta="{}"></CodeMirrorBlock>
                //setOutputElements((prevElements) => {
                //  prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
                //  let newElements = [...prevElements, _currentBlock]
                //  return newElements
                //})
                setSourceCode(currentBlockData)

                break
              } else if (codeBlockEnd[0] >= 0) {

                if (codeBlockEnd[0] > 0) { // write out all code before markdown block
                  currentBlockData += chatResponse.substring(0, codeBlockEnd[0])

                  const _currentBlockIndex = currentBlockIndex
                  //const _currentBlock = <CodeMirrorBlock key={currentBlockIndex} codes={currentBlockData} lang={currentBlockLang} meta="{}"></CodeMirrorBlock>
                  //setOutputElements((prevElements) => {
                  //  prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
                  //  let newElements = [...prevElements, _currentBlock]
                  //  return newElements
                  //})
                  setSourceCode(currentBlockData)
                }

                if (currentBlockData.includes('package:flutter/')) {

                  /*const _currentBlockIndex = currentBlockIndex
                  const _currentBlock = <CodeMirrorBlock key={currentBlockIndex} codes={currentBlockData} lang={'flutter'} meta="{}"></CodeMirrorBlock>
                  setOutputElements((prevElements) => {
                    prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
                    let newElements = [...prevElements, _currentBlock]
                    return newElements
                  })*/

                }

                currentBlockIndex++
                currentBlockData = ''
                const _currentBlock = <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>;
                currentBlockType = 'markdown'
                setOutputElements((prevElements) => ([...prevElements, _currentBlock]))

                chatResponse = chatResponse.substring(codeBlockEnd[0] + codeBlockEnd[1].length)
                continue
              } else {
                break
              }
            }
          } // end process data

        }

      }

      if (chatResponse.length > 0) {
        if (currentBlockType == 'markdown') {
          currentBlockData += chatResponse
          const _currentBlockIndex = currentBlockIndex
          const _currentBlock = <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>;
          setOutputElements((prevElements) => {
            prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
            let newElements = [...prevElements, _currentBlock]
            return newElements
          })
        } else {
          currentBlockData += chatResponse
          const _currentBlockIndex = currentBlockIndex
          //if(currentBlockData.includes('package:flutter/')) {
          //  currentBlockLang = 'flutter'
          //}
          //const _currentBlock = <CodeMirrorBlock key={currentBlockIndex} codes={currentBlockData} lang={currentBlockLang} meta="{}"></CodeMirrorBlock>
          //setOutputElements((prevElements) => {
          //  prevElements = prevElements.filter((e: any) => e.key != _currentBlockIndex)
          //  let newElements = [...prevElements, _currentBlock]
          //  return newElements
          //})
          setSourceCode(currentBlockData)
        }
      }

      if (isComplete) {
        dispatchLlmStatus(false);
        spinnerRef.current?.classList.add('hidden')
      } else {
        fixSpinnerRef.current?.classList.add('hidden')
      }

      setChatDone(true)

      //editorRef.current?.scrollIntoView()
      //window.scrollTo(curXOffset, curYOffset)

    } catch (e) {
      if(isComplete)
        spinnerRef.current?.classList.add('hidden')
      else
        fixSpinnerRef.current?.classList.add('hidden')
        
      dispatchLlmStatus(false);
      console.log(e)
    }

  }

  return (
    <div className="code-snippet mb-6 relative">
      <div className="copy-code-wrap" onClick={async () => {
          //try {
          //  await navigator.clipboard.writeText(viewRef?.current!.state.doc.toString());
          //} catch (e) { // for vs code
            const textElement = document.createElement('textarea');
            textElement.value = viewRef?.current!.state.doc.toString();
            document.body.append(textElement);
            textElement.select();
            document.execCommand('copy');
            textElement.remove();
          //}
      }} style={{ position: 'absolute', cursor: 'pointer', width: 24, height: 24, top: 5, right: 5, color: "white", zIndex: 9 }}>
        <img className="copy-code" src="/img/copy.png" />
      </div>
      <div className="border-2" ref={editorRef} style={{minHeight: meta.minHeight??'90px', maxHeight: meta.maxHeight??'50vh', overflow: 'auto'}}></div>
      <textarea ref={extraInfoRef} className="hidden" style={{boxSizing: 'border-box', width: 'calc(100% - 4px)', margin: '4px 2px'}} placeholder="You have the option to submit additional documentation or sample code that can assist AI in completing your code or fixing any errors more effectively. Please provide them here."></textarea>
      {supported ?
        <div className="flex justify-end items-center px-1 mt-2 mb-2  gap-2">
          <PaperClipIcon title="Add Extra Information" className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none mx-2" onClick={() => {
            extraInfoRef.current?.classList.toggle('hidden')
          }}></PaperClipIcon>
           <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" onClick={() => {
            props.cancelCallback()
          }}>Cancel</button>

          {props.codes.includes('TODO:') ||
          <button className="w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4" onClick={()=>handleRun(true)}>
            <span>Complete it</span><div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
          </button>
          }

          <button className="w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4" onClick={()=>handleRun(false)}>
            <span>Fix it</span><div ref={fixSpinnerRef} className="loader hidden w-5 h-5"></div>
          </button>

          <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" onClick={() => {
   
            if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
              return
            }
        
            if (fixSpinnerRef.current && !fixSpinnerRef.current.classList.contains('hidden')) {
              return
            }
            props.saveCallback(viewRef?.current.state.doc.toString())
          }}>Save</button>

        </div>
        : null}
      {
        output ?
          meta.api ?
            (meta.api == 'chat' || meta.api == 'code') ?
              <Log>{t('output')}:{chatDone ? <div style={{ backgroundColor: 'white', border: `1px solid #cccccc55`, padding: 10 }}><MarkdownRenderer markdown={output} lang={meta.topic} meta={`{"from":"chat"}`}></MarkdownRenderer></div> : <Pre>{output}</Pre>}</Log>
              :
              <Log>{t('output')}:<Pre>{output}</Pre></Log>
            :
            <Log>{t('output')}:<Pre>{output}</Pre></Log>
          :
          ""
      }
      {outputElements}
      <style jsx>{`

        .copy-code {
          width: 24px;
          height: 24px;
          margin: 0px !important;
        }

        .copy-code-wrap:active .copy-code {
          transform: translate(0, 0) scale(0.9);
        }
        .animate {
          transform: translate(0, 0) scale(1.12);
        }

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
  
        
        `}</style>
    </div>
  );
}

export default memo(CodeSnippet);
