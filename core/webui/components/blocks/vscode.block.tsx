import React, { useState, useEffect, useRef, memo } from "react"
import sleep from 'sleep-promise'
import RJSON from 'relaxed-json';
import logger from '../../libs/logger';
import { BoltIcon } from '@heroicons/react/24/solid'
import { Markdown } from './MarkdownRenderer';
import ReactDOMServer from 'react-dom/server';

const extractText = (children: any): any => {
  if (typeof children === 'string') {
    return children;
  }
  if (React.Children.count(children) === 0) {
    return '';
  }
  // @ts-ignore
  return React.Children.map(children, child => {
    if (React.isValidElement(child)) {
      // @ts-ignore
      return extractText(child.props.children);
    }
    return child;
  }).join('');
};

const VSCodeBlock = (props: any) => {
  const [content, setContent] = useState<string>('')
  const callbackRef = useRef(false);

  const ref = useRef<HTMLDivElement>(null)

  let meta: any = {}
  try {
    meta = RJSON.parse(props.meta ?? "{}")
  } catch (e: any) {
    logger.error(e.message)
  }

  const renderLink = (linkProps: any) => {
    let text = extractText(linkProps.children)

    if (!text) text = '1:0-1:0'

    // [1:0-12:20](/file)
    const start = text.split('-')[0]
    const end = text.split('-')[1]
    const fromLine = start.split(':')[0]
    const startChar = start.split(':')[1]
    const toLine = end.split(':')[0]
    const endChar = end.split(':')[1]

    return (
      <a href="#" onClick={(e) => {
        e.preventDefault()

        let payload: any = {}
        if (linkProps.href.indexOf('#') == 0) {
          if (linkProps.href == '#close') {
            payload = { type: 'terminal_close_all' }
          } else if (linkProps.href == '#new') {
            payload = { type: 'terminal_new' }
          } else if (linkProps.href == '#focus') {
            payload = { type: 'terminal_focus' }
          } else {
            payload = { type: 'terminal_new', directory: linkProps.href.substring(1) }
          }

        } else {
          payload = { type: 'open_file', file: linkProps.href, fromLine, startChar, toLine, endChar }
        }

        if (props.sendCommand) props.sendCommand(payload)

      }
        // @ts-ignore
      } title="Quick Open" ><BoltIcon className="w-6 h-6 inline mx-2 text-primary-blue opacity-80" /></a>
    );
  };

  const renderLinkWithData = (linkProps: any) => {
    let text = extractText(linkProps.children)

    if (!text) text = '1:0-1:0'

    // [1:0-12:20](/file)
    const start = text.split('-')[0]
    const end = text.split('-')[1]
    const fromLine = start.split(':')[0]
    const startChar = start.split(':')[1]
    const toLine = end.split(':')[0]
    const endChar = end.split(':')[1]

    let payload: any = {}
    if (linkProps.href.indexOf('#') == 0) {
      if (linkProps.href == '#close') {
        payload = { type: 'terminal_close_all' }
      } else if (linkProps.href == '#new') {
        payload = { type: 'terminal_new' }
      } else if (linkProps.href == '#focus') {
        payload = { type: 'terminal_focus' }
      } else {
        payload = { type: 'terminal_new', directory: linkProps.href.substring(1) }
      }

    } else {
      payload = { type: 'open_file', file: linkProps.href, fromLine, startChar, toLine, endChar }
    }

    return (
      <a href={`#${JSON.stringify(payload)}`}>__BoltIcon__</a>
    );
  };

  useEffect(() => {
    const init = async () => {

      setContent(props.content)
      await sleep(1)
      ref.current!.style.opacity = '1'

      if (meta.during) await sleep(meta.during)

      if (props.callback) {
        if (callbackRef.current) return
        callbackRef.current = true
        props.callback(props.index, 1)

        if (meta.vscode && props.sendCommand) {
          // @ts-ignore
          const html = ReactDOMServer.renderToStaticMarkup(<Markdown components={{ a: renderLinkWithData }} children={props.content}></Markdown>)
          const payload = { type: 'right_panel', body: { html, shell: meta.shell }, clear: meta.clear }
          props.sendCommand(payload)
        }
      }
    }
    init()
  }, [])

  return <div ref={ref} style={{ opacity: 0, transition: 'opacity 1s ease-in-out' }}>
    <Markdown components={{ a: renderLink }} children={content}></Markdown>
  </div>
}

export default memo(VSCodeBlock)
