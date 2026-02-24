import React, { useEffect, useRef, useState, memo } from "react";
import {basicSetup} from "codemirror"
import { EditorState } from "@codemirror/state"
import { EditorView, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, keymap, dropCursor, rectangularSelection, crosshairCursor, ViewUpdate } from "@codemirror/view"
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
import axios from "axios";
import logger from '../../libs/logger';
import { Gallery } from "react-grid-gallery";
import MarkdownRenderer from './MarkdownRenderer';
import { draculaHighlightStyle } from '@ddietr/codemirror-themes/dracula'
import { tags } from '@lezer/highlight';
import { useTranslation } from 'next-i18next'
import RJSON from 'relaxed-json'

import ChatBlock from "./chat.block";
import { useSelector } from "react-redux";
import { ReduxStoreState } from "../../types/store";
import {  getHeader } from "../../libs/auth-header";
import { apiUrl } from "../../libs/api-base";
import { dispatchLlmStatus, getClientId, getSelectedProvider } from "../../libs/llm";
import { Throttle } from "../../libs/utils";
import { OnlineCourseEventCallback } from "../../types/online-course";

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

interface Props extends OnlineCourseEventCallback {
  lang: string;
  meta: string;
  codes: string;
  readOnly?: boolean;
  noActions?: boolean;
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

const IMAGES = [
  {
    src: process.env.NEXT_PUBLIC_URL + "/img/ai-no-sel-1.png",
    width: 512,
    height: 512,
    seed: null
  },
  {
    src: process.env.NEXT_PUBLIC_URL + "/img/ai-no-sel-2.png",
    width: 512,
    height: 512,
    seed: null
  },
  {
    src: process.env.NEXT_PUBLIC_URL + "/img/ai-no-sel-3.png",
    width: 512,
    height: 512,
    seed: null
  },
  {
    src: process.env.NEXT_PUBLIC_URL + "/img/ai-no-sel-4.png",
    width: 512,
    height: 512,
    seed: null
  }
];

const CodeMirrorBlock = (props: Props) => {
  const user = useSelector((state:ReduxStoreState) => state.user.user);
  const apiServerToken = useSelector((state:ReduxStoreState) => state.apiServerToken.apiServerToken);
  const editorRef = useRef<HTMLDivElement | null>(null);
  const spinnerRef = useRef<HTMLImageElement | null>(null);

  const padRef = useRef<HTMLDivElement | null>(null);

  const [editView, setEditView] = useState<EditorView | null>(null);
  const [output, setOutput] = useState("");
  const [imageError, setImageError] = useState("");
  const [hasQuestion, setHasQuestion] = useState(false);
  const [chatDone, setChatDone] = useState(true);

  const padCreatedRef = useRef<boolean>(false);

  const [images, setImages] = useState<any>(IMAGES);

  const { t } = useTranslation('common')

  let meta: any = {}
  try {
    meta = RJSON.parse(props.meta ?? "{}")
  } catch (e: any) {
    logger.error(e.message)
  }

  if (!meta.api) meta.api = null

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
      if (v.docChanged){
        if (props.onDocChanged){
          customThrottle.onHandle(() => {
            props.onDocChanged?.call(null,v.state.doc.toString())
          },350);
        }
      }
    })
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

  if (props.noActions) supported = false

  if (meta.api == 'code') supported = true

  extensions.push(theme)

  if (props.readOnly || meta.readOnly) {
    extensions.push(EditorView.editable.of(false))
  }

  const state = EditorState.create({
    doc: props.codes,
    extensions
  });


  const viewRef = useRef<any | null>(null);

  useEffect(() => {

    //if (props.lang == 'flutter' || props.lang == 'react') {
    if(0) {

      if (padRef.current == null) return

      if (padCreatedRef.current) return

      padCreatedRef.current = true

      let script: any = document.getElementById("dartpadLoader");

      let isVSCode = 0;
      if(location.href.indexOf('embedded-vscode-extension') > 0 && location.href.indexOf('version=') > 0) {
        isVSCode = 1;
      }

      padRef.current.innerHTML = `<pre>
      <code class="language-run-dartpad:theme-dark:mode-flutter:null_safety-true:split-60:width-100%:height-620px:id-iframe_0:vscode-${isVSCode}">
      <!--#!#${props.codes}#!#-->
      </code>
      </pre>`

      // When run, the app will look like this:\n\n![Flutter Example Screenshot](https://i.imgur.com/0RbTzvM.png)

      if (script && script.parentNode) script.parentNode.removeChild(script);

      script = document.createElement("script");
      script.src = "/code-pad/inject_embed.dart.js";
      script.id = "dartpadLoader";
      script.async = true;
      document.body.appendChild(script);

      return () => {
      }
    }

    if (editorRef.current == null) {
      return;
    }

    if (meta.api == 'image') setOutput('images')

    viewRef.current = new EditorView({ state, parent: editorRef.current });

    setEditView(viewRef.current);
    return () => {
      viewRef?.current.destroy();
      // editorRef.current.removeEventListener("input", log);
    };
  }, [props.lang]);

  useEffect(() => {

    if(editView == null) return

    let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: props.codes } })
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })

  }, [props.codes])

  const handleRun = async () => {

    if (viewRef?.current.state.doc.toString().trim().length < 2) return

    if (props.lang == 'json') {
      try {
        let data = JSON.parse(viewRef?.current.state.doc.toString())
      } catch (e: any) {
        setOutput(JSON.stringify(e.message))
        if (meta.api == 'image') setImageError(JSON.stringify(e.message))
        return
      }
    }

    if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
      return
    }
    spinnerRef.current?.classList.remove('hidden')
    /*if (props.lang == 'kotlin') {
      kotlinTimer = setTimeout(function () {
        setOutput("For technical reason, compiling kotlin can take up to 30s, please wait ..., but we will improve this soon.")
      }, 3000);
    }*/
    setImageError("")
    if (!meta.api) setOutput("")
    try {
      let res

      if (meta.api == 'chat' || meta.api == 'code') {

        let curXOffset = window.pageXOffset
        let curYOffset = window.pageYOffset

        let dataReceived = false
        let chatResponse = "";

        let lang = props.lang
        let message = viewRef?.current.state.doc.toString()

        if (meta.api == 'code') {
          lang = ''
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
          } else if (msg.indexOf('rust lang') > -1) {
            lang = 'rust'
          } else if (msg.indexOf('go lang') > -1) {
            lang = 'go'
          }

          if (lang == '') { 
            setOutput("Please specify the language in your code's comment, e.g. 'java', 'kotlin', 'dart', 'swift', 'rust', 'python', 'php', 'javascript', 'typescript")
            spinnerRef.current?.classList.add('hidden')
            return
          }
        }

        // axios not work for stream in browser
        const provider = getSelectedProvider();
        const clientId = getClientId();
        dispatchLlmStatus(true);
        const response = await fetch(apiUrl('/rest/' + meta.api + (meta.api == 'code'?'_v1':'')), {
          method: "POST",
          // headers: {
          //   "Content-Type": "application/json", 'Authorization': `Bearer ${localStorage.getItem('token')}`
          // },
          headers: getHeader(user.id, apiServerToken),
          body: JSON.stringify({
            lang,
            meta: props.meta,
            message,
            taskId: props.taskId,
            onlineCourseSessionId: props.onlineCourseSessionId,
            provider,
            client_id: clientId,
          })
        });
        props.onSubmit?.call(null);
        const reader = response.body!.getReader();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          if (!dataReceived) {
            setOutput('')
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
            setOutput(chatResponse)
          }

        }

        dispatchLlmStatus(false);
        spinnerRef.current?.classList.add('hidden')

        if (meta.api == 'code') {
          if(chatResponse.indexOf('```') == -1) { 
            setOutput(
`\`\`\`${lang}
${chatResponse}
\`\`\``              )
          }
        }

        setChatDone(true)

        //editorRef.current?.scrollIntoView()
        window.scrollTo(curXOffset, curYOffset)

        return
      } else if (props.lang != 'kotlin') {
        res = await axios({
          method: 'POST',
          url: apiUrl('/api/execute_code'),
          // headers: {
          //   "Content-Type": "application/json", 'Authorization': `Bearer ${localStorage.getItem('token')}`
          // },
          headers: getHeader(user.id, apiServerToken),
          data: {
            lang: props.lang,
            meta: props.meta,
            source: viewRef?.current.state.doc.toString(),
            taskId: props.taskId,
            onlineCourseSessionId: props.onlineCourseSessionId,
          }
        })
        props.onSubmit?.call(null);
      } else {
        let sourceCode = viewRef?.current.state.doc.toString();
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
        props.onSubmit?.call(null);

        if (res.data.text.length > 0) {
          res = { data: { data: { execute_code: { result: res.data.text.replace('<outStream>', '').replace('</outStream>', '') } } } }
        } else if (res.data.errors && res.data.errors['File.kt'] && res.data.errors['File.kt'][0].message && res.data.errors['File.kt'][0].message.length > 0) {
          res = { data: { data: { execute_code: { result: res.data.errors['File.kt'][0].message } } } }
        } else {
          res = { data: { data: { execute_code: { result: "Error-4!" } } } }
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
        props.onError?.call(null);
      } else {
        if (meta.api != 'image') {
          setOutput(data.data.execute_code.result)
        } else {
          try {
            let imgList = JSON.parse(data.data.execute_code.result)
            setImages(imgList.map((img: any) => {
              return {
                src: img.image,
                width: 512,
                height: 512,
                isSelected: false,
                seed: img.seed
              }
            }))
            setOutput('images')
          } catch (e) {
            logger.error(e)
          }
        }
      }
    } catch (e) {
      if (kotlinTimer != null) {
        clearTimeout(kotlinTimer)
        kotlinTimer = null
      }
      console.log(e)
      setOutput("Error-3!")
      dispatchLlmStatus(false);
      props.onError?.call(null);
    }
    spinnerRef.current?.classList.add('hidden')
  }

  const handleReset = () => {
    // reset the user-modified code
    // editView?.state.doc = props.codes;

    if (spinnerRef.current && !spinnerRef.current.classList.contains('hidden')) {
      return
    }

    let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: meta.api == 'chat' && !meta.reset ? "\n\n\n" : props.codes } })
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })

    if (!meta.api) setOutput("")
    setImageError("")
    props.onReset?.call(null);
  };

  //if (props.lang == 'flutter' || props.lang == 'react') {
  if(0) {
    return (
      <div className="dart-pad-panel" ref={padRef} />
    )
  }

  return (<>
    {(meta.caption || meta.detail)&&
    <div>
      {meta.caption && <h4>{meta.caption}</h4>}
      {meta.detail && <h5 className="whitespace-pre">{meta.detail}</h5>}
    </div>}
    <div className="code-mirror-block mb-6 relative">
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
      <div className="border-2" ref={editorRef}></div>
      {supported ?
        <div className="flex justify-end items-center px-1 mt-2 mb-2  gap-2">
          <button className="w-auto rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4" onClick={handleRun}>
            <span>{(meta.api == 'chat' || meta.api == 'code') ? t('ask-now') : t('try-it')}</span><div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
          </button>
          {
            (props.readOnly || meta.readOnly) ?
              null
              :
              <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" style={{color: 'black'}} onClick={handleReset}>{meta.api == 'chat' && !meta.reset ? t('clear') : t('reset')}</button>
          }
          {meta.from == "chat" ?
            <button className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50" onClick={() => setHasQuestion(true)}>{t('ask')} ?
            </button>
            : null}
        </div>
        : null}
      {
        output ?
          meta.api ?
            (meta.api == 'chat' || meta.api == 'code') ?
              <Log>{t('output')}:{chatDone ? <div style={{ backgroundColor: 'white', border: `1px solid #cccccc55`, padding: 10 }}><MarkdownRenderer markdown={output} lang={meta.topic} meta={`{"from":"chat"}`}></MarkdownRenderer></div> : <Pre>{output}</Pre>}</Log>
              :
              meta.api == 'image' ?
                <Log>{t('output')}:<div style={{ backgroundColor: 'white', border: `1px solid #cccccc55`, padding: 10 }}>
                  <div style={{ color: 'red' }}>{imageError}</div>
                  <Gallery rowHeight={220} images={images} onSelect={
                    (index: number, item: any, event: any) => {
                      //if (images[index].seed === null) return

                      const nextImages: any = images.map((image: any, i: number) =>
                        i === index ? { ...image, isSelected: !image.isSelected } : { ...image, isSelected: false }
                      );

                      setImages(nextImages);

                      try {
                        let newData = JSON.parse(viewRef?.current.state.doc.toString())
                        newData.input.init_image = images[index].src
                        newData.input.seed = images[index].seed
                        const newSting = JSON.stringify(newData, null, 2)

                        let transaction = editView?.state.update({ changes: { from: 0, to: editView?.state.doc.length, insert: newSting } })
                        editView?.dispatch(transaction ? transaction : { changes: { from: 0, insert: "0" } })
                      } catch (e) {
                        logger.error(e)
                      }

                    }} /></div></Log>
                :
                <Log>{t('output')}:<Pre>{output}</Pre></Log>
            :
            <Log>{t('output')}:<Pre>{output}</Pre></Log>
          :
          ""
      }
      {meta.from == "chat" && hasQuestion ? <><div><b>{t('question')}:</b> </div><div className="w-full">
        <ChatBlock codes={`${
          new RegExp(/(\/\/|#)\s*(todo|update|edit|fix|please|pls)/i).test(props.codes) ? 
          "Please complete the code below according to the requirements specified in the comments: \n\n" + props.codes
          :
          "Can you explain the code below? As I can not understand it: \n\n" + props.codes}`} lang="markdown" meta={'{api:chat}'} />
        </div></> : null}
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
    </div></>
  );
}

export default memo(CodeMirrorBlock);
