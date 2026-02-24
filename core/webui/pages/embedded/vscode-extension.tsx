import React, { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import { GetStaticPropsContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations'
import axios from "axios";

import { ControlledMenu, MenuItem } from '@szhsin/react-menu';
import '@szhsin/react-menu/dist/index.css';

import CodeBlock from '../../components/blocks/code.block';
import ChatBlock from '../../components/blocks/chat.block';
import { apiUrl } from '../../libs/api-base';
import { dispatchLlmStatus, getClientId, getSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');

interface LlmProvider {
  id: string;
  name: string;
}

// --- Helper Functions (Unchanged) ---
function removeCustomComments(code: string) {
  let inCommentBlock = false;
  const lines = code.split('\n');
  const filteredLines = [];

  for (let line of lines) {
    if (line.includes('/*+')) {
      inCommentBlock = true;
    }

    if (!inCommentBlock) {
      filteredLines.push(line);
    }

    if (line.includes('+*/')) {
      inCommentBlock = false;
    }
  }

  return filteredLines.join('\n');
}

const getLangFromExt = (ext: string) => {
  switch (ext) {
    case 'dart': return 'dart';
    case 'go': return 'go';
    case 'java': return 'java';
    case 'js': return 'javascript';
    case 'json': return 'json';
    case 'kt': return 'kotlin';
    case 'md': return 'markdown';
    case 'php': return 'php';
    case 'py': return 'python';
    case 'rs': return 'rust';
    case 'scss': return 'scss';
    case 'sh': return 'bash';
    case 'ts': return 'typescript';
    case 'jsx':
    case 'tsx': return 'react';
    case 'yaml':
    case 'yml': return 'yaml';
    case 'c': return 'c';
    case 'cc':
    case 'cpp': return 'c++';
    case 'swift': return 'swift';
    case 'm':
    case 'mm': return 'objective-c';
    case 'css':
    case 'htm':
    case 'html': return 'html';
    default: return 'natural';
  }
}

function isEditor(node: any) {
  let i = 0;
  while (node) {
    if (node?.nodeType == 1 && node.classList.contains('cm-editor')) {
      return true;
    }
    node = node?.parentNode;
    i++;
    if (i > 100) return false;
  }
  return false;
}
// --- End Helper Functions ---


// --- Updated Tab Type ---
type ActiveTab = 'assistant' | 'execute' | 'translate';

const EmbeddedVSCodeExtension = (props: any) => {

  // --- Refs ---
  const translateLangSelectRef = useRef<HTMLSelectElement | null>(null);
  const codeLangSelectRef = useRef<HTMLSelectElement | null>(null);

  // --- State ---
  const [isMenuOpen, setMenuOpen] = useState(false);
  const [menuAnchorPoint, setMenuAnchorPoint] = useState({ x: 0, y: 0 });
  const [menuFrameId, setMenuFrameId] = useState<string>('');

  // Tab state
  const [activeTab, setActiveTab] = useState<ActiveTab>('assistant'); // Default to Assistant

  // State for each panel
  const [codeAction, setCodeAction] = useState('run');
  const [code, setCode] = useState("console.log('Hello, JuniorIT.AI!')\n\n");
  const [codeLang, setCodeLang] = useState("javascript");

  const [translateLang, setTranslateLang] = useState("natural");
  const [translateCode, setTranslateCode] = useState("The entry point\n\nprint string 'Hello, JuniorIT.AI!'\nPrint integer 1234");

  const [assistantLang, setAssistantLang] = useState("any");
  const [assistantText, setAssistantText] = useState("Can you please give me a few examples of Dart functions?\n\n");

  // --- New State: Output Language ---
  const [outputLanguage, setOutputLanguage] = useState<string>('English'); // Default to English

  // --- LLM Provider State ---
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [llmRunning, setLlmRunning] = useState(false);

  // --- Connection Status State ---
  const [isConnected, setIsConnected] = useState(false);
  const [isCheckingConnection, setIsCheckingConnection] = useState(false);
  const checkingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Key refs for forcing re-renders if needed (Unchanged)
  const translateKeyValueRef = useRef<number>(0);
  const codeKeyValueRef = useRef<number>(0);
  const assistantKeyValueRef = useRef<number>(0);

  // --- Fetch LLM Providers ---
  const fetchLlmProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/llm/providers`);
      const providers: LlmProvider[] = res.data.providers || [];
      setLlmProviders(providers);
      const stored = getSelectedProvider();
      const defaultId = stored || providers[0]?.id || null;
      if (defaultId) {
        setSelectedProvider(defaultId);
      }
      setLlmProvider(defaultId);
    } catch (err) {
      console.error('Failed to fetch LLM providers:', err);
    }
  };

  const fetchAndSendLocalDevToken = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/local-dev-token`);
      const token = res.data?.token;
      if (typeof token === 'string' && token.length > 0) {
        window.parent.postMessage({ type: 'local-dev-token', token }, '*');
      }
    } catch (err) {
      console.error('Failed to fetch local dev token:', err);
    }
  };

  // --- Handle Stop LLM ---
  const handleStopLlm = async () => {
    try {
      const clientId = getClientId();
      await axios.post(`${API_BASE_URL}/llm/stop`, { client_id: clientId });
    } catch (err) {
      console.error('Failed to stop LLM:', err);
    } finally {
      dispatchLlmStatus(false);
      setLlmRunning(false);
    }
  };

  // --- Check Connection Status ---
  const checkConnectionStatus = () => {
    // Clear any existing timeout
    if (checkingTimeoutRef.current) {
      clearTimeout(checkingTimeoutRef.current);
    }
    setIsCheckingConnection(true);
    window.parent.postMessage({ type: 'check-connection' }, '*');
    // Timeout fallback: if no response within 5s, assume disconnected
    checkingTimeoutRef.current = setTimeout(() => {
      setIsCheckingConnection(false);
      setIsConnected(false);
    }, 5000);
  };

  // --- Handle Reconnect ---
  const handleReconnect = () => {
    if (isCheckingConnection) return;
    setIsCheckingConnection(true);
    window.parent.postMessage({ type: 'reconnect-socket' }, '*');
    // Timeout fallback: if no response within 10s, assume disconnected
    if (checkingTimeoutRef.current) {
      clearTimeout(checkingTimeoutRef.current);
    }
    checkingTimeoutRef.current = setTimeout(() => {
      setIsCheckingConnection(false);
      setIsConnected(false);
    }, 10000);
  };

  // --- Effects ---
  useEffect(() => {
    // Fetch LLM providers on mount
    fetchLlmProviders();
    fetchAndSendLocalDevToken();
  }, []);

  // --- LLM Status Listener ---
  useEffect(() => {
    const handler = (event: any) => {
      setLlmRunning(Boolean(event?.detail?.running));
    };
    window.addEventListener('llm:status', handler);
    return () => window.removeEventListener('llm:status', handler);
  }, []);

  // --- Connection Status Check on Mount and Visibility Change ---
  useEffect(() => {
    // Check connection on mount
    checkConnectionStatus();

    // Check connection when page becomes visible
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        checkConnectionStatus();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // --- Main Message Handler Effect ---
  useEffect(() => {
    let notifier: any = null;

    // Set initial select values based on state
    if (codeLangSelectRef.current) codeLangSelectRef.current.value = codeLang;
    if (translateLangSelectRef.current) translateLangSelectRef.current.value = translateLang;

    const onMessage = async (event: any) => {
      const data = event.data;

      // --- Existing message handling logic (mostly unchanged) ---
      if (data === 'juniorit-vscode-reply') {
        if (notifier != null) {
          clearInterval(notifier);
          notifier = null;
        }
        return;
      }

      if (data.sender && data.sender == 'vscode-juniorit-pad') {
        if (data.type == 'keydown_event') {
          window.parent.postMessage(data.data, '*')
        } else if (data.type == 'contextMenuClick_event') {
          const iframe = document.getElementById(data.frameId);
          if (!iframe) return;
          setMenuFrameId(data.frameId);
          const left = iframe.getBoundingClientRect().left;
          const top = iframe.getBoundingClientRect().top;
          setMenuAnchorPoint({ x: left + data.pageX, y: top + data.pageY });
          setMenuOpen(true);
        }
        return;
      }

      // --- Handle Connection Status Response ---
      if (data.type === 'connection-status') {
        if (checkingTimeoutRef.current) {
          clearTimeout(checkingTimeoutRef.current);
          checkingTimeoutRef.current = null;
        }
        setIsConnected(data.connected === true);
        setIsCheckingConnection(false);
        return;
      }

      if (!data.sender || data.sender != 'vscode-juniorit') {
        return;
      }

      // --- Paste Logic (Unchanged) ---
      if (data.pasteText !== undefined) {
         if (data.targetFrame !== undefined) {
          const iframe: any = document.getElementById(data.targetFrame);
          iframe?.contentWindow.postMessage({ ...data, type: 'pasteText' }, '*');
          return;
        }

        var selection = window.getSelection();
        if (!selection) return;

        var range = selection.getRangeAt(0);

        if (!isEditor(range.commonAncestorContainer)) {
          return;
        }
        var textNode = document.createTextNode(data.pasteText);
        range.deleteContents();
        range.insertNode(textNode);
        range.setStartAfter(textNode);
        range.setEndAfter(textNode);
        selection.removeAllRanges();
        selection.addRange(range);
        return;
      }

      // --- Language Detection (Unchanged) ---
      const codeLangs = ['dart', 'flutter', 'javascript', 'typescript', 'react', 'python',
        'php', 'swift', 'java', 'kotlin', 'c', 'c++', 'objective-c', 'go', 'rust']

      let lang: string = getLangFromExt(data.fileExt)

      if (data.code?.includes("package:flutter/")) {
        lang = "flutter";
      } else if (data.code?.match(/from\s+('|")react('|")/)) {
        lang = "react";
      }

      // --- *** UPDATE: Set Active Tab based on command *** ---
      if (data.command == 'complete' || data.command == 'fix' || data.command == 'execute') {
         if (!codeLangs.includes(lang)) lang = 'javascript'

         setCode(data.command === 'execute' ? data.code : removeCustomComments(data.code))
         setCodeLang(lang)
         setCodeAction(data.command === 'execute' ? 'run' : data.command) // complete, fix, run
         codeKeyValueRef.current++
         if(codeLangSelectRef.current) codeLangSelectRef.current.value = lang; // Update dropdown
         setActiveTab('execute'); // <-- Set Execute tab active

      } else if (data.command == 'translate') {
        if (!['dart', 'flutter', 'html', 'javascript', 'typescript', 'tsx', 'rn', 'python', 'php', 'swift', 'java', 'kotlin', 'c', 'c++', 'objective-c', 'go', 'rust'].includes(lang)) {
          lang = 'natural'
        }

        setTranslateCode(removeCustomComments(data.code))
        setTranslateLang(lang)
        translateKeyValueRef.current++
        if(translateLangSelectRef.current) translateLangSelectRef.current.value = lang; // Update dropdown
        setActiveTab('translate'); // <-- Set Translate tab active

      } else if (data.command == 'inline' || data.command == 'enter') {
        // --- Inline/Enter logic (Passes output language) ---
        let start_line = data.start_line
        let end_line = data.end_line
        let code = data.code
        let reference = data.reference
        let action = data.action
        let payload = null
        let error = null

        if(reference) {
          reference = removeCustomComments(reference)
        }
        code = removeCustomComments(code)

        try {
          const response = await axios({
            method: 'post',
            url: process.env.NEXT_PUBLIC_CODES_API + '/rest/inline-code',
            headers: { 'Content-Type': 'application/json' },
             // Pass output language for inline actions as well
            data: { action, lang, code, reference, output_language: outputLanguage }
          });
          payload = response.data.payload
          error = response.data.error
        } catch (err) {
          console.log(err);
          error = 'ERR'
        }
        const eventObj = {
          type: 'response', command: data.command, action, lang, code, payload, error, start_line, end_line
        }
        window.parent.postMessage(eventObj, '*')
        // No tab change for inline/enter

      } else { // Default case (likely assistant related)
        if (!['dart', 'flutter', 'html', 'javascript', 'typescript', 'tsx', 'rn', 'python', 'php', 'swift', 'java', 'kotlin', 'c', 'c++', 'objective-c', 'go', 'rust'].includes(lang)) {
          lang = 'any'
        }

        const prompt = new RegExp(/(\/\/|#)\s*(todo|update|edit|fix|please|pls)/i).test(data.code) ?
        "Please complete the code below according to the requirements specified in the comments: \n\n" + data.code
        :
        "Can you explain the code below? As I can not understand it: \n\n" + data.code

        setAssistantLang(lang)
        setAssistantText(prompt)
        assistantKeyValueRef.current++
        setActiveTab('assistant'); // <-- Set Assistant tab active
      }
    }

    window.addEventListener('message', onMessage);

    // --- Keydown and Context Menu Logic (Unchanged) ---
    const onKeydown = (e: any) => {
       if (!(e.metaKey || e.ctrlKey) || !(e.key == 'c' || e.key == 'v' || e.key == 'x')) {
        return;
      }
      e.preventDefault()
      var range;
      if (e.key == 'x') {
        var selection = window.getSelection();
        if (!selection) return;
        range = selection.getRangeAt(0);
        if (!isEditor(range.commonAncestorContainer)) {
          return;
        }
        selection.removeAllRanges();
        selection.addRange(range);
      }
      const obj = {
        altKey: e.altKey, code: e.code, ctrlKey: e.ctrlKey, isComposing: e.isComposing,
        key: e.key == 'x' ? 'c' : e.key, location: e.location, metaKey: e.metaKey,
        repeat: e.repeat, shiftKey: e.shiftKey, userAgent: navigator.userAgent,
        selectedText: window.getSelection()?.toString()
      }
      window.parent.postMessage(obj, '*')
      if (e.key == 'x' && range) {
        range.deleteContents();
      }
    }

    function contextMenuClick(event: any) {
      event.preventDefault();
      setMenuFrameId('');
      setMenuAnchorPoint({ x: event.clientX, y: event.clientY });
      setMenuOpen(true);
    }

    let isVSCode = false;
    if (location.href.indexOf('vscode-extension') > 0 && location.href.indexOf('version=') > 0) {
      window.addEventListener('keydown', onKeydown);
      window.addEventListener('contextmenu', contextMenuClick);
      isVSCode = true;
    }

    // --- Ready message logic (Unchanged) ---
    window.parent.postMessage('juniorit-embedded-vscode-page-ready', "*");
    notifier = setInterval(() => {
      window.parent.postMessage('juniorit-embedded-vscode-page-ready', "*");
    }, 1000);

    // --- Cleanup (Unchanged) ---
    return () => {
      if (notifier != null) {
        clearInterval(notifier);
        notifier = null;
      }
      window.removeEventListener('message', onMessage);
      window.removeEventListener('contextmenu', contextMenuClick);
      if (isVSCode) {
        window.removeEventListener('keydown', onKeydown);
      }
    }
    // --- Effect Dependencies (Kept empty as per original logic) ---
  }, [])

  // --- Render ---
  return (
    <div className='w-full'>
      <Head>
        <title>SKill-Pilot.AI - Assistant of VS Code</title>
      </Head>

      <div>
        <div className='mx-auto px-2 max-w-4xl '>
          {/* --- Header --- */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, marginBottom: 10 }}>
            <img className="h-12" src="/images/skill-pilot-2.png" alt="Logo"/>

            {/* --- LLM Provider Selector and Loading Indicator --- */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <select
                value={llmProvider || ''}
                onChange={(e) => {
                  if (!e.target.value) return;
                  setLlmProvider(e.target.value);
                  setSelectedProvider(e.target.value);
                }}
                className="llm-provider-select"
                style={{
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  fontSize: '0.9rem',
                  backgroundColor: '#fff',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {llmProviders.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>

              {/* LLM Status Indicator */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  cursor: llmRunning ? 'pointer' : 'default',
                }}
                onClick={() => {
                  if (llmRunning) handleStopLlm();
                }}
                title={llmRunning ? "Click to stop LLM" : "LLM Idle"}
              >
                {llmRunning ? (
                  <>
                    <div className="spinner" style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid #f3f3f3',
                      borderTop: '2px solid #3498db',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite',
                    }}></div>
                    <span style={{ fontSize: '0.85rem', color: '#e74c3c' }}>Stop</span>
                  </>
                ) : (
                  <span style={{ fontSize: '0.85rem', color: '#95a5a6' }}>⚡ Idle</span>
                )}
              </div>

              {/* Connection Status Indicator */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  cursor: !isConnected && !isCheckingConnection ? 'pointer' : 'default',
                  padding: '4px 8px',
                  borderRadius: '4px',
                }}
                onClick={() => {
                  if (!isConnected && !isCheckingConnection) {
                    handleReconnect();
                  }
                }}
                title={
                  isCheckingConnection
                    ? "Checking connection..."
                    : isConnected
                      ? "Connected to server"
                      : "Disconnected - Click to reconnect"
                }
              >
                {isCheckingConnection ? (
                  <>
                    <div className="spinner" style={{
                      width: '12px',
                      height: '12px',
                      border: '2px solid #f3f3f3',
                      borderTop: '2px solid #3498db',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite',
                    }}></div>
                    <span style={{ fontSize: '0.7rem', color: '#6c757d' }}>Checking</span>
                  </>
                ) : isConnected ? (
                  <>
                    <span style={{ fontSize: '1rem', color: '#28a745' }}>●</span>
                    <span style={{ fontSize: '0.7rem', color: '#155724' }}>Connected</span>
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: '1rem', color: '#dc3545' }}>●</span>
                    <span style={{ fontSize: '0.7rem', color: '#721c24' }}>Disconnected</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* --- Context Menu (Unchanged) --- */}
          <ControlledMenu
            anchorPoint={menuAnchorPoint}
            state={isMenuOpen ? 'open' : 'closed'}
            direction="right"
            onClose={() => setMenuOpen(false)}
          >
             <MenuItem onClick={(e) => {
              if (menuFrameId) {
                const iframe: any = document.getElementById(menuFrameId);
                iframe?.contentWindow.postMessage({ type: 'cutText' }, '*');
                return;
              }
              var selection = window.getSelection();
              if (!selection) return;
              var range = selection.getRangeAt(0);
              if (!isEditor(range.commonAncestorContainer)) return;
              selection.removeAllRanges();
              selection.addRange(range);
              const obj = {
                altKey: false, code: '', ctrlKey: true, isComposing: false, key: 'c',
                location: null, metaKey: true, repeat: false, shiftKey: false,
                userAgent: navigator.userAgent, contextMenu: true, selectedText: window.getSelection()?.toString()
              }
              window.parent.postMessage(obj, '*')
              range.deleteContents();
            }}>Cut</MenuItem>
             <MenuItem onClick={(e) => {
              if (menuFrameId) {
                const iframe: any = document.getElementById(menuFrameId);
                iframe?.contentWindow.postMessage({ type: 'copyText' }, '*');
                return;
              }
              const obj = {
                altKey: false, code: '', ctrlKey: true, isComposing: false, key: 'c',
                location: null, metaKey: true, repeat: false, shiftKey: false,
                userAgent: navigator.userAgent, contextMenu: true, selectedText: window.getSelection()?.toString()
              }
              window.parent.postMessage(obj, '*')
            }}>Copy</MenuItem>
             <MenuItem onClick={(e) => {
              const obj: any = {
                altKey: false, code: '', ctrlKey: true, isComposing: false, key: 'v',
                location: null, metaKey: true, repeat: false, shiftKey: false,
                userAgent: navigator.userAgent, contextMenu: true, selectedText: window.getSelection()?.toString()
              }
              if (menuFrameId) obj.frameId = menuFrameId
              window.parent.postMessage(obj, '*')
            }}>Paste</MenuItem>
          </ControlledMenu>

          {/* --- *** Tab Navigation *** --- */}
          <div className="tabs-container">
            <button
              className={`tab-button ${activeTab === 'assistant' ? 'active' : ''}`}
              onClick={() => setActiveTab('assistant')}
            >
              Assistant
            </button>
            <button
              className={`tab-button ${activeTab === 'execute' ? 'active' : ''}`}
              onClick={() => setActiveTab('execute')}
            >
              Execute
            </button>
            <button
              className={`tab-button ${activeTab === 'translate' ? 'active' : ''}`}
              onClick={() => setActiveTab('translate')}
            >
              Translate
            </button>
          </div>

          {/* --- *** Tab Content *** --- */}
          <div className='prose max-w-none tab-content'>

            {/* --- Assistant Panel --- */}
            {activeTab === 'assistant' && (
              <div className="tab-panel">
                 {/* --- Updated Meta Prop --- */}
                <ChatBlock key={`assistant-key-${assistantKeyValueRef.current}`} lang={assistantLang} meta={`{"show_vibe_learning": true, "output_language": "${outputLanguage}" }`} codes={assistantText} />
              </div>
            )}

            {/* --- Execute Panel --- */}
            {activeTab === 'execute' && (
              <div className="tab-panel">
                <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', borderBottom: '0px solid gray', marginBottom: 10 }}>
                  <select
                    ref={codeLangSelectRef}
                    value={codeLang} // Controlled component
                    onChange={(e) => {
                       codeKeyValueRef.current++ // Force re-render of CodeBlock if needed
                       setCodeLang(e.target.value)
                    }}
                    className="language-select" // Added class for potential styling
                  >
                    <option value="dart">Dart</option>
                    <option value="flutter">Flutter</option>
                    <option value="javascript">JavaScript</option>
                    <option value="typescript">TypeScript</option>
                    <option value="react">React</option>
                    <option value="python">Python</option>
                    <option value="php">PHP</option>
                    <option value="kotlin">Kotlin</option>
                    <option value="java">Java</option>
                    <option value="swift">Swift</option>
                    <option value="objective-c">Objective-C</option>
                    <option value="c">C</option>
                    <option value="c++">C++</option>
                    <option value="go">Golang</option>
                    <option value="rust">Rust</option>
                  </select>
                </div>
                {/* --- Updated Meta Prop --- */}
                <CodeBlock key={`code-key-${codeKeyValueRef.current}`} lang={codeLang} meta={`{ "action": "${codeAction}", "output_language": "${outputLanguage}" }`} codes={code} />
              </div>
            )}

            {/* --- Translate Panel --- */}
            {activeTab === 'translate' && (
              <div className="tab-panel">
                <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', borderBottom: '0px solid gray', marginBottom: 10 }}>
                  <select
                    ref={translateLangSelectRef}
                    value={translateLang} // Controlled component
                    onChange={(e) => {
                       setTranslateLang(e.target.value)
                    }}
                    className="language-select" // Added class for potential styling
                  >
                    <option value="natural">Natural</option>
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
                    <option value="c++">C++</option>
                    <option value="objective-c">Objective-C</option>
                    <option value="go">Golang</option>
                    <option value="rust">Rust</option>
                  </select>
                </div>
                {/* --- Updated Meta Prop --- */}
                <ChatBlock key={`translate-key-${translateKeyValueRef.current}`} lang={translateLang} meta={`{ "action": "translate", "output_language": "${outputLanguage}" }`} codes={translateCode} />
              </div>
            )}

          </div> {/* End prose / tab-content */}

        </div> {/* End container */}
      </div>

      {/* --- Styles (Includes styles for new elements) --- */}
      <style jsx>{`
        .error-message {
          color: red;
          font-size: 12px;
        }
        .result-message {
          color: green;
          font-size: 12px;
        }

        /* General select styling */
        select.language-select { /* Target selects more specifically */
          border: 1px solid #ccc; /* Subtle border */
          outline: none;
          background-color: #fff; /* White background */
          color: black;
          box-shadow: none;
          padding: 6px 2rem 6px 0.5rem; /* Adjust padding */
          text-align-last: left;
          margin-bottom: 0.5em;
          font-size: 0.9rem; /* Slightly smaller font */
          cursor: pointer;
          border-radius: 4px; /* Rounded corners */
          -webkit-appearance: none; /* Remove default arrow */
          -moz-appearance: none;
          appearance: none;
          /* Add custom arrow */
          background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007bff%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E');
          background-repeat: no-repeat, repeat;
          background-position: right .7em top 50%, 0 0;
          background-size: .65em auto, 100%;
        }

        select.language-select:focus {
          outline: none;
          border-color: blue; /* Highlight on focus */
        }

        .tabs-container {
          display: flex;
          flex-wrap: wrap; /* Allow tabs to wrap on smaller screens */
          border-bottom: 1px solid #ccc;
          margin-bottom: 1rem; /* Space below tabs */
        }

        .tab-button {
          padding: 10px 15px;
          cursor: pointer;
          border: none;
          background-color: transparent;
          border-bottom: 3px solid transparent; /* For active indicator */
          margin-bottom: -1px; /* Overlap border */
          font-size: 1rem;
          color: #555; /* Dim inactive tabs */
          transition: all 0.2s ease-in-out;
          white-space: nowrap; /* Prevent wrapping within button */
        }

        .tab-button:hover {
          color: #000;
           background-color: #f0f0f0; /* Slight hover effect */
        }

        .tab-button.active {
          border-bottom: 3px solid blue; /* Active indicator color */
          color: #000; /* Make active tab text darker */
          font-weight: bold;
        }

        .tab-content {
          padding-top: 1rem; /* Add some space above tab content */
        }

        .tab-panel {
           /* Styles specific to each panel container if necessary */
        }

        /* Ensure prose styles don't interfere badly with select */
        .prose select.language-select {
            margin-top: 0;
            margin-bottom: 0.5em; /* Keep consistent margin */
        }
        .prose label {
            margin-bottom: 0.5em; /* Consistent margin for label */
            font-size: 1rem; /* Match surrounding text if needed */
            font-weight: normal; /* Override potential prose bolding */
            color: initial; /* Override potential prose colors */
            margin-top: 0; /* Override potential prose margins */
        }
        .prose p {
            margin-top: 0.5em; /* Adjust paragraph spacing if needed */
            margin-bottom: 0.5em;
        }

        /* Spinner animation */
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// --- getStaticProps ---
export const getStaticProps = async (context: GetStaticPropsContext) => {

  let email = null
  let jwt = null

  return {
    props: {
      email, jwt, ...(await serverSideTranslations(context.locale ?? 'en', [
        'common',
      ]))
    }
  }
};

export default EmbeddedVSCodeExtension;
