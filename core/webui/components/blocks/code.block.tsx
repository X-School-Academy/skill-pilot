import React, { useEffect, useRef, useState, memo } from "react";
import {basicSetup} from "codemirror"
import { EditorState } from "@codemirror/state"
import { EditorView, ViewUpdate, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, keymap, dropCursor, rectangularSelection, crosshairCursor } from "@codemirror/view"
import { history, indentWithTab } from "@codemirror/commands"
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
import axios from "axios";
import logger from '../../libs/logger';
//import Markdown from 'react-markdown'
import MarkdownRenderer, { Markdown } from './MarkdownRenderer';
import { draculaHighlightStyle } from '@ddietr/codemirror-themes/dracula'
import { tags } from '@lezer/highlight';
import { useTranslation } from 'next-i18next'
import RJSON from 'relaxed-json'
import sleep from "sleep-promise";
import ChatBlock from "./chat.block";
import { HandRaisedIcon, PencilIcon, PencilSquareIcon, ArrowsPointingInIcon, ArrowsPointingOutIcon, PaperClipIcon } from '@heroicons/react/24/solid'
import ModalDialog from "../ModalDialog";
import CodeSnippet from "./code.snippet";
import { getApiServerAuthHeader, getHeader, getJsonAuthHeader } from "../../libs/auth-header";
import { useSelector } from "react-redux";
import { ReduxStoreState } from "../../types/store";
import { Throttle } from "../../libs/utils";
import { OnlineCourseEventCallback } from "../../types/online-course";
import { apiUrl } from "../../libs/api-base";
import { dispatchLlmStatus, getClientId, getSelectedProvider } from "../../libs/llm";

const TEST_CASE_PATTERN = '\\```';

const TextArea = (props: any) => {
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (ref && ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = ref.current.scrollHeight + 'px'
    }
  }, [props.value])

  return <>
  <textarea ref={ref} readOnly={props.readOnly} value={props.value} onSelect={props.onSelect}></textarea>
  <style jsx>{`
    textarea {
      border: none;
      outline: none;
      width: 100%;
      height: 100px;
      line-height: 1.5;
      background-color: transparent;
      color: ${props.error? 'red' : 'black'};
      box-shadow: none;
    }

    textarea:focus {
      outline: none;
    }
  `}</style>
  </>
}


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
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': { backgroundColor: config.selection + ' !important' },
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

interface Props extends OnlineCourseEventCallback {
  lang: string;
  meta: string;
  codes: string;
  reload?: boolean;
  readOnly?: boolean;
  noActions?: boolean;
  index?: number;
  showRun?: boolean;
  token?: string;
  callback?: (index: number, result: any) => void;
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

declare global {
  interface String {
    indexOfRegex(regex: RegExp): any[];
  }
}

String.prototype.indexOfRegex = function (regex: RegExp): any[] {
  const match = this.match(regex);
  return [match ? this.indexOf(match[0]) : -1, match ? match[0] : null];
};

const CodeBlock = (props: Props) => {
  const [testCaseCode, setTestCaseCode] = useState<string>();
  const user = useSelector((state: ReduxStoreState) => state.user.user);
  const apiServerToken = useSelector((state: ReduxStoreState) => state.apiServerToken.apiServerToken);

  const thisRef = useRef<HTMLDivElement | null>(null);
  const maskRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<HTMLDivElement | null>(null);
  const spinnerRef = useRef<HTMLImageElement | null>(null);
  const execSpinnerRef = useRef<HTMLImageElement | null>(null);

  const extraInfoRef = useRef<HTMLTextAreaElement | null>(null);

  const padRef = useRef<HTMLDivElement | null>(null);
  const padCreatedRef = useRef<boolean>(false);

  const hasSelectedContentRef = useRef<boolean>(false);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);

  const [editView, setEditView] = useState<EditorView | null>(null);
  const [output, setOutput] = useState("");
  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState(false);
  const [sourceCode, setSourceCode] = useState(props.codes);
  const [sourceLang, setSourceLang] = useState(props.lang);
  const [showRun, setShowRun] = useState(props.showRun??false);

