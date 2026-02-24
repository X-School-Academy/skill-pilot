import React, { useEffect, useRef, useState, memo } from 'react'
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import CodeBlock from './code.block';
import RJSON from 'relaxed-json';
import MarkdownRenderer from './MarkdownRenderer';


const CodeTabsBlock = (props: any) => {
  const callbackRef = useRef(false);
  const self = useRef<HTMLDivElement>(null);

  let content = props.content;
  content = content.replaceAll('\\```', '```').replaceAll('\\`\\`\\`', '```')

  const ast = unified().use(remarkParse).parse(content);

  let tabsMetaData: any = {}

  try{
    if (props.meta) tabsMetaData = RJSON.parse(props.meta ?? "{}")
  } catch(e:any) {
    console.error(e.message)
  }

  useEffect(() => {
    let isDown = false;
    let startX: number;
    let scrollLeft: number;

    const onMouseDown = (e: MouseEvent) => {
      isDown = true;
      startX = e.pageX - (element?.offsetLeft ?? 0);
      scrollLeft = element?.scrollLeft ?? 0;
    };

    const onMouseLeave = () => {
      isDown = false;
    };

    const onMouseUp = () => {
      isDown = false;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDown) return;
      e.preventDefault();
      const x = e.pageX - (element?.offsetLeft ?? 0);
      const walk = (x - startX) * 3; // 3 is the scroll-speed
      if (element) {
        element.scrollLeft = scrollLeft - walk;
      }
    };

    if(!self.current) return

    const element = self.current.querySelector<HTMLElement>('.react-tabs ul');
    if (element) {
      element.addEventListener('mousedown', onMouseDown);
      element.addEventListener('mouseleave', onMouseLeave);
      element.addEventListener('mouseup', onMouseUp);
      element.addEventListener('mousemove', onMouseMove);
    }

    return () => {
      if (element) {
        element.removeEventListener('mousedown', onMouseDown);
        element.removeEventListener('mouseleave', onMouseLeave);
        element.removeEventListener('mouseup', onMouseUp);
        element.removeEventListener('mousemove', onMouseMove);
      }
    };
  }, []);

  useEffect(() => {
    if (props.callback) {
      if (callbackRef.current) return
      callbackRef.current = true
      props.callback(props.index, 1)
    }
  }, [])

  return <div ref={self}>
    <Tabs>
      <TabList className="whitespace-nowrap overflow-scroll md:whitespace-normal md:overflow-visible border-b border-gray-500">
        {ast.children.map((node: any, index) => {
          let metaData: any = {}
          try {
            if (node.meta) {
              metaData = RJSON.parse(node.meta ?? "{}")
            }
          } catch(e:any) {
            console.error(e.message)
          }
          if (node.lang == 'jsx') node.lang = 'react'
          if (!node.lang) node.lang = 'any'
          let title = node.lang.charAt(0).toUpperCase() + node.lang.slice(1);
          if (metaData.title) title = metaData.title;
          if (title == 'Php') title = 'PHP'
          if (title == 'Go') title = 'Golang'

          return <Tab key={index}>{title}</Tab>

        })}
      </TabList>

      {ast.children.map((node: any, index) => {
        if (node.lang == 'jsx') node.lang = 'react'
        let metaData: any = {}
        try {
          if (node.meta) {
            metaData = RJSON.parse(node.meta ?? "{}")
          }
        } catch(e:any) {
          console.error(e.message)
        }
        if (tabsMetaData.rawCode) metaData.rawCode = true
        if (tabsMetaData.minHeight) metaData.minHeight = tabsMetaData.minHeight
        if (tabsMetaData.maxHeight) metaData.maxHeight = tabsMetaData.maxHeight

        let fallbackMarkDownCode;
        if(['plantuml', 'mermaid', 'latex'].includes(node.lang)) {
          fallbackMarkDownCode = `\`\`\`${node.lang}\n${node.value}\n\`\`\``;
        }


        return <TabPanel key={index}>
          {fallbackMarkDownCode ? 
          <MarkdownRenderer key={index} markdown={fallbackMarkDownCode}></MarkdownRenderer>
          :
          <CodeBlock key={index} codes={node.value} lang={node.lang ?? "any"} meta={JSON.stringify(metaData)}></CodeBlock>
          }
        </TabPanel>
      })}

    </Tabs>
  </div>
}

export default memo(CodeTabsBlock)