import React, { useEffect, useRef, useState, useCallback, memo } from "react";
import { basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import {
  EditorView,
  lineNumbers,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
  ViewUpdate,
} from "@codemirror/view";
import { history, indentWithTab } from "@codemirror/commands";
import { python } from "@codemirror/lang-python";
import { php } from "@codemirror/lang-php";
import { json } from "@codemirror/lang-json";
import { rust } from "@codemirror/lang-rust";
import { markdown } from "@codemirror/lang-markdown";
import { java } from "@codemirror/lang-java";
import {
  bracketMatching,
  defaultHighlightStyle,
  foldGutter,
  StreamLanguage,
  indentOnInput,
  syntaxHighlighting,
  HighlightStyle,
} from "@codemirror/language";
import { autocompletion, closeBrackets } from "@codemirror/autocomplete";
import { dart, kotlin } from "@codemirror/legacy-modes/mode/clike";
import { swift } from "@codemirror/legacy-modes/mode/swift";
import { highlightSelectionMatches } from "@codemirror/search";
import styled from "styled-components";
import axios from "axios";
import logger from "../../libs/logger";
//import Markdown from "react-markdown";
import MarkdownRenderer, { Markdown } from "./MarkdownRenderer";
import CodeBlock from "./code.block";
import { useTranslation } from "next-i18next";
import RJSON from "relaxed-json";
import { MicrophoneIcon, PaperClipIcon } from "@heroicons/react/24/solid";
import { tags } from "@lezer/highlight";
import { useSelector } from "react-redux";
import { ReduxStoreState } from "../../types/store";
import { getApiServerAuthHeader, getHeader, getJsonAuthHeader } from "../../libs/auth-header";
import { apiUrl } from "../../libs/api-base";
import { dispatchLlmStatus, getClientId, getSelectedProvider } from "../../libs/llm";
import { Throttle } from "../../libs/utils";
import { OnlineCourseEventCallback } from "../../types/online-course";

const config = {
  name: "dracula",
  dark: true,
  background: "#282A36",
  foreground: "#F8F8F2",
  selection: "#ef4146",
  selectionMatch: "#ef414644",
  cursor: "#F8F8F2",
  dropdownBackground: "#282A36",
  dropdownBorder: "#191A21",
  activeLine: "#44475A00",
  matchingBracket: "#ef4146",
  keyword: "#FF79C6",
  storage: "#FF79C6",
  variable: "#F8F8F2",
  parameter: "#F8F8F2",
  function: "#50FA7B",
  string: "#F1FA8C",
  constant: "#BD93F9",
  type: "#8BE9FD",
  class: "#8BE9FD",
  number: "#BD93F9",
  comment: "#909cc3",
  heading: "#BD93F9",
  invalid: "#FF5555",
  regexp: "#F1FA8C",
};
const _draculaTheme = EditorView.theme(
  {
    "&": {
      color: config.foreground,
      backgroundColor: config.background,
    },
    ".cm-content": { caretColor: config.cursor },
    ".cm-cursor, .cm-dropCursor": { borderLeftColor: config.cursor },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection":
      { backgroundColor: config.selection + " !important" },
    ".cm-panels": {
      backgroundColor: config.dropdownBackground,
      color: config.foreground,
    },
    ".cm-panels.cm-panels-top": { borderBottom: "2px solid black" },
    ".cm-panels.cm-panels-bottom": { borderTop: "2px solid black" },
    ".cm-searchMatch": {
      backgroundColor: config.dropdownBackground,
      outline: `1px solid ${config.dropdownBorder}`,
    },
    ".cm-searchMatch.cm-searchMatch-selected": {
      backgroundColor: config.selectionMatch,
    },
    ".cm-activeLine": {
      backgroundColor: config.activeLine,
      border: "1px dotted #44475A",
    },
    ".cm-selectionMatch": { backgroundColor: config.selectionMatch },
    "&.cm-focused .cm-matchingBracket, &.cm-focused .cm-nonmatchingBracket": {
      backgroundColor: config.matchingBracket,
      outline: "none",
    },
    ".cm-gutters": {
      backgroundColor: config.background,
      color: config.foreground,
      border: "none",
    },
    ".cm-activeLineGutter": { backgroundColor: config.background },
    ".cm-foldPlaceholder": {
      backgroundColor: "transparent",
      border: "none",
      color: config.foreground,
    },
    ".cm-tooltip": {
      border: `1px solid ${config.dropdownBorder}`,
      backgroundColor: config.dropdownBackground,
      color: config.foreground,
    },
    ".cm-tooltip .cm-tooltip-arrow:before": {
      borderTopColor: "transparent",
      borderBottomColor: "transparent",
    },
    ".cm-tooltip .cm-tooltip-arrow:after": {
      borderTopColor: config.foreground,
      borderBottomColor: config.foreground,
    },
    ".cm-tooltip-autocomplete": {
      "& > ul > li[aria-selected]": {
        background: config.selection,
        color: config.foreground,
      },
    },
  },
  { dark: config.dark }
);

const _draculaHighlightStyle = HighlightStyle.define([
  { tag: tags.keyword, color: config.keyword },
  {
    tag: [tags.name, tags.deleted, tags.character, tags.macroName],
    color: config.variable,
  },
  { tag: [tags.propertyName], color: config.function },
  {
    tag: [
      tags.processingInstruction,
      tags.string,
      tags.inserted,
      tags.special(tags.string),
    ],
    color: config.string,
  },
  {
    tag: [tags.function(tags.variableName), tags.labelName],
    color: config.function,
  },
  {
    tag: [tags.color, tags.constant(tags.name), tags.standard(tags.name)],
    color: config.constant,
  },
  { tag: [tags.definition(tags.name), tags.separator], color: config.variable },
  { tag: [tags.className], color: config.class },
  {
    tag: [
      tags.number,
      tags.changed,
      tags.annotation,
      tags.modifier,
      tags.self,
      tags.namespace,
    ],
    color: config.number,
  },
  { tag: [tags.typeName], color: config.type, fontStyle: config.type },
  { tag: [tags.operator, tags.operatorKeyword], color: config.keyword },
  {
    tag: [tags.url, tags.escape, tags.regexp, tags.link],
    color: config.regexp,
  },
  { tag: [tags.meta, tags.comment], color: config.comment },
  { tag: tags.strong, fontWeight: "bold" },
  { tag: tags.emphasis, fontStyle: "italic" },
  { tag: tags.link, textDecoration: "underline" },
  { tag: tags.heading, fontWeight: "bold", color: config.heading },
  {
    tag: [tags.atom, tags.bool, tags.special(tags.variableName)],
    color: config.variable,
  },
  { tag: tags.invalid, color: config.invalid },
  { tag: tags.strikethrough, textDecoration: "line-through" },
]);

const theme = [_draculaTheme, syntaxHighlighting(_draculaHighlightStyle)];

interface Props extends OnlineCourseEventCallback {
  lang: string;
  meta: string;
  codes: string;
  codeVersion?: number;
  readOnly?: boolean;
  noActions?: boolean;
  index?: number;
  callback?: (index: number, result: any, input?: any) => void;
}

let Log = styled.div`
  font-family: system-ui;
  font-size: 14px;
  margin: 10px 0;
`;

let Pre = styled.pre`
  color: black;
  margin-top: 0px !important;
  border: 1px solid #cccccc55 !important;
  background-color: white !important;
  white-space: pre-wrap !important;
`;

declare global {
  interface String {
    indexOfRegex(regex: RegExp): any[];
  }
}

String.prototype.indexOfRegex = function (regex: RegExp): any[] {
  const match = this.match(regex);
  return [match ? this.indexOf(match[0]) : -1, match ? match[0] : null];
};

const ChatBlock = (props: Props) => {
  const user = useSelector((state: ReduxStoreState) => state.user.user);
  const apiServerToken = useSelector((state: ReduxStoreState) => state.apiServerToken.apiServerToken);

  const editorRef = useRef<HTMLDivElement | null>(null);
  const spinnerRef = useRef<HTMLImageElement | null>(null);
  const spinnerRunRef = useRef<HTMLImageElement | null>(null);
  const micRef = useRef<any | null>(null);

  const extraInfoRef = useRef<HTMLTextAreaElement | null>(null);
  const topicSelectRef = useRef<HTMLSelectElement | null>(null);

  const [editView, setEditView] = useState<EditorView | null>(null);
  const [output, setOutput] = useState("");
  const [hasQuestion, setHasQuestion] = useState(false);

  const [chatDone, setChatDone] = useState(true);

  const [outputElements, setOutputElements] = useState<any[]>([]);

  const callbackRef = useRef(false);

  const { t } = useTranslation("common");

  const audioStarted = useRef(0);
  const audioEnded = useRef(0);

  let meta: any = {};
  try {
    meta = RJSON.parse(props.meta ?? "{}");
  } catch (e: any) {
    logger.error(e.message);
  }

  if (!meta.api) meta.api = "chat";

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
    formData.append("action", "chat");
    handleRun(formData);

    return {
      blob,
      text: "OK",
    };
  };

  let kotlinTimer: any = null;

  let supported = true;

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
      //let fromLine = doc.lineAt(v.state.selection.main.from)
      //let toLine = doc.lineAt(v.state.selection.main.to)
      if (v.docChanged){
        if (props.onDocChanged){
          customThrottle.onHandle(() => {
            props.onDocChanged?.call(null,v.state.doc.toString())
          },350);
        }
      }
    })
  ];

  if (meta.action === "translate") {
    extensions.push(lineNumbers());
    extensions.push(java());
    extensions.push(theme);
  } else {
    extensions.push(markdown());
  }

  /*switch (props.lang) {
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
    case 'c':
    case 'cpp':
    case 'c++':
    case 'go':
    case 'dart':
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      break
    default:
      extensions.push(lineNumbers())
      extensions.push(java())
      //extensions = [... extensions, lineNumbers(), StreamLanguage.define(dart)]
      supported = false
  }*/

  if (props.noActions) supported = false;

  if (meta.api == "code") supported = true;

  if (props.readOnly || meta.readOnly) {
    extensions.push(EditorView.editable.of(false));
  }

  const state = EditorState.create({
    doc: props.codes,
    extensions,
  });

  const viewRef = useRef<any | null>(null);

  useEffect(() => {
    let langInfo = props.lang;
    if ((langInfo === "markdown" || langInfo === "any") && meta.topic)
      langInfo = meta.topic;

    let chatLang = "any";
    switch (langInfo) {
      case "html":
        chatLang = "html";
        break;
      case "js":
      case "javascript":
        chatLang = "javascript";
        break;
      case "ts":
      case "typescript":
        break;
      case "react":
      case "jsx":
      case "tsx":
        chatLang = "tsx";
        break;
      case "rn": // react native
        chatLang = "rn";
        break;
      case "py":
      case "python":
        chatLang = "python";
        break;
      case "pp":
      case "php":
        chatLang = "php";
        break;
      case "jv":
      case "java":
        chatLang = "java";
        break;
      case "kt":
      case "kotlin":
        chatLang = "kotlin";
        break;
      case "sw":
      case "swift":
        chatLang = "swift";
        break;
      case "rs":
        case "rust":
          chatLang = "rust";
          break;
      case "c":
        chatLang = "c";
        break;
      case "cp":
      case "cpp":
      case "c++":
        chatLang = "c++";
        break;
      case "objc":
      case "objective-c":
        chatLang = "objective-c";
        break;
      case "go":
        chatLang = "go";
        break;
      case "dt":
      case "dart":
        chatLang = "dart";
        break;
      case "flt":
      case "flutter":
        chatLang = "flutter";
      case "u":
        chatLang = localStorage.getItem("prefer_lang") || "dart";
        break;
      default:
        chatLang = "any";
    }

    if (meta.general === false && chatLang == "any") {
      chatLang = "dart";
    }

    if (topicSelectRef.current) {
      topicSelectRef.current.value = chatLang;
    }

    if (meta.optional && props.callback && props.index) {
      if (!callbackRef.current) {
        callbackRef.current = true;
        props.callback(props.index, 1);
      }
    }

    if (editorRef.current == null) {
      return;
    }

    viewRef.current = new EditorView({ state, parent: editorRef.current });

    setEditView(viewRef.current);
    return () => {
      viewRef?.current.destroy();
      // editorRef.current.removeEventListener("input", log);
    };
  }, []);

  useEffect(() => {
    if (editView == null) return;

    let transaction = editView?.state.update({
      changes: { from: 0, to: editView?.state.doc.length, insert: props.codes },
    });
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(
      transaction ? transaction : { changes: { from: 0, insert: "0" } }
    );
  }, [props.codes, props.codeVersion]); // codeVersion force update the conntent if the content is changed, but props.codes is not changed

  const handleRun = async (fileFormData: any, run?: Boolean) => {
    if (viewRef?.current.state.doc.toString().trim().length < 2) return;

    if (props.lang == "json") {
      try {
        let data = JSON.parse(viewRef?.current.state.doc.toString());
      } catch (e: any) {
        setOutput(JSON.stringify(e.message));
        return;
      }
    }

    /*if (props.lang == 'kotlin') {
      kotlinTimer = setTimeout(function () {
        setOutput("For technical reason, compiling kotlin can take up to 30s, please wait ..., but we will improve this soon.")
      }, 3000);
    }*/
    if (!meta.api) setOutput("");
    try {
      if (meta.api == "chat" && !run) {
        setChatDone(true);

        if (spinnerRef.current && !spinnerRef.current.classList.contains("hidden")) {
          return;
        }
        spinnerRef.current?.classList.remove("hidden");

        let dataReceived = false;
        let chatResponse = "";
        let outputData = "";

        let lang = props.lang;
        let message = viewRef?.current.state.doc.toString();

        if (meta.action == "translate") {
          lang = props.lang == "flutter" ? "dart" : props.lang;
          if (props.lang == "react") lang = "typescript";
          let msg = message.toLowerCase();

          if (msg.indexOf("dart lang") > -1) {
            lang = "dart";
          } else if (msg.indexOf("kotlin lang") > -1) {
            lang = "kotlin";
          } else if (msg.indexOf("swift lang") > -1) {
            lang = "swift";
          }  else if (msg.indexOf("rust lang") > -1) {
            lang = "rust";
          } else if (msg.indexOf("java lang") > -1) {
            lang = "java";
          } else if (msg.indexOf("python lang") > -1) {
            lang = "python";
          } else if (msg.indexOf("php lang") > -1) {
            lang = "php";
          } else if (msg.indexOf("javascript lang") > -1) {
            lang = "javascript";
          } else if (msg.indexOf("typescript lang") > -1) {
            lang = "typescript";
          } else if (msg.indexOf("objective-c lang") > -1) {
            lang = "objective-c";
          } else if (msg.indexOf("objc lang") > -1) {
            lang = "objective-c";
          } else if (msg.indexOf("c lang") > -1) {
            lang = "c";
          } else if (msg.indexOf("c++ lang") > -1) {
            lang = "c++";
          } else if (msg.indexOf("go lang") > -1) {
            lang = "go";
          } else if (msg.indexOf("natural") > -1) {
            lang = "natural";
          } else if (msg.indexOf("human") > -1) {
            lang = "natural";
          }

          if (!lang || lang == "any") {
            setOutput(
              "Please specify the language in your code's comment, e.g. 'natural', 'java', 'kotlin', 'dart', 'swift', 'rust', 'python', 'php', 'javascript', 'typescript'"
            );
            spinnerRef.current?.classList.add("hidden");
            return;
          }

          if (topicSelectRef.current!.value == "any") {
            setOutput(
              "Please select which language you want to translate in the dropdown above"
            );
            spinnerRef.current?.classList.add("hidden");
            return;
          } else if (topicSelectRef.current!.value == lang) {
            setOutput("Please select a different language to translate");
            spinnerRef.current?.classList.add("hidden");
            return;
          }
        } else {
          if (topicSelectRef.current && topicSelectRef.current.value != "any") {
            lang = topicSelectRef.current.value;
          }
        }

        let body: any = JSON.stringify({
          lang,
          toLang:
            meta.action == "translate" ? topicSelectRef.current?.value : false,
          meta: props.meta,
          extraInfo: extraInfoRef.current?.value,
          message,
          taskId: props.taskId,
          onlineCourseSessionId: props.onlineCourseSessionId,
        });

        let isAudio = false;
        let audioText = "";
        if (!fileFormData.target) isAudio = true;

        let header = getApiServerAuthHeader(user.id, apiServerToken);

        if (isAudio) {
          body = fileFormData;
          body.append("lang", lang);
          body.append("meta", props.meta);
          body.append("extraInfo", extraInfoRef.current?.value);
        } else {
          header = getJsonAuthHeader(header);
        }
        // axios not work for stream in browser
        const provider = getSelectedProvider();
        const clientId = getClientId();
        dispatchLlmStatus(true);
        const response = await fetch(
          apiUrl("/rest/" + (!isAudio ? meta.api : "audio")),
          {
            method: "POST",
            headers: header,
            body: isAudio
              ? (() => {
                  body.append("provider", provider ?? "");
                  body.append("client_id", clientId);
                  return body;
                })()
              : JSON.stringify({
                  ...JSON.parse(body as string),
                  provider,
                  client_id: clientId,
                }),
          }
        );

        props.onSubmit?.call(null);

        const reader = response.body!.getReader();

        let currentBlockIndex = 0;
        let currentBlockType = "markdown";
        let currentBlockLang = "";
        let currentBlockData = "";
        const _currentBlock = (
          <Markdown key={currentBlockIndex}>{currentBlockData}</Markdown>
        );

        setOutputElements((_) => [_currentBlock]);

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          if (!dataReceived) {
            setOutput("");
            setOutputElements([]);
            setChatDone(false);
            dataReceived = true;
          }

          let data = new TextDecoder("utf-8").decode(value!);
          if (data == "[-DONE-]") {
          } else if (data == "[-ERROR-]") {
            setOutput("Error-1!");
          } else if (data == "[-LIMIT-]") {
            setOutput("Daily limit is reached!");
          } else if (data == "[-SILENCE-]") {
            setOutput("Audio recording is too short!");
          } else {
            chatResponse += data;
            outputData += data;

            if (isAudio && audioText.length == 0) {
              if (chatResponse.indexOf("\n") > 0) {
                audioText = chatResponse.substring(
                  0,
                  chatResponse.indexOf("\n")
                );
                chatResponse = chatResponse.substring(
                  chatResponse.indexOf("\n") + 1
                );
                //console.log(audioText)

                let transaction = editView?.state.update({
                  changes: {
                    from: 0,
                    to: editView?.state.doc.length,
                    insert: audioText,
                  },
                });
                editView?.dispatch(
                  transaction
                    ? transaction
                    : { changes: { from: 0, insert: "0" } }
                );
              } else {
                continue;
              }
            }

            while (true) {
              // start processing chat response
              if (currentBlockType == "markdown") {
                let codeBlockStart =
                  chatResponse.indexOfRegex(/```[a-z\+\-]*\n/);
                if (chatResponse.length > 15 && codeBlockStart[0] == -1) {
                  currentBlockData += chatResponse.substring(
                    0,
                    chatResponse.length - 15
                  );
                  chatResponse = chatResponse.substring(
                    chatResponse.length - 15
                  );

                  const _currentBlockIndex = currentBlockIndex;
                  const _currentBlock = (
                    <Markdown key={currentBlockIndex}>
                      {currentBlockData.replace("[-DONE-]", "")}
                    </Markdown>
                  );
                  setOutputElements((prevElements) => {
                    prevElements = prevElements.filter(
                      (e: any) => e.key != _currentBlockIndex
                    );
                    let newElements = [...prevElements, _currentBlock];
                    return newElements;
                  });

                  break;
                } else if (codeBlockStart[0] >= 0) {
                  if (codeBlockStart[0] > 0) {
                    // write out all markdown before code block
                    currentBlockData += chatResponse.substring(
                      0,
                      codeBlockStart[0]
                    );

                    const _currentBlockIndex = currentBlockIndex;
                    const _currentBlock = (
                      <Markdown key={currentBlockIndex}>
                        {currentBlockData.replace("[-DONE-]", "")}
                      </Markdown>
                    );
                    setOutputElements((prevElements) => {
                      prevElements = prevElements.filter(
                        (e: any) => e.key != _currentBlockIndex
                      );
                      let newElements = [...prevElements, _currentBlock];
                      return newElements;
                    });
                  }

                  currentBlockIndex++;
                  currentBlockData = "";
                  currentBlockLang = codeBlockStart[1]
                    .trim()
                    .replace("```", "");
                  const _currentBlock = (
                    <CodeBlock
                      key={currentBlockIndex}
                      codes={currentBlockData}
                      lang={currentBlockLang}
                      meta="{from:chat, action: run}"
                    ></CodeBlock>
                  );
                  currentBlockType = "code";
                  setOutputElements((prevElements) => [
                    ...prevElements,
                    _currentBlock,
                  ]);

                  chatResponse = chatResponse.substring(
                    codeBlockStart[0] + codeBlockStart[1].length
                  );

                  continue;
                } else {
                  break;
                }
              } else {
                let codeBlockEnd = chatResponse.indexOfRegex(/```/);
                if (chatResponse.length >= 3 && codeBlockEnd[0] == -1) {
                  currentBlockData += chatResponse.substring(
                    0,
                    chatResponse.length - 3
                  );
                  chatResponse = chatResponse.substring(
                    chatResponse.length - 3
                  );

                  if (currentBlockData.includes("package:flutter/")) {
                    currentBlockLang = "flutter";
                  } else if (currentBlockData.match(/from\s+('|")react('|")/)) {
                    currentBlockLang = "react";
                  }

                  const _currentBlockIndex = currentBlockIndex;
                  const _currentBlock = (
                    <CodeBlock
                      key={currentBlockIndex}
                      codes={currentBlockData}
                      lang={currentBlockLang}
                      meta="{from:chat, action: run}"
                    ></CodeBlock>
                  );
                  setOutputElements((prevElements) => {
                    prevElements = prevElements.filter(
                      (e: any) => e.key != _currentBlockIndex
                    );
                    let newElements = [...prevElements, _currentBlock];
                    return newElements;
                  });

                  break;
                } else if (codeBlockEnd[0] >= 0) {
                  if (codeBlockEnd[0] > 0) {
                    // write out all code before markdown block
                    currentBlockData += chatResponse.substring(
                      0,
                      codeBlockEnd[0]
                    );

                    const _currentBlockIndex = currentBlockIndex;
                    const _currentBlock = (
                      <CodeBlock
                        key={currentBlockIndex}
                        codes={currentBlockData}
                        lang={currentBlockLang}
                        meta="{from:chat, action: run}"
                      ></CodeBlock>
                    );
                    setOutputElements((prevElements) => {
                      prevElements = prevElements.filter(
                        (e: any) => e.key != _currentBlockIndex
                      );
                      let newElements = [...prevElements, _currentBlock];
                      return newElements;
                    });
                  }

                  if (currentBlockData.includes("package:flutter/")) {
                    const _currentBlockIndex = currentBlockIndex;
                    currentBlockLang = "flutter";
                    const _currentBlock = (
                      <CodeBlock
                        key={currentBlockIndex}
                        reload={true}
                        codes={currentBlockData}
                        lang={currentBlockLang}
                        meta="{from:chat, action: run}"
                      ></CodeBlock>
                    );
                    setOutputElements((prevElements) => {
                      prevElements = prevElements.filter(
                        (e: any) => e.key != _currentBlockIndex
                      );
                      let newElements = [...prevElements, _currentBlock];
                      return newElements;
                    });
                  } else if (currentBlockData.match(/from\s+('|")react('|")/)) {
                    const _currentBlockIndex = currentBlockIndex;
                    currentBlockLang = "react";
                    const _currentBlock = (
                      <CodeBlock
                        key={currentBlockIndex}
                        reload={true}
                        codes={currentBlockData}
                        lang={currentBlockLang}
                        meta="{from:chat, action: run}"
                      ></CodeBlock>
                    );
                    setOutputElements((prevElements) => {
                      prevElements = prevElements.filter(
                        (e: any) => e.key != _currentBlockIndex
                      );
                      let newElements = [...prevElements, _currentBlock];
                      return newElements;
                    });
                  }

                  currentBlockIndex++;
                  currentBlockData = "";
                  const _currentBlock = (
                    <Markdown key={currentBlockIndex}>
                      {currentBlockData}
                    </Markdown>
                  );
                  currentBlockType = "markdown";
                  setOutputElements((prevElements) => [
                    ...prevElements,
                    _currentBlock,
                  ]);

                  chatResponse = chatResponse.substring(
                    codeBlockEnd[0] + codeBlockEnd[1].length
                  );
                  continue;
                } else {
                  break;
                }
              }
            } // end process data
          }
        }

        if (chatResponse.length > 0) {
          if (currentBlockType == "markdown") {
            currentBlockData += chatResponse;
            const _currentBlockIndex = currentBlockIndex;
            const _currentBlock = (
              <Markdown key={currentBlockIndex}>
                {currentBlockData.replace("[-DONE-]", "")}
              </Markdown>
            );
            setOutputElements((prevElements) => {
              prevElements = prevElements.filter(
                (e: any) => e.key != _currentBlockIndex
              );
              let newElements = [...prevElements, _currentBlock];
              return newElements;
            });
          } else {
            currentBlockData += chatResponse;
            const _currentBlockIndex = currentBlockIndex;
            if (currentBlockData.includes("package:flutter/")) {
              currentBlockLang = "flutter";
            } else if (currentBlockData.match(/from\s+('|")react('|")/)) {
              currentBlockLang = "react";
            }
            const _currentBlock = (
              <CodeBlock
                key={currentBlockIndex}
                codes={currentBlockData}
                reload={true}
                lang={currentBlockLang}
                meta="{from:chat, action: run}"
                taskId={props.taskId}
                onlineCourseSessionId={props.onlineCourseSessionId}
              ></CodeBlock>
            );
            setOutputElements((prevElements) => {
              prevElements = prevElements.filter(
                (e: any) => e.key != _currentBlockIndex
              );
              let newElements = [...prevElements, _currentBlock];
              return newElements;
            });
          }
        }

        dispatchLlmStatus(false);
        spinnerRef.current?.classList.add("hidden");

        setChatDone(true);

        if (meta.promptType && props.callback) {
          props.callback(1, outputData.replace("[-DONE-]", ""), viewRef?.current.state.doc.toString());
          setOutput("");
          setOutputElements([]);
          return;
        } 

        if (callbackRef.current) return;
        callbackRef.current = true;
        if (props.callback) props.callback(props.index ?? 0, 1);

        //editorRef.current?.scrollIntoView()
        //window.scrollTo(curXOffset, curYOffset)

        return;
      } else {
        if (spinnerRunRef.current && !spinnerRunRef.current.classList.contains("hidden")) {
          return;
        }
        spinnerRunRef.current?.classList.remove("hidden");

        setChatDone(false);

        let lang = props.lang == "flutter" ? "dart" : props.lang;
        if (props.lang == "react") lang = "typescript";
        let msg = viewRef?.current.state.doc.toString();

        if (msg.indexOf("dart lang") > -1) {
          lang = "dart";
        } else if (msg.indexOf("kotlin lang") > -1) {
          lang = "kotlin";
        } else if (msg.indexOf("swift lang") > -1) {
          lang = "swift";
        } else if (msg.indexOf("rust lang") > -1) {
          lang = "rust";
        } else if (msg.indexOf("java lang") > -1) {
          lang = "java";
        } else if (msg.indexOf("python lang") > -1) {
          lang = "python";
        } else if (msg.indexOf("php lang") > -1) {
          lang = "php";
        } else if (msg.indexOf("javascript lang") > -1) {
          lang = "javascript";
        } else if (msg.indexOf("typescript lang") > -1) {
          lang = "typescript";
        } else if (msg.indexOf("objective-c lang") > -1) {
          lang = "objective-c";
        } else if (msg.indexOf("objc lang") > -1) {
          lang = "objective-c";
        } else if (msg.indexOf("c lang") > -1) {
          lang = "c";
        } else if (msg.indexOf("c++ lang") > -1) {
          lang = "c++";
        } else if (msg.indexOf("go lang") > -1) {
          lang = "go";
        }

        let res;

        if (props.lang != "kotlin") {
          res = await axios({
            method: "POST",
            url: apiUrl("/api/execute_code"),
            // headers: {
            //   "Content-Type": "application/json",
            //   Authorization: `Bearer ${localStorage.getItem("token")}`,
            // },
            headers: getHeader(user.id,apiServerToken),
            data: {
              lang,
              meta: props.meta,
              source: viewRef?.current.state.doc.toString(),
              taskId: props.taskId,
              onlineCourseSessionId: props.onlineCourseSessionId,
            },
          });
        } else {
          let sourceCode = viewRef?.current.state.doc.toString();
          if (!meta.rawCode && !sourceCode.match(/fun\s+main\s*\(/)) {
            sourceCode = `fun main() {
                    ${sourceCode}
              }`;
          }
          res = await axios({
            method: "POST",
            timeout: 9000,
            url: "https://api.kotlinlang.org//api/1.8.10/compiler/run",
            data: {
              args: "",
              files: [
                {
                  name: "File.kt",
                  text: sourceCode,
                },
              ],
            },
          });

          if (res.data.text.length > 0) {
            res = {
              data: {
                data: {
                  execute_code: {
                    result: res.data.text
                      .replace("<outStream>", "")
                      .replace("</outStream>", ""),
                  },
                },
              },
            };
          } else if (
            res.data.errors &&
            res.data.errors["File.kt"] &&
            res.data.errors["File.kt"][0].message &&
            res.data.errors["File.kt"][0].message.length > 0
          ) {
            res = {
              data: {
                data: {
                  execute_code: {
                    result: res.data.errors["File.kt"][0].message,
                  },
                },
              },
            };
          } else {
            res = { data: { data: { execute_code: { result: "Error-4!" } } } };
          }
        }

        props.onSubmit?.call(null);

        const data = res.data;
        if (data.error) {
          logger.error(data.error.errors);
          setOutput("Error-2!");
          props.onError?.call(null);
        } else {
          setOutput(data.data.execute_code.result);
        }

        spinnerRunRef.current?.classList.add("hidden");
      }
    } catch (e) {
      if (kotlinTimer != null) {
        clearTimeout(kotlinTimer);
        kotlinTimer = null;
      }
      console.log(e);
      setOutput("Error-3!");
      props.onError?.call(null);
      dispatchLlmStatus(false);
    }
    if (!run) spinnerRef.current?.classList.add("hidden");
    else spinnerRunRef.current?.classList.add("hidden");
  };

  const handleReset = () => {
    // reset the user-modified code
    // editView?.state.doc = props.codes;

    if (spinnerRef.current && !spinnerRef.current.classList.contains("hidden")) {
      return;
    }

    let transaction = editView?.state.update({
      changes: {
        from: 0,
        to: editView?.state.doc.length,
        insert: meta.reset ? props.codes : "\n\n\n",
      },
    });
    //console.log(transaction?.state.doc.toString())
    // At this point the view still shows the old state.
    editView?.dispatch(
      transaction ? transaction : { changes: { from: 0, insert: "0" } }
    );
    props.onReset?.call(null);

    setOutput("");
    setOutputElements([]);
  };

  //console.log(meta)

  return (<>
    {(meta.caption || meta.detail)&&
    <div>
      {meta.caption && <h4>{meta.caption}</h4>}
      {meta.detail && <h5 className="whitespace-pre">{meta.detail}</h5>}
    </div>}
    <div className="chat-block mb-6 relative">
      <div
        className="copy-code-wrap"
        onClick={async () => {
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
        }}
        style={{
          position: "absolute",
          cursor: "pointer",
          width: 24,
          height: 24,
          top: 5,
          right: 5,
          color: "white",
          zIndex: 9,
        }}
      >
        <img className="copy-code" src="/img/copy.png" />
      </div>
      <div
        className="border-2"
        ref={editorRef}
        style={{
          minHeight: meta.minHeight ?? "90px",
          maxHeight: meta.resize ? undefined : (meta.maxHeight ?? "50vh"),
          overflow: "auto",
          height: meta.height ?? undefined,
          resize: meta.resize ? 'vertical' : 'none'
        }}
      ></div>
      <textarea
        ref={extraInfoRef}
        className="hidden"
        style={{
          boxSizing: "border-box",
          width: "calc(100% - 4px)",
          margin: "4px 2px",
        }}
        placeholder="You have the option to submit additional documentation or sample code that can assist AI in completing your task more effectively. Please provide them here."
      ></textarea>
      {supported ? (
        <div className="flex justify-end items-center px-1 mt-2 mb-2 gap-2">
          {meta.dropdown !== false && (
            <select
              ref={topicSelectRef}
              onChange={() => {
                if (
                  topicSelectRef.current?.value &&
                  topicSelectRef.current?.value != "any"
                ) {
                  try {
                    localStorage.setItem(
                      "prefer_lang",
                      topicSelectRef.current?.value
                    );
                  } catch (e) {}
                }
              }}
            >
              {meta.general !== false && (
                <option value="any">
                  {meta.action == "translate" ? "Translate to" : "General"}
                </option>
              )}
              {meta.show_vibe_learning === true && (
                <option value="vibe-learning">Vibe Learning</option>
              )}
              <option value="dart">Dart</option>
              <option value="flutter">Flutter</option>
              <option value="html">HTML/CSS</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="tsx">React</option>
              <option value="rn">React Native</option>
              <option value="python">Python</option>
              <option value="php">PHP</option>
              <option value="swift">Swift</option>
              <option value="java">Java</option>
              <option value="kotlin">Kotlin</option>
              <option value="c">C</option>
              <option value="c++">++C</option>
              <option value="objective-c">Objective-C</option>
              <option value="go">Golang</option>
              <option value="Rust">Rust</option>
              <option value="assembly">Assembly</option>
            </select>
          )}
          {meta.extraInfo != false && (
            <PaperClipIcon
              className="w-6 h-6 text-primary-blue hover:opacity-80 cursor-pointer inline select-none mx-2"
              title="Add Extra Information"
              onClick={() => {
                extraInfoRef.current?.classList.toggle("hidden");
              }}
            ></PaperClipIcon>
          )}

          {false && meta.audio ? (
            <button
              ref={micRef}
              className="select-none"
              onContextMenu={(e) => e.preventDefault()}
            >
              <MicrophoneIcon className="w-7 h-7 text-primary-blue hover:text-red cursor-pointer select-none" />
            </button>
          ) : null}

          <button
            className="w-auto select-none rounded h-10 border-primary-blue text-white font-medium bg-primary-blue hover:opacity-80 flex flex-row items-center gap-2 px-4"
            onClick={handleRun}
            onContextMenu={(e) => e.preventDefault()}
          >
            <span className="whitespace-nowrap">
              {meta.button ? meta.button : t("ask-now")}
            </span>
            <div ref={spinnerRef} className="loader hidden w-5 h-5"></div>
          </button>
          {props.readOnly || meta.readOnly ? null : meta.action ==
            "translate" ? (
            <button
              className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50 select-none"
              style={{ color: "black" }}
              onClick={() => handleRun(undefined, true)}
              onContextMenu={(e) => e.preventDefault()}
            >
              <span>Run</span>
              <div ref={spinnerRunRef} className="loader hidden w-5 h-5"></div>
            </button>
          ) : (
            <button
              className="w-auto px-4 rounded h-10 border border-gray-400 text-black font-medium bg-secondary-white hover:bg-gray-50 select-none"
              style={{ color: "black" }}
              onClick={handleReset}
              onContextMenu={(e) => e.preventDefault()}
            >
              {meta.reset ? t("reset") : t("clear")}
            </button>
          )}
          {meta.from == "chat" ? (
            <button
              className="w-auto px-4 h-8 bg-white rounded-md shadow-md inline-flex justify-center"
              onClick={() => setHasQuestion(true)}
            >
              {t("ask")} ?
            </button>
          ) : null}
        </div>
      ) : null}
      {output && (
        <Log>
          {t("output")}:
          {chatDone ? (
            <div
              style={{
                backgroundColor: "white",
                border: `1px solid #cccccc55`,
                padding: 10,
              }}
            >
              <MarkdownRenderer
                markdown={output}
                lang={meta.topic}
                meta={`{"from":"chat"}`}
              ></MarkdownRenderer>
            </div>
          ) : (
            <Pre>{output}</Pre>
          )}
        </Log>
      )}
      {meta.from == "chat" && hasQuestion ? (
        <>
          <div>
            <b>{t("question")}:</b>{" "}
          </div>
          <div className="w-full">
            <ChatBlock
              codes={
                new RegExp(/(\/\/|#)\s*(todo|update|edit|fix|please|pls)/i).test(props.codes) ? 
                "Please complete the code below according to the requirements specified in the comments: \n\n" + props.codes
                :
                "Can you explain the code below? As I can not understand it: \n\n" + props.codes
              }
              lang={props.lang}
              meta={"{type:chat, audio:false}"}
            ></ChatBlock>
          </div>
        </>
      ) : null}
      <div style={{ color: "#0c41b5" }}>{outputElements}</div>
      <style jsx>{`
        .copy-code {
          width: 24px;
          height: 24px;
          margin: 0px !important;
        }

        .copy-code-wrap:active .copy-code {
          transform: translate(0, 0) scale(0.9);
        }

        select {
          border: none;
          outline: none;
          background-color: transparent;
          color: black;
          box-shadow: none;
          padding-right: 2rem;
          text-align-last: right;
        }

        select:focus {
          outline: none;
        }

        option {
          direction: rtl;
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
    </div></>
  );
};

export default memo(ChatBlock);
