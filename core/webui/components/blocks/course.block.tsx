import React, { useState, useEffect, useRef } from 'react';
import ChatBlock from './chat.block';
import FormBlock from "./form.block";
import ControlBlock from './control.block'
import CodeBlock from './code.block';
import ListBLock from './list.block'
import sleep from "sleep-promise";
import { unified } from "unified";
import remarkParse from "remark-parse";

import RJSON from 'relaxed-json'
import yaml from 'js-yaml';
import BashBlock from './bash.block';
import NotebookBlock from './notebook.block'
import MediaBlock from './media.block'
import VSCodeBlock from './vscode.block'
import ContainerBlock from './container.block'

import MarkdownPlay from './MarkdownPlay.block'
import { AudioResponse } from './AudioResponse.block';
import CodeTabsBlock from './CodeTabs.block';
import SlidesBlock from './Slides.block';
import MemoryCardBlock from './MemoryCard.block';
import { io, Socket } from "socket.io-client";
import axios from "axios";
import { apiUrl, getApiBase } from "../../libs/api-base";

import dynamic from 'next/dynamic';

/*
const LiveChatWindowNoSSR = dynamic(
  () => import('./live-chat-window'),
  { ssr: false }
);
*/

const CourseBlock = (props: any) => {
  const nodeList = unified().use(remarkParse).parse(props.courseData);

  if(props.fromIndex) {
    nodeList.children.splice(1, props.fromIndex) 
  }

  const metaNode: any = nodeList.children[0]
  const courseMeta: any = yaml.load(metaNode.value)

  const [elements, setElements] = useState<any[]>([])
  const [nextIndex, setNextIndex] = useState(Math.max(Number(props.lastStep ?? 1), 1))
  const [localDevToken, setLocalDevToken] = useState<string | null>(null)

  const courseCallbackRef = useRef(false)
  let socketClient = useRef<Socket | null>(null);
  let socketShellResponses = useRef<any>({});
  let socketShellHistory = useRef('');
  let socketContainerStatusPayload = useRef(null);

  let relatedContents = useRef<any>({});
  let testResults = useRef<any>({});

  const emitAssignmentEvent = (payload: any, useVolatile = false) => {
    if (!socketClient.current || !localDevToken) {
      return false
    }
    const enrichedPayload = { ...payload, local_dev_token: localDevToken }
    if (useVolatile) {
      socketClient.current.volatile.emit('assignment_event', enrichedPayload)
    } else {
      socketClient.current.emit('assignment_event', enrichedPayload)
    }
    return true
  }

  // set web_url
  const getGithubPagesUrl = (gitRemoteOutput: string) => {
    // Regular expressions for SSH and HTTPS formats
    const sshRegex = /origin\s+git@github\.com:(\S+)\/(\S+)(\.git)?/;
    const httpsRegex = /origin\s+https:\/\/github\.com\/(\S+)\/(\S+)(\.git)?/;

    let userName, repoName;

    // Check if the remote URL is in SSH format
    let match = sshRegex.exec(gitRemoteOutput);
    if (match) {
        userName = match[1];
        repoName = match[2];
    } else {
        // Check if the remote URL is in HTTPS format
        match = httpsRegex.exec(gitRemoteOutput);
        if (match) {
            userName = match[1];
            repoName = match[2];
        } else {
            return false;
        }
    }

    // Construct GitHub Pages URL
    return `https://${userName}.github.io/${repoName}`;
  }

  const getNode = async (index: number) => {

    const node = nodeList.children[index]
    //console.log('nodeList:',nodeList,'index:',index);

    if(!node) {
      console.error("getNode out of the range!")
      return
    }
    
    if (node.type == 'code') {

      let meta: any = {}

      try {
        if (node.meta) {
          meta = RJSON.parse(node.meta ?? "{}")
        }
      } catch(e:any) {
        console.log("error meta data:", node.meta)
        //console.error(e.message)
      }

      if(!meta.index) meta.index = index;

      if(meta.uuid) relatedContents.current[meta.uuid] = node.value

      //console.log(meta);

      if (node.lang == 'markdown' || !node.lang) {
        if (meta.type == 'chat') {
          return <ChatBlock key={meta.index} codes={node.value} lang={`markdown`} meta={node.meta ?? ""} index={meta.index} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex
                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}></ChatBlock>
        } else if (meta.type == 'container') {
          return <ContainerBlock containerType={meta.containerType} assignmentToken={props.token} lastStep={props.lastStep} timeLeft={meta.timeLeft} warning={meta.warning} refInfo={meta.ref} key={meta.index} index={meta.index} meta={node.meta}

            createContainer={(type: number) => {
              if (socketClient.current == null) {
                return false
              }
              socketClient.current.volatile.emit('assignment_event', {
                type: 'get-container',
                assignment_token: props.token,
                container_type: type,
                local_dev_token: localDevToken
              })
              return socketContainerStatusPayload.current
            }}

            callback={(currentIndex: number, result: any) => {
              if (result == 1) {

                if (nextIndex == currentIndex) {
                  let _currentIndex = currentIndex

                  if (props.token) {
                    axios({
                      method: 'post',
                      url: apiUrl('/rest/assignment-last-step'),
                      headers: { 'Content-Type': 'application/json' },
                      data: { assignment_token: props.token, last_step: _currentIndex + 1 }
                    }).catch(e => console.log(e))
                  }

                  setNextIndex(() => {
                    return _currentIndex + 1
                  })
                }
              }
            }}></ContainerBlock>
        } else if (meta.type == 'control') {
          return <ControlBlock token={props.token} lastStep={props.lastStep} timeLeft={meta.timeLeft} warning={meta.warning} content={node.value} refInfo={meta.ref} key={meta.index} index={meta.index} action={meta.action} sendCommand={async(feedback: string)=>{
                                                if(meta.action == 'submit') {
                                                    if(props.token) {
                                                        let result = await axios({
                                                            method: 'post',
                                                            url: apiUrl('/rest/submit-assignment'),
                                                            headers: { 'Content-Type': 'application/json' },
                                                            data: {assignment_token: props.token, content: 'web-online', status: 'completed', feedback, testResults: testResults.current, currentStep: meta.index }
                                                        });
                                                        if (result.data.payload == 'OK')
                                                          return true;
                                                        else
                                                          return result.data.error;
                                                    } else {
                                                      return 'No token is found';
                                                    }
                                                }

                                                if(socketClient.current == null) {
                                                  return true
                                                }

                                                if(meta.history) {

                                                  let pass = false

                                                  for(let i = 0; i < 10; i ++) {
                                                    await sleep(500)
                                                    let res = socketShellHistory.current
                                                    if (res) {
                                                      let regex
                                                      if(meta.history.indexOf('/') == 0) {
                                                        let str = meta.history;
                                                        let regexPattern = str.slice(1, str.lastIndexOf("/"));
                                                        let regexFlags = str.slice(str.lastIndexOf("/") + 1);
                                                        regex = new RegExp(regexPattern, regexFlags);
                                                      } else {
                                                        regex = new RegExp(meta.history);
                                                      }
                                                      if(regex.test(res)) {
                                                        pass = true
                                                        if(!meta.cmd) return true
                                                      } else {
                                                        return meta.error
                                                      }
                                                    }
                                      
                                                  }

                                                  if(!pass) return meta.error || 'Your dev container is offline or system error, please try again later or contact support.'
                                                }

                                                if(!meta.cmd) return true

                                                if(!meta.dir) meta.dir = '/tmp'

                                                //console.log(`shell:${meta.cmd}:${meta.dir}:${meta.regx}`)

                                                socketShellResponses.current[`shell:${meta.cmd}:${meta.dir}:${meta.regx}`] = null
                                                emitAssignmentEvent({type: 'shell', cmd: meta.cmd, dir: meta.dir, regx: meta.regx, error: meta.error})
   
                                                for(let i = 0; i < 30; i ++) {
                                                  await sleep(500)
                                                  let res = socketShellResponses.current[`shell:${meta.cmd}:${meta.dir}:${meta.regx}`]
                                                  if ( res != null) {

                                                    if(meta.cmd.includes('git remote')) {
                                                      const webUrl = getGithubPagesUrl(res.response)
                                                      if(!webUrl) {
                                                        return "Your containner has a git repository setup issue!"
                                                      } else {

                                                        if(props.token) {
                                                            axios({
                                                              method: 'post',
                                                              url: apiUrl('/rest/assignment-web-url'),
                                                              headers: { 'Content-Type': 'application/json' },
                                                              data: {assignment_token: props.token,  web_url: webUrl }
                                                          }).catch(e=>console.log(e))
                                                        }

                                                        return true
                                                      }
                                                    }

                                                    let regex
                                                    if(meta.regx.indexOf('/') == 0) {
                                                      let str = meta.regx;
                                                      let regexPattern = str.slice(1, str.lastIndexOf("/"));
                                                      let regexFlags = str.slice(str.lastIndexOf("/") + 1);
                                                      regex = new RegExp(regexPattern, regexFlags);
                                                    } else {
                                                      regex = new RegExp(meta.regx);
                                                    }
                                                    if(regex.test(res.response)) {
                                                      return true
                                                    } else {
                                                      return res.error
                                                    }
                                                  }

                                                }

                                                return meta.error || 'Your dev container is offline or system error, please try again later or contact support.'
                                            }
          } meta={node.meta} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(meta.action == 'nestEnd' && props.callback && props.index != undefined) {
                if(courseCallbackRef.current) return
                courseCallbackRef.current = true
                props.callback(props.index, 1)
                return
              }

              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex


                if(props.token) {
                    axios({
                      method: 'post',
                      url: apiUrl('/rest/assignment-last-step'),
                      headers: { 'Content-Type': 'application/json' },
                      data: {assignment_token: props.token,  last_step: _currentIndex + 1 }
                  }).catch(e=>console.log(e))
                }

                //console.log(`elements.length ${elements.length}, currentIndex ${currentIndex}`)

                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}>
          </ControlBlock>
        } else if (meta.type == 'bash') {
          return <BashBlock key={meta.index} index={meta.index} meta={node.meta ?? null} content={node.value} 
            callback={(currentIndex: number, result: any) => {
              if (result == 1) {
                if(nextIndex == currentIndex) {
                  let _currentIndex = currentIndex
                  setNextIndex(()=> {
                    return _currentIndex + 1
                  })
                }
              }
            }}
            sendText={(text:string, addNewLine: boolean)=>{
              const payload = {type: 'terminal_sent_text', text, addNewLine, dst: 'vscode'}
              emitAssignmentEvent(payload)
            }}
            sendCommand={(payload: any)=>{
              payload.dst = 'vscode'
              emitAssignmentEvent(payload)
            }}
          ></BashBlock>
        } else if (meta.type == 'vscode') {
          return <VSCodeBlock key={meta.index} index={meta.index} meta={node.meta ?? null} content={node.value} 
            callback={(currentIndex: number, result: any) => {
              if (result == 1) {
                if(nextIndex == currentIndex) {
                  let _currentIndex = currentIndex
                  setNextIndex(()=> {
                    return _currentIndex + 1
                  })
                }
              }
            }}
            sendCommand={(payload: any)=>{
              payload.dst = 'vscode'
              emitAssignmentEvent(payload)
            }}
          ></VSCodeBlock>
        } else if(meta.type == 'audioResponse') {

          return <AudioResponse key={meta.index} index={meta.index} fromLang={meta.fromLang} toLang={meta.toLang} audioUrl={meta.audioUrl} meta={node.meta ?? null} content={node.value.replaceAll('\\```', '```').replaceAll('\\`\\`\\`', '```')} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex
                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}></AudioResponse>

        } else {
          return <MarkdownPlay key={meta.index} index={meta.index} meta={node.meta ?? null} content={node.value.replaceAll('\\```', '```').replaceAll('\\`\\`\\`', '```')} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex
                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}></MarkdownPlay>
        }
      } else if (node.lang == 'yaml') {
        if (meta.type == 'form') {
          return <FormBlock token={props.token} lastStep={props.lastStep} row={meta.row} order={meta.order} refInfo={meta.ref} video={meta.video}  key={meta.index} yml={node.value} index={meta.index} onSubmit={(uuid: string, data: any)=>{

            // data = {assignment_token: assignmentToken, test: results, action: 'test', ref, isPassed: boolean}
            testResults.current[uuid] = {test: data.test, relatedContent: relatedContents.current[uuid], isPassed: data.isPassed}

            axios({
              method: 'post',
              url: apiUrl('/rest/assignment-activity'),
              headers: { 'Content-Type': 'application/json' },
              data: {... data, relatedContent: relatedContents.current[uuid], currentStep: meta.index}
            }).catch(e=>console.log(e));

          }} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex
                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}/>
        } else if(meta.type == 'list') {
          return <ListBLock key={meta.index} meta={node.meta ?? "{}"} yml={node.value} index={meta.index} callback={(currentIndex: number, result: any) => {
            if (result == 1) {
              if(nextIndex == currentIndex) {
                let _currentIndex = currentIndex
                setNextIndex(()=> {
                  return _currentIndex + 1
                })
              }
            }
          }}/>
        } else if (meta.type == 'notebook') {
          return <NotebookBlock key={meta.index} index={meta.index} meta={node.meta ?? null} bookType={meta.bookType} file={meta.file} lang={meta.lang} yml={node.value} 
            callback={(currentIndex: number, result: any) => {
              if (result == 1) {
                if(nextIndex == currentIndex) {
                  let _currentIndex = currentIndex
                  setNextIndex(()=> {
                    return _currentIndex + 1
                  })
                }
              }
            }}
            
            sendCode={(bookType: string, file:string, lang: string, code: string, execute: boolean)=>{
              let type = 'notebook_add_cell'

              if(bookType == 'notebook') {
                if(execute) type = 'notebook_add_execute'
              } else {
                type = 'editor_add_code'
              }
              const payload = {type, file, lang, code, dst: 'vscode'}
              emitAssignmentEvent(payload)
            }}
          
          ></NotebookBlock>
        } else if (meta.type == 'media') {
          return <MediaBlock key={meta.index} index={meta.index} meta={node.meta ?? null} yml={node.value} 
            callback={(currentIndex: number, result: any) => {
              if (result == 1) {
                if(nextIndex == currentIndex) {
                  let _currentIndex = currentIndex
                  setNextIndex(()=> {
                    return _currentIndex + 1
                  })
                }
              }
            }}
          ></MediaBlock>
        } else {
          return null
        }
      } else if (node.lang == 'tabs') {
        return <CodeTabsBlock key={meta.index} uuid={meta.uuid} content={node.value} meta={node.meta ?? "{}"} index={meta.index} callback={(currentIndex: number, result: any) => {
          if (result == 1) {
            if(nextIndex == currentIndex) {
              let _currentIndex = currentIndex
              setNextIndex(()=> {
                return _currentIndex + 1
              })
            }
          }
        }}/>
      } else if (node.lang == 'slides' || meta.type == 'slides') {
        return <SlidesBlock key={meta.index} content={node.value} meta={node.meta ?? "{}"} index={meta.index} callback={(currentIndex: number, result: any) => {
          if (result == 1) {
            if(nextIndex == currentIndex) {
              let _currentIndex = currentIndex
              setNextIndex(()=> {
                return _currentIndex + 1
              })
            }
          }
        }}/>
      } else if (node.lang == 'memory-card' || meta.type == 'memory-card') {
        return <MemoryCardBlock key={meta.index} content={node.value} meta={node.meta ?? "{}"} index={meta.index} callback={(currentIndex: number, result: any) => {
          if (result == 1) {
            if(nextIndex == currentIndex) {
              let _currentIndex = currentIndex
              setNextIndex(()=> {
                return _currentIndex + 1
              })
            }
          }
        }}/>
      } else if (meta.type == 'code') {
        return <CodeBlock token={props.token} key={meta.index} codes={node.value} lang={node.lang ?? "any"} meta={node.meta ?? "{}"} index={meta.index} callback={(currentIndex: number, result: any) => {
          if (result == 1) {
            //console.log(currentIndex, index, nextIndex)

            if(nextIndex == currentIndex) {
              let _currentIndex = currentIndex
              setNextIndex(()=> {
                return _currentIndex + 1
              })
            }
            
          }
        }}></CodeBlock>
      } else {// plantuml, mermaid, latex
        let fallbackMarkDownCode = `\`\`\`${node.lang}\n${node.value}\n\`\`\``;

        return  <MarkdownPlay key={meta.index} index={meta.index} meta={node.meta ?? null} content={fallbackMarkDownCode} callback={(currentIndex: number, result: any) => {
          if (result == 1) {
            if(nextIndex == currentIndex) {
              let _currentIndex = currentIndex
              setNextIndex(()=> {
                return _currentIndex + 1
              })
            }
          }
        }}></MarkdownPlay>
      }
    } else {
      return null
    }
  }

  useEffect(() => {
    let cancelled = false
    axios.get(apiUrl('/api/local-dev-token')).then((res) => {
      const token = res.data?.token
      if (!cancelled && typeof token === 'string' && token.length > 0) {
        setLocalDevToken(token)
      }
    }).catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(()=> {
    if(!props.token || !localDevToken) return
    if(socketClient.current != null) return;

    socketClient.current = io(getApiBase(), {reconnection: true, reconnectionDelay: 1000, reconnectionDelayMax:15000});

    const socket = socketClient.current;

    socket.on("connect", () => {
      socket.sendBuffer = []
      socket.emit('assignment_event',  {type: 'sign-in', token: localDevToken});
    })

    socket.on('connected', () => {
    })

    socket.on('server_event', (msg: any) => {
      if(msg.type == 'sign-in-request') {
        socket.emit('assignment_event',  {type: 'sign-in', token: localDevToken});
      } else if (msg.type == 'container-status') {
        socketContainerStatusPayload.current = msg
      }
    })

    socket.on('container_event', (msg: any) => {
      if(msg.type == 'shell') {
        socketShellResponses.current[`${msg.type}:${msg.cmd}:${msg.dir}:${msg.regx}`] = msg
      } else if (msg.type == 'history') {
        socketShellHistory.current = socketShellHistory.current + "\n" + msg.content
      }
    })

    socket.on("disconnect", () => {
      console.log(socket.id);
    })

  }, [props.token, localDevToken])

  useEffect(() => {

    async function init() {
      if(elements.length < nextIndex -1) {
        let items = []
        for(let i = 1; i < nextIndex; i ++) {
          items.push(await getNode(i))
        }
        setElements([... items, await getNode(nextIndex)])
      } else {
        setElements([... elements, await getNode(nextIndex)])
      }
    }
    init()
  }, [nextIndex])

  useEffect(() => {
    const next = Math.max(Number(props.lastStep ?? 1), 1);
    setElements([]);
    setNextIndex(next);
  }, [props.courseData, props.lastStep]);

    return (
        <div>
            {/*<h1 className="text-2xl mb-6">{courseMeta.title}</h1>*/}
            <div className='prose max-w-none'>
            {
                elements
            }
            </div>
            {/*<LiveChatWindowNoSSR initialWidth={500} initialHeight={400} />*/}
        </div>
    )
}

export default CourseBlock
