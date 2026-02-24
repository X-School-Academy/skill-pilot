import React, { useEffect, useRef, useState, memo } from 'react';
import yaml from 'js-yaml';
import RJSON from 'relaxed-json';
import logger from '../../libs/logger';
import ChatBlock from './chat.block';
import { HandRaisedIcon } from '@heroicons/react/24/solid'

/*
- Basic computer knowledge#:
   - What are the main components of a computer?#
   - How do hardware and software work together?
   - What are the basic functions of an operating system?

- History of programming languages#:
   - What are the key milestones in the history of programming languages?#
   - What are the main categories of programming languages?
   - How has the evolution of programming languages shaped the software development landscape?
*/

const Text = (props: any) => {
   const ref = useRef<any>(null)
   let ret = props.children.match(/#([a-z]{0,10})$/)
   if(ret) {
      return <>
         {props.children.slice(0, -(ret[1].length + 1))}
         <HandRaisedIcon title='Ask AI Now' ref={ref} className="w-5 h-5 ml-3 hover:opacity-80 cursor-pointer inline select-none" style={{color: props.index == props.showChatIndex?'#373c93':'gray', margin: '0 0 0 10px'}} onClick={() => {
            if(props.index == props.showChatIndex) {
               ref.current!.style.color = 'gray'
               props.setShowChatIndex(null)
            } else {
               ref.current!.style.color = '#373c93'
               props.setShowChatIndex(props.index)
            }
         }}></HandRaisedIcon>
         {props.index == props.showChatIndex && <ChatBlock lang={ret[1]??'any'} meta='{extraInfo: false}' codes={props.children.slice(0, -(ret[1].length + 1))}></ChatBlock>}
      </>
   } else {
      return <>
         {props.children}
         {props.meta.default && <>
            <HandRaisedIcon title='Ask AI Now' ref={ref} className="w-5 h-5 ml-3 hover:opacity-80 cursor-pointer inline select-none" style={{color: props.index == props.showChatIndex?'#373c93':'gray', margin: '0 0 0 10px'}} onClick={() => {
               if(props.index == props.showChatIndex) {
                  ref.current!.style.color = 'gray'
                  props.setShowChatIndex(null)
               } else {
                  ref.current!.style.color = '#373c93'
                  props.setShowChatIndex(props.index)
               }
            }}></HandRaisedIcon>
            {props.index == props.showChatIndex && <ChatBlock lang={'any'} meta='{extraInfo: false}' codes={props.children}></ChatBlock>}
         </>}
      </>
   }
}

const ListItem = (props: any) => {

   // check if props.children is javascript object
   if(typeof props.children === 'object') {
      return<li>
            <Text index={props.index + "_"} meta={props.meta} showChatIndex={props.showChatIndex} setShowChatIndex={props.setShowChatIndex}>{Object.keys(props.children)[0]}</Text>
            <ul>
            {(Object.values(props.children) as Array<any>)[0].map((key: any, index: number) => {
               return <li key={index}>
                     <Text index={props.index + "_" + index} meta={props.meta} showChatIndex={props.showChatIndex} setShowChatIndex={props.setShowChatIndex}>{key}</Text>
                  </li>
            })}
         </ul>
      </li> 
   } else {
      return <li><Text index={props.index + "_"} meta={props.meta} showChatIndex={props.showChatIndex} setShowChatIndex={props.setShowChatIndex} >{props.children}</Text></li>
   }
}


const  ListBLock  =  (props: any)   =>   {
    const callbackRef = useRef(false);

    const [showChatIndex, setShowChatIndex] = useState(null)

    let meta: any = {default: false}
    try {
      meta = RJSON.parse(props.meta ?? "{}")
    } catch (e: any) {
      logger.error(e.message)
    }

    const elementList: any = yaml.load(props.yml)

    useEffect(() => {
      const init = async () => {

          if (props.callback) {
              if(callbackRef.current) return
              callbackRef.current = true
              props.callback(props.index, 1)
          }
      }
      init()
  }, [])

    return <>
      {meta.tag == 'ol' ?
      <ol>
            {elementList.map((element: any, index: number) => {
               return <ListItem key={index} index={index} showChatIndex={showChatIndex} meta={meta} setShowChatIndex={setShowChatIndex}>{element}</ListItem>
            })}
      </ol>
      :
      <ul>
            {elementList.map((element: any, index: number) => {
               return <ListItem key={index} index={index} showChatIndex={showChatIndex} meta={meta} setShowChatIndex={setShowChatIndex}>{element}</ListItem>
            })}
      </ul>
      }
    </>
}

export default memo(ListBLock)