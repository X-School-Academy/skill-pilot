import React, { useState, memo, useEffect, useRef } from "react";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkStringify from 'remark-stringify';
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import CodeMirrorBlock from "./codemirror.block";
import FormBlock from "./form.block";
import ListBLock from "./list.block";
import RJSON from 'relaxed-json'
import ChatBlock from './chat.block';
import CodeBlock from './code.block';
import CodeTabsBlock from './CodeTabs.block';
import { OnlineCourseEventCallback } from "../../types/online-course";
import { VideoCameraIcon } from "@heroicons/react/24/solid";
import gfm from 'remark-gfm';
import MermaidChart from './MermaidChart'
import TikzPicture from './TikzPicture'
import plantumlEncoder from 'plantuml-encoder'

const extractText = (children:any): any => {
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

// [0:10-0:30](v=2gT74fLQ3tg)
const YoutubePIPPlayer = (props:any) => {

  const [isPlaying, setIsPlaying] = useState(false)


  const videoID = props.href.substring(2)

  let url = `/video-player/${videoID}`

  let text = extractText(props.children)
  let label = ''

  if(text.indexOf('|') > 0) {
    text = text.split('|')[0]
    label = text.split('|')[1]
  }

  if(text.match(/[0-9\:\-]{7,}/)) {
    const startStr  = text.split("-")[0]
    const endStr  = text.split("-")[1]

    const startFrom  = Number.parseInt(startStr.split(":")[0]) * 60 + Number.parseInt(startStr.split(":")[1])
    const endTo  =  Number.parseInt(endStr.split(":")[0]) * 60 + Number.parseInt(endStr.split(":")[1])

    url = `/video-player/${videoID}/${startFrom}/${endTo}`
  } else {
    if(!label) label = text
  }


   // https://mdn.github.io/dom-examples/document-picture-in-picture/
  const click = async (event:any) => {

    if (!("documentPictureInPicture" in window)) return true

    event.preventDefault()

    if(isPlaying) {
      setIsPlaying(false)
      // @ts-ignore
      if(window.documentPictureInPicture.window) window.documentPictureInPicture.window.close();
    } else {
      setIsPlaying(true)

      // @ts-ignore
      if(window.documentPictureInPicture.window) window.documentPictureInPicture.window.close();

      // Returns null if no pip window is currently open
      // @ts-ignore 
      if (!window.documentPictureInPicture.window) {
        const width = screen.width > 2220 ? 1920 : (screen.width - 300)
        const height = Math.round(width * 1080.0/1920)
        // Open a Picture-in-Picture window.
        // @ts-ignore 
        const pipWindow = await window.documentPictureInPicture.requestWindow({
          width,
          height
        });
        
        pipWindow.document.body.style.margin = '0px'
        pipWindow.document.body.innerHTML = `<iframe style="border: none; height: 100vh; width: 100vw;" src="${url}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>`

        // Add pagehide listener to handle the case of the pip window being closed using the browser X button
        pipWindow.addEventListener("pagehide", (event:any) => {
          setIsPlaying(false)
        });

      } else {
        console.log("never happen here")
      }
      
    }
  }


  useEffect(()=> {
    if (!("documentPictureInPicture" in window)) return

    const onEnter = () => {

    }
    // @ts-ignore 
    documentPictureInPicture.addEventListener("enter", onEnter)

    return ()=>{
      // @ts-ignore 
      documentPictureInPicture.removeEventListener("enter", onEnter)
    }

  }, [])

  return <>
      <a href={url} onClick={click} target={props.target}><VideoCameraIcon className="w-6 h-6 inline mx-2 text-primary-blue opacity-80" /></a>
      { label && <a href={url} onClick={click} target={props.target}>
          {label} 
      </a>}
  </>
}

const renderLink = (props:any) => {
  if(props.href.indexOf("v=") == 0) return YoutubePIPPlayer(props)

  const isYouTubeLink = props.href.includes('youtube') ||  props.href.includes('youtu');
  return (<>
      <a href={props.href} target={props.target}>
          {props.children} 
      </a> 
      {isYouTubeLink && <a href={props.href} target={props.target}><VideoCameraIcon className="w-6 h-6 inline mx-2 text-primary-blue opacity-80" /></a>} 
      </>
  );
};

interface CodeBlockProps extends OnlineCourseEventCallback {
  codes: string;
  lang: string;
  meta: string;
  readOnly?: boolean
  noActions?: boolean
}

const CodeMirror = ({ 
  lang, 
  meta, 
  codes, 
  readOnly, 
  noActions,
  taskId,
  onlineCourseSessionId,
  onDocChanged,
  onSubmit,
  onError,
  onReset,
 }: CodeBlockProps) => {
  const [value, setValue] = useState(codes);

  return (
    <div>
      <CodeMirrorBlock 
      codes={value} 
      lang={lang} 
      meta={meta} 
      readOnly={readOnly} 
      noActions={noActions} 
      taskId={taskId}
      onlineCourseSessionId={onlineCourseSessionId}
      onDocChanged={onDocChanged} 
      onSubmit={onSubmit}
      onError={onError}
      onReset={onReset}
      />
    </div>
  );
};

interface Props extends OnlineCourseEventCallback {
  markdown: string;
  lang?: string
  meta?: string
  readOnly?: boolean
  noActions?: boolean
  linkTarget?:string
}

const preprocessLaTeX = (content: string) => {
  // Replace block-level LaTeX delimiters \[ \] with \\[ \\]

  const blockProcessedContent = content.replace(
    /\\\[(.*?)\\\]/gs,
    (_, equation) => `\\\\[${equation}\\\\]`,
  );

  // Replace inline LaTeX delimiters \( \) with \\( \\)
  const inlineProcessedContent = blockProcessedContent.replace(
    /\\\((.*?)\\\)/gs,
    (_, equation) => `\\\\(${equation}\\\\)`,
  );
  return inlineProcessedContent;
};

export const Markdown = ({ children, ...props }: any) => {
  const processedCode = preprocessLaTeX(children);

  useEffect(() => {
      if (window.MathJax?.typeset) {
        //window.MathJax.typesetClear()
        window.MathJax.typeset()
      }
  }, [children]); 

  return <ReactMarkdown remarkPlugins={[gfm]} {...props}>{processedCode.replaceAll("\\```", "```")}</ReactMarkdown>
};


const MarkdownRenderer = ({ 
  markdown, 
  lang, 
  meta, 
  readOnly, 
  noActions,
  linkTarget,
  taskId,
  onlineCourseSessionId,
  onDocChanged,
  onSubmit,
  onError,
  onReset, 
}: Props) => {
  // parse the markdown into an abstract syntax tree (AST)
  const ast = unified().use(remarkParse).parse(preprocessLaTeX(markdown));

  return (
    <div className="w-full">
      {ast.children.map((node, index) => {
        if (node.type === "code") {

          if (meta && !node.meta) node.meta = meta
          if (lang && !node.lang) node.lang = lang

          if (node.lang == 'yml-form') {
            return <FormBlock key={index} yml={node.value} onSubmit={()=>{}} />
          }

          /*
          for math https://github.com/remarkjs/remark-math/tree/main?tab=readme-ov-file#example-katex
          import rehypeKatex from 'rehype-katex'
          import remarkMath from 'remark-math'

          ChatGPT uses LaTeX by default for mathematical notation
          for geometric shapes: https://github.com/ezhomelabs/tikzjax 

          sudo apt-get install texlive texlive-pictures texlive-latex-extra --no-install-recommends
          or
          https://github.com/ezhomelabs/node-tikzjax
          
          **TikZ** is a package that is part of the larger **LaTeX** typesetting system. The relationship between TikZ and LaTeX is as follows:

          - **LaTeX** is a high-quality typesetting system that is widely used in academia and technical publishing for creating documents. It is based on the TeX typesetting engine developed by Donald Knuth.

          - **TikZ** (short for "TikZ ist kein Zeichenprogramm", which is German for "TikZ is not a drawing program") is a package that extends the capabilities of LaTeX by providing a sophisticated and powerful way to create vector graphics and diagrams directly within LaTeX documents.

          - TikZ is written using the LaTeX macro language, which means that it is essentially a set of macros and commands that are interpreted by the LaTeX engine.

          - To use TikZ, you need to have a LaTeX installation and include the `\usepackage{tikz}` command in the preamble of your LaTeX document. This loads the TikZ package and makes its commands available for use.

          - Within the LaTeX document, you can then use the TikZ environment (`\begin{tikzpicture} ... \end{tikzpicture}`) and its associated commands to define and draw various geometric shapes, create plots, build diagrams, and more.

          - The code for the graphics is written using a descriptive syntax, where you specify the shapes, their positions, styles, and transformations using TikZ commands and coordinates.

          - When the LaTeX document is compiled, the TikZ code is processed, and the resulting graphics are rendered and included in the output (typically a PDF file).

          In summary, TikZ is a powerful package that seamlessly integrates with LaTeX, allowing users to create high-quality vector graphics and diagrams directly within their LaTeX documents using a code-based approach. It leverages the strengths of the LaTeX typesetting system while providing a rich set of tools for creating and customizing graphics.

          */

          if (node.lang == 'plantuml') {
            const encoded = plantumlEncoder.encode(node.value);
            return <img key={index} src={`${process.env.PLANTUML_SERVER_API??'https://www.plantuml.com/plantuml/svg/'}${encoded}`}/>
          }

          if (node.lang == 'mermaid') {
            //const encoded = encodeURI(node.value);
            //return <img src={`${process.env.MERMAID_SERVER_API}${encoded}`}/>
            return <MermaidChart key={index} chart={node.value}></MermaidChart>
          }

          if (node.lang?.toLowerCase() == 'latex') { // LaTeX or latex,  only support tikzpicture for now
            return <TikzPicture key={index} code={node.value}></TikzPicture>
          }

          if (node.lang == 'yml-list') {
            return <ListBLock key={index} meta={node.meta ?? "{}"} yml={node.value} />
          }

          if(node.lang == 'tabs') {
            return <CodeTabsBlock key={index} content={node.value} meta={node.meta ?? "{}"}></CodeTabsBlock>
          }

          let metaData: any = {}

          try {
              metaData = RJSON.parse(node.meta ?? "{}")
          } catch(e:any) {
            console.error(e.message)
          }

          if (node.lang == 'yaml' && metaData.type == 'form') {
            return <FormBlock key={index} yml={node.value} onSubmit={()=>{}} />
          }

          if (metaData.type == 'chat') {
            return <ChatBlock 
                    key={index} 
                    codes={node.value} 
                    lang={node.lang ?? 'markdown'} 
                    meta={node.meta ?? "{}"} 
                    taskId={taskId}
                    onlineCourseSessionId={onlineCourseSessionId}
                    onDocChanged={onDocChanged}
                    onSubmit={onSubmit}
                    onError={onError}
                    onReset={onReset}
                    />
          } else if (metaData.type == 'code') {
            if(node.lang == 'jsx') node.lang = 'react'
            return <CodeBlock 
                    key={index} 
                    codes={node.value} 
                    lang={node.lang ?? "any"} 
                    meta={node.meta ?? "{}"} 
                    taskId={taskId}
                    onlineCourseSessionId={onlineCourseSessionId}
                    onDocChanged={onDocChanged}
                    onSubmit={onSubmit}
                    onError={onError}
                    onReset={onReset}
                  />
          } else if (node.lang && node.meta) {
            return (
              <CodeMirror
                key={index}
                lang={node.lang}
                meta={node.meta}
                codes={node.value}
                readOnly={readOnly}
                noActions={noActions}
                taskId={taskId}
                onlineCourseSessionId={onlineCourseSessionId}
                onDocChanged={onDocChanged}
                onSubmit={onSubmit}
                onError={onError}
                onReset={onReset}
              />
            );
          } else {
            const othernode: string = unified().use(remarkStringify).stringify({ type: 'root', children: [node] })
            return <ReactMarkdown components={{ a: renderLink }} linkTarget={linkTarget || '_self'} key={index} remarkPlugins={[gfm]} children={othernode}></ReactMarkdown>
          }
        } else {
          const othernode: string = unified().use(remarkStringify).stringify({ type: 'root', children: [node] })
          return<ReactMarkdown components={{ a: renderLink }} linkTarget={linkTarget || '_self'} key={index} rehypePlugins={[rehypeRaw]} remarkPlugins={[gfm]} children={othernode}></ReactMarkdown>
        }
      })}
    </div>
  );
};

export default memo(MarkdownRenderer);