  const [hasQuestion, setHasQuestion] = useState(false);
  const [chatDone, setChatDone] = useState(true);
  const [showAssistant, setShowAssistant] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);

  const [outputElements, setOutputElements] = useState<any[]>([]);

  const [assistantCode, setAssistantCode] = useState<string>('');
  const [assistantComments, setAssistantComments] = useState<boolean>(false);
  const [assistantText, setAssistantText] = useState<string>('');

  const callbackRef = useRef(false);
  const isReadyRef = useRef(false);

  const { t } = useTranslation('common')

  let meta: any = {}
  try {
    meta = RJSON.parse(props.meta ?? "{}")
  } catch (e: any) {
    logger.error(e.message)
  }

  if (!meta.api) meta.api = 'code'

  let kotlinTimer: any = null;

  let supported = true

  const customThrottle = new Throttle();

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
    EditorView.updateListener.of((v: ViewUpdate) => {
      let doc = v.state.doc
      //let fromLine = doc.lineAt(v.state.selection.main.from)
      //let toLine = doc.lineAt(v.state.selection.main.to)

      if (v.docChanged){
        if (props.onDocChanged){
          customThrottle.onHandle(() => {
            props.onDocChanged?.call(null,doc.toString())
          },350);
        }
      }

      if (v.state.selection.main.to - v.state.selection.main.from > 0) {
        if (hasSelectedContentRef.current === false) {
          hasSelectedContentRef.current = true
          setShowAssistant(() => true)
        }
      } else {
        if (hasSelectedContentRef.current === true) {
          hasSelectedContentRef.current = false
          setShowAssistant(() => false)
        }
      }
    })
  ];

  switch (sourceLang) {
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
      supported = false
      break
    case 'php':
      extensions.push(lineNumbers())
      extensions.push(php({ plain: meta.rawCode !== true }))
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
      supported = false
      break
    case 'c':
    case 'cpp':
    case 'c++':
    case 'objc':
    case 'objective-c':
    case 'go':
    case 'dart':

    case 'flutter':
    case 'react':
    case 'html':
    case 'tsx':
    case 'rn':
    case 'any':
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      break
    case 'rs':
    case 'rust':
      extensions.push(lineNumbers())
      extensions.push(rust())
      break;
    default:
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      supported = false
  }

  extensions.push(theme)

  if (props.noActions || meta.action == 'none') supported = false

  if(!meta.action) meta.action = 'run'

  if (props.readOnly || meta.readOnly) {
    extensions.push(EditorView.editable.of(false))
  }

  const state = EditorState.create({
    doc: sourceCode,
    extensions
  });


  const viewRef = useRef<EditorView | null>(null);
  let padFrameID = useRef<Number>(0);

  useEffect(() => {
    if ((meta.optional || !supported || meta.codeOnly) && props.callback && props.index) {
      if (callbackRef.current) return
      callbackRef.current = true
      props.callback(props.index, 1)
    }
  }, [])

  useEffect(() => {
    //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
    if(0) {

      if (padRef.current == null) return

      const onMessage = (event: any) => {
        const data = event.data;

        if (data.sender && data.sender == 'frame' && data.frameId == `iframe_${padFrameID.current}`) {
          if (data.type == 'fetch' && data.code) {
            handleRun(data.code)
          } else if (data.type == 'edit') {
            if (data.output) {// from output log
              setAssistantCode(`/* TODO:
Please check the code below, as I have got an error when running it: 
${data.output}
*/

${data.code}`)
            } else {
              setAssistantCode(data.code)
            }
            setIsAssistantOpen(true)
          } else if (data.type == 'assistant') {
            if (data.output) { // from output log
              setAssistantText(data.output)
            }
            setAssistantCode(data.code)
            //setShowAssistant(true)  
            setAssistantComments(false)
            setHasQuestion(!hasQuestion)
          } else if(data.type == 'ready') {
            if(!isReadyRef.current)setTimeout(() => {
              isReadyRef.current = true
            }, 1000)

            // fix one code loading issue
            setTimeout(() => {
              const message = {
                'sourceCode': {
                  'main.dart': sourceCode,
                  'test.dart': '',
                  'scroll': 'true'
                },
                'autoRun': false,
                'type': 'sourceCode',
                'analyze': false,
              };
        
              padRef.current!.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
            }, 150);
          }
        } else {
          //console.log('message', data, padFrameID.current)
        }
      }

      window.addEventListener('message', onMessage);

      let timer0 = setTimeout(() => {
        const message = {
          'type': 'mode',
          'lang': sourceLang,
        };

        padRef.current?.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
      }, 200)


      let timer = setTimeout(() => {
        const message = {
          'type': 'mode',
          'lang': sourceLang,
        };

        padRef.current?.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
      }, 3000)


      if (padCreatedRef.current && props.reload !== true) return
      //if (padCreatedRef.current) return

      padCreatedRef.current = true

      if(isReadyRef.current && props.reload == true) {

        //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
        if(0) {

          if (padRef.current == null) return
    
          const message = {
            'sourceCode': {
              'main.dart': sourceCode,
              'test.dart': '',
              'scroll': 'true'
            },
            'autoRun': false,
            'type': 'sourceCode',
            'analyze': false,
          };
    
          padRef.current.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
        }

        return
      }

      let script: any = document.getElementById("dartpadLoader");

      padFrameID.current = Math.floor(Math.random() * 10000 + 1);

      let isVSCode = 0;
      if(location.href.indexOf('embedded-vscode-extension') > 0 && location.href.indexOf('version=') > 0) {
        isVSCode = 1;
      }

      // <!--#!# fix jsx issue #!#-->
      padRef.current.innerHTML = `<pre>
      <code class="language-run-dartpad:theme-dark:mode-flutter:null_safety-true:split-60:width-100%:height-620px:id-iframe_${padFrameID.current}:vscode-${isVSCode}">
      <!--#!#${props.codes}#!#-->
      </code>
      </pre>`

      //console.log(props.codes)
      // When run, the app will look like this:\n\n![Flutter Example Screenshot](https://i.imgur.com/0RbTzvM.png)

      if (script && script.parentNode) script.parentNode.removeChild(script);

      script = document.createElement("script");
      script.src = "/code-pad/inject_embed.dart.js";
      script.id = "dartpadLoader";
      script.async = true;
      document.body.appendChild(script);

      return () => {
        clearTimeout(timer0)
        clearTimeout(timer)
        window.removeEventListener('message', onMessage);
        viewRef?.current?.destroy();
      }
    }

    if (editorRef == null || editorRef.current == null) {
      return;
    }

    viewRef.current = new EditorView({ 
      state, 
      parent: editorRef.current,
      
    });

    if(meta.minHeight) {
      (editorRef.current.querySelector('.cm-editor') as HTMLElement).style.minHeight = meta.minHeight
    }

    setEditView(viewRef.current);
    return () => {
      viewRef?.current?.destroy();
      // editorRef.current.removeEventListener("input", log);
    };
  //}, [sourceLang]);
  }, [sourceLang, props.reload]);

  useEffect(() => {

    //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
    if(0) {

      if (padRef.current == null) return

      const message = {
        'sourceCode': {
          'main.dart': sourceCode,
          'test.dart': '',
          'scroll': 'true'
        },
        'autoRun': false,
        'type': 'sourceCode',
        'analyze': false,
      };

      padRef.current.querySelector('iframe')?.contentWindow?.postMessage(message, '*')

      return
    }

    if (editView == null) return

    let transaction = editView?.state.update({ changes: { 
        from: 0, 
        to: editView?.state.doc.length, insert: sourceCode }, 
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
    setSourceLang(props.lang)
  }, [props.lang])

  useEffect(() => {
    const code = findTestCodeAndReplace();
    setSourceCode(code)
  }, [props.codes])

  useEffect(() => {
    if (meta.action === 'run' && !meta.codeOnly) {
      setShowRun(true)
    }
  }, [meta])

  const handleRun = async (event: any) => {

    let source = undefined

    if (event.preventDefault) {
      event.preventDefault()
    } else {
      source = event
    }

    if (source == undefined) {
      //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
      if(0) {
        const message = {
          'type': 'fetch',
          'action': 'complete'
        }
        padRef?.current?.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
        return
      } else {
        source = viewRef?.current!.state.doc.toString()
      }
    }

    if (source.length < 2) return

    if (sourceLang == 'json') {
      try {
        let data = JSON.parse(source)
      } catch (e: any) {
        setOutput(JSON.stringify(e.message))
        return
      }
    }

    if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
      return
    }
    spinnerRef.current?.classList.remove('hidden')
    /*if (sourceLang == 'kotlin') {
      kotlinTimer = setTimeout(function () {
        setOutput("For technical reason, compiling kotlin can take up to 30s, please wait ..., but we will improve this soon.")
      }, 3000);
    }*/

    setOutput("")
    setCodeOutput("")
    try {
      let res
      
      if (meta.api == 'code') {

        let dataReceived = false
        let chatResponse = "";

        let message = source
        //let lang = sourceLang

        let lang = (props.lang == 'flutter' || sourceLang == 'flutter') ? 'dart' : sourceLang
        if (props.lang == 'react' || sourceLang == 'react') lang = 'typescript'
        let msg = message.toLowerCase()

        if (msg.indexOf('dart lang') > -1) {
          lang = 'dart'
        } else if (msg.indexOf('kotlin lang') > -1) {
          lang = 'kotlin'
        } else if (msg.indexOf('swift lang') > -1) {
          lang = 'swift'
        } else if (msg.indexOf('java lang') > -1) {
          lang = 'java'
        } else if (msg.indexOf('python lang') > -1) {
          lang = 'python'
        } else if (msg.indexOf('php lang') > -1) {
          lang = 'php'
        } else if (msg.indexOf('javascript lang') > -1) {
          lang = 'javascript'
        } else if (msg.indexOf('typescript lang') > -1) {
          lang = 'typescript'
        } else if (msg.indexOf('objective-c lang') > -1) {
          lang = 'objective-c'
        } else if (msg.indexOf('objc lang') > -1) {
          lang = 'objective-c'
        } else if (msg.indexOf('c lang') > -1) {
          lang = 'c'
        } else if (msg.indexOf('c++ lang') > -1) {
          lang = 'c++'
        } else if (msg.indexOf('go lang') > -1) {
          lang = 'go'
        } else if (msg.indexOf('rust lang') > -1) {
          lang = 'rust'
        }

        if (!lang || lang == 'any') {
          setOutput("Please specify the language in your code's comment, e.g. 'java', 'kotlin', 'dart', 'swift', 'rust', 'python', 'php', 'javascript', 'typescript")
          spinnerRef.current?.classList.add('hidden')
          return
        }
        // append testCaseCode
        if (testCaseCode && meta.testcase && meta.testcase === true) {
          //message = message + '\n' + testCaseCode
          meta.testcase_code = testCaseCode;
        }

        if (meta.detail && meta.aiCheck && meta.aiCheck === true) {
          meta.aiCheck_detail = meta.detail;
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
          headers: getJsonAuthHeader(getApiServerAuthHeader(user.id,apiServerToken)),
          body: JSON.stringify({
            lang,
            snippet: false,
            extraInfo: extraInfoRef.current?.value,
            meta: JSON.stringify(meta),
            message,
            taskId: props.taskId,
            onlineCourseSessionId: props.onlineCourseSessionId,
            provider,
            client_id: clientId,
          })
        });

        props.onSubmit?.call(null);

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
                  setSourceLang(currentBlockLang)

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

                  if (currentBlockData.includes('package:flutter/') && currentBlockLang != 'flutter') {
                    currentBlockLang = 'flutter'
                    setSourceLang(currentBlockLang)
                  }else if (currentBlockData.match(/from\s+('|")react('|")/) && currentBlockLang != 'react') {
                    currentBlockLang = 'react'
                    setSourceLang(currentBlockLang)
                  }

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

        dispatchLlmStatus(false);
        spinnerRef.current?.classList.add('hidden')

        setChatDone(true)

        //editorRef.current?.scrollIntoView()
        //window.scrollTo(curXOffset, curYOffset)
        setShowRun(true)

        if (props.callback) {
          if (callbackRef.current) return
          callbackRef.current = true
          props.callback(props.index ?? 0, 1)
        }
      } 
    } catch (e) {
      if (kotlinTimer != null) {
        clearTimeout(kotlinTimer)
        kotlinTimer = null
      }
      console.log(e)
      setOutput("Error-3!");
      dispatchLlmStatus(false);
      props.onError?.call(null);
    }
    spinnerRef.current?.classList.add('hidden')
  }

  const execute = async (event: any) => {

    let source = undefined

    if (event.preventDefault) {
      event.preventDefault()
    } else {
      source = event
    }

    if (source == undefined) {
      //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
      if(0) {
        const message = {
          'type': 'fetch',
          'action': 'complete'
        }
        padRef?.current?.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
        return
      } else {
        source = viewRef?.current!.state.doc.toString().trim()
      }
    }

    if (source.length < 2) return

    setOutput('')
    setCodeOutput('')

    if (sourceLang == 'json') {
      try {
        let data = JSON.parse(source)
      } catch (e: any) {
        setCodeOutput(JSON.stringify(e.message))
        setCodeError(true)
        return
      }
    }

    if (execSpinnerRef.current && !execSpinnerRef.current.classList.contains('hidden')) {
      return
    }
    execSpinnerRef.current?.classList.remove('hidden')
    /*if (sourceLang == 'kotlin') {
      kotlinTimer = setTimeout(function () {
        setOutput("For technical reason, compiling kotlin can take up to 30s, please wait ..., but we will improve this soon.")
      }, 3000);
    }*/

    try {
      let res
      // append testCaseCode
      if (testCaseCode && meta.testcase && meta.testcase === true) {
        //source = source + '\n' + testCaseCode
        meta.testcase_code = testCaseCode;
      }

      if (meta.detail && meta.aiCheck && meta.aiCheck === true) {
        meta.aiCheck_detail = meta.detail;
      }

      if (sourceLang != 'kotlin') {
        res = await axios({
          method: 'POST',
          url: apiUrl('/api/execute_code'),
          // headers: {
          //   "Content-Type": "application/json", 'Authorization': `Bearer ${localStorage.getItem('token')}`
          // },
          headers: getHeader(user.id,apiServerToken),
          data: {
            lang: sourceLang,
            meta: JSON.stringify(meta),
            source: source,
            taskId: props.taskId,
            onlineCourseSessionId: props.onlineCourseSessionId,
          }
        })
      } else {
        let sourceCode = source;
        if (!meta.rawCode && !sourceCode.match(/fun\s+main\s*\(/)) {
            sourceCode = `fun main() {
                  ${sourceCode}
            }`
        }

        res = await axios({
          method: 'POST',
          timeout: 9000,
          url: 'https://api.kotlinlang.org//api/1.8.10/compiler/run',
          data: {
            args: "",
            files: [{
              name: "File.kt",
              text: sourceCode
            }]
          }
        })
        if (res.data.text.length > 0) {
          res = { data: { data: { execute_code: {status: 1, result: res.data.text.replace('<outStream>', '').replace('</outStream>', '') } } } }
        } else if (res.data.errors && res.data.errors['File.kt'] && res.data.errors['File.kt'][0].message && res.data.errors['File.kt'][0].message.length > 0) {
          res = { data: { data: { execute_code: {status: 0, result: res.data.errors['File.kt'][0].message } } } }
        } else {
          res = { data: { data: { execute_code: {status: 0, result: "Error-4!" } } } }
        }
      }

      //if (kotlinTimer != null) {
      //  clearTimeout(kotlinTimer)
      //  kotlinTimer = null
      //}

      const data = res.data
      if (data.error) {
        logger.error(data.error.errors)
        setOutput("Error-2!")
        logger.error(data.error.errors);
        props.onError?.call(null);
      } else {
        setOutput('')
        props.onSubmit?.call(null);
        setCodeOutput(data.data.execute_code.result)
        if(data.data.execute_code.status == 1) {
          setCodeError(false)
        } else {
          setCodeError(true)
          props.onError?.call(null);
        }
      }
    } catch (e) {
      if (kotlinTimer != null) {
        clearTimeout(kotlinTimer)
        kotlinTimer = null
      }
      console.log(e)
      setOutput("Error-3!");
      props.onError?.call(null);
    }

    execSpinnerRef.current?.classList.add('hidden')

    if (props.callback) {
      if (callbackRef.current) return
      callbackRef.current = true
      props.callback(props.index ?? 0, 1)
    }

  }

  const handleReset = () => {
    // reset the user-modified code
    // editView?.state.doc = props.codes;

    if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
      return
    }

    if (execSpinnerRef.current && !execSpinnerRef.current.classList.contains('hidden')) {
      return
    }
    let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: props.codes } })
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })

    setOutput('')
    setCodeOutput('')

    props.onReset?.call(null);
  };

  const findTestCodeAndReplace = (): string => {
    // find last TEST_CASE_PATTERN 
    const endIndex =  props.codes.lastIndexOf(TEST_CASE_PATTERN);
    if (endIndex === -1) {
      return props.codes;
    }
    // find begin TEST_CASE_PATTERN 
    let startIndex = props.codes.lastIndexOf(TEST_CASE_PATTERN, endIndex - 4); 
    const code = props.codes.substring(startIndex - 1, endIndex + 4);
    setTestCaseCode(code)
    // console.log('testCaseCode:',testCaseCode);
    return props.codes.replaceAll(code,'');
  }

  return (<>
    {(meta.caption || meta.detail)&&
    <div>
      {meta.caption && <h4>{meta.caption}</h4>}
      {meta.detail && <h5 className="whitespace-pre">{meta.detail}</h5>}
    </div>}
    <div ref={thisRef} className={`code-block mb-6 relative`}>
      {(props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') ?
        <div className="dart-pad-panel" ref={padRef} />
        :
        <>
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
        <div className="border-2" ref={editorRef} style={{minHeight: meta.minHeight??'90px', maxHeight: meta.maxHeight??'50vh', overflow: 'auto'}} />
        </>
      }
      <textarea ref={extraInfoRef} className="hidden" style={{boxSizing: 'border-box', width: 'calc(100% - 4px)', margin: '4px 2px'}} placeholder="You have the option to submit additional documentation or sample code that can assist AI in completing your code or fixing any errors more effectively. Please provide them here."></textarea>
      {supported ?
        <div className="flex justify-end items-center px-1 mt-2 mb-2 gap-2">
          {
            meta.action != 'run'
            &&
            <>
              <PaperClipIcon title="Add Extra Information" className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none mx-2" onClick={() => {
                extraInfoRef.current?.classList.toggle('hidden')
              }}></PaperClipIcon>
              <button className={`w-auto rounded h-10 font-medium flex flex-row items-center gap-2 px-4 ${showRun ? 'w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50' : 'border-primary-blue text-white bg-primary-blue hover:opacity-80'}`} onClick={handleRun}>
                <span className="whitespace-nowrap">{meta.button ?
                  meta.button
                  :
                  (meta.action == 'complete') ? t('complete-for-me') : t('fix-error-for-me')
                }</span><div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
              </button>
            </>
          }
          {
            (!showRun || ['flutter', 'react', 'html', 'tsx', 'rn'].includes(sourceLang) || ['flutter', 'react', 'html', 'tsx', 'rn'].includes(props.lang)) ?
              null
              :
              <button className="w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4" onClick={execute}>
                <span>{meta.action != 'run' ? (meta.runButton ?? t('run-button')) : (meta.button ?? t('run-button'))}</span><div ref={execSpinnerRef} className="loader hidden w-5 h-5"></div>
              </button>
          }
          {
            (props.readOnly || meta.readOnly || (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react')) ?
              null
              :
              <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" style={{color: 'black'}} onClick={handleReset}>{meta.api == 'chat' && !meta.reset ? t('clear') : t('reset')}</button>
          }

          <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" onClick={() => {

            if (!isFullScreen && document.getElementsByTagName('body')[0].classList.contains('code-block-full')) return

            document.getElementsByTagName('body')[0].classList.toggle('code-block-full')

            thisRef.current?.classList.toggle('full')
            if (padRef.current && padRef.current!.querySelector('iframe')) {
              padRef.current!.querySelector('iframe')!.style.height = isFullScreen ? '620px' : '80vh'
            }
            if (isFullScreen) {
              thisRef.current?.scrollIntoView()
            } else {
              window.scrollTo(0, 0)
            }
            setIsFullScreen(!isFullScreen)
          }}>{isFullScreen ? <ArrowsPointingInIcon className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer" /> : <ArrowsPointingOutIcon className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer" />}
          </button>

          {(meta.from == "chat" || meta.handBtn || showAssistant) ?
            <HandRaisedIcon title='Ask AI Now' className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none mx-2" onClick={() => {
              let fromLine = editView?.state.doc.lineAt(editView?.state.selection.main.from)
              let toLine = editView?.state.doc.lineAt(editView?.state.selection.main.to)
              let selectedCode = editView?.state.doc.sliceString(fromLine!.from, toLine!.to)
              setAssistantCode(selectedCode ? selectedCode : '')
              setAssistantText('')
              setAssistantComments(false)

              setHasQuestion(!hasQuestion)
            }}></HandRaisedIcon>
            : null}
          {(meta.from == "chat"  || meta.commentBtn) ?
            <PencilIcon title="Ask AI to comment the code" className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none mx-2" onClick={() => {
              let fromLine = editView?.state.doc.lineAt(editView?.state.selection.main.from)
              let toLine = editView?.state.doc.lineAt(editView?.state.selection.main.to)
              let selectedCode = editView?.state.doc.sliceString(fromLine!.from, toLine!.to)
              setAssistantCode(selectedCode ? selectedCode : '')
              setAssistantText('')
              setAssistantComments(true)

              setHasQuestion(!hasQuestion)
            }}></PencilIcon>
            : null}
          {showAssistant && <PencilSquareIcon title="Ask AI to edit" className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer" onClick={() => {
            let fromLine = editView?.state.doc.lineAt(editView?.state.selection.main.from)
            let toLine = editView?.state.doc.lineAt(editView?.state.selection.main.to)
            let selectedCode = editView?.state.doc.sliceString(fromLine!.from, toLine!.to)
            setAssistantCode(selectedCode ? selectedCode : '')
            setIsAssistantOpen(true)
          }}
          />}
        </div>
        : null}
      {
        output && <Log>{t('output')}:{chatDone ? <div style={{ backgroundColor: 'white', border: `1px solid #cccccc55`, padding: 10 }}><MarkdownRenderer markdown={output} lang={meta.topic} meta={`{"from":"chat"}`}></MarkdownRenderer></div> : <Pre>{output}</Pre>}</Log>
      }
      {
        codeOutput && <Log>Output: {assistantText &&
          <>
            <PencilSquareIcon title="Ask AI to edit" className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline mx-3 select-none" onClick={() => {
              editView?.dispatch({
                selection: {
                  anchor: 0,
                  head: 0
                },
              });

              if (props.lang == 'python' && sourceLang == 'python') {
                setAssistantCode(`'''
Please check the code below, as I have got an error when running it: 
${assistantText}
'''

${viewRef?.current!.state.doc.toString().trim()}`)
              } else {
                setAssistantCode(`/* TODO:
Please check the code below, as I have got an error when running it: 
${assistantText}
*/

${viewRef?.current!.state.doc.toString().trim()}`)
              }

              setIsAssistantOpen(true)
            }}></PencilSquareIcon>
            <HandRaisedIcon title='Ask AI Now' className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none" onClick={() => {
              setAssistantCode('')
              setAssistantComments(false)
              setHasQuestion(!hasQuestion)
            }}></HandRaisedIcon>
          </>
        }
          <TextArea readOnly={true} value={codeOutput} error={codeError}  onSelect={(event:any) => {
            let text = event.currentTarget.value.substring(event.currentTarget.selectionStart, event.currentTarget.selectionEnd)
            if (text.length > 0) {
              setAssistantText(text)
            } else {
              setAssistantText('')
            }
          }} />
        </Log>
      }
      {hasQuestion ? 
      <>
          <div><b>{t('question')}:</b> </div>
          <div className="w-full">
            <ChatBlock 
              codes={(()=> {
                const code = (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') ? assistantCode : (assistantCode.length == 0?viewRef?.current!.state.doc.toString():assistantCode)

                let str
                if(assistantComments) {
                  str = 'Please add comments to the code below, as I cannot understand it.'
                } else {
                  str = `Can you ${assistantText ? 'check' : 'explain'} the code below? `
                  str += assistantText ? `As I have got: ${assistantText}.`  : 'As I cannot understand it.'

                  if(new RegExp(/(\/\/|#)\s*(todo|update|edit|fix|please|pls)/i).test(code) && !assistantText) {
                    str = 'Please complete the code below according to the requirements specified in the comments:'
                  }
                }
                str += `\n\n${code}`
                
                return str
              })()}
              lang={props.lang} 
              meta={"{type:chat, action: code, button: 'Ask AI', reset: true, audio: false}"}
            />
          </div>
      </> 
        : 
      null}
      <div>
        {outputElements}
      </div>

      <ModalDialog title="Code Assistant" toolbar={false} isOpen={isAssistantOpen} onClose={() => setIsAssistantOpen(false)}>

        <CodeSnippet codes={assistantCode} source={sourceCode} lang={
          (props.lang == 'flutter' || sourceLang == 'flutter') ?
            'dart'
            :
            (props.lang == 'react' || sourceLang == 'react') ? 'react' : sourceLang
        } meta={'{}'} cancelCallback={() => {
          setIsAssistantOpen(false)
        }} saveCallback={(code: string) => {
          //if (props.lang == 'flutter' || sourceLang == 'flutter' || props.lang == 'react' || sourceLang == 'react') {
          if(0) {
            const message = {
              'type': 'assistant',
              'action': 'complete',
              'code': code
            }
            padRef?.current?.querySelector('iframe')?.contentWindow?.postMessage(message, '*')
          } else if (editView != null) {
            let fromLine = editView?.state.doc.lineAt(editView?.state.selection.main.from)
            let toLine = editView?.state.doc.lineAt(editView?.state.selection.main.to)
            let transaction = editView?.state.update({
              changes: {
                from: fromLine.from,
                to:
                  (editView?.state.selection.main.from == 0 && editView?.state.selection.main.to == 0)
                    ?
                    editView?.state.doc.length
                    :
                    toLine.to, insert: code
              }
            })
            editView.dispatch(transaction)
          } else {
            console.log('editView is null')
          }
          setIsAssistantOpen(false)
        }} />

      </ModalDialog>
      <style jsx>{`

        .code-block {
          background-color: white;
        }

        .copy-code {
          width: 24px;
          height: 24px;
          margin: 0px !important;
        }

        .copy-code-wrap:active .copy-code {
          transform: translate(0, 0) scale(0.9);
        }

        .full {
          position: fixed;
          top: 0px;
          left: 0px;
          width: 100%;
          height: 100%;
          padding: 20px;
          z-index: 100000;
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
    </div></>
  );
}

export default memo(CodeBlock);
