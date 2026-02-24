import React, { useEffect, useRef, useState, memo } from 'react';
import MarkdownRenderer, {Markdown} from './MarkdownRenderer';
import yaml from 'js-yaml';
import { useSearchParams } from 'next/navigation';
import axios from "axios";
import { el } from 'date-fns/locale';

/*
- type: text
  name: a
  label: Question A
  markdown: |
    ```dart
    ```
  hint: |
    any text
    ```markdown
    ```
  placeholder: placeholder
  value: operating system
- type: textarea
  name: b
  label: Question B
  row: 3
  placeholder: placeholder text
  value: operating system 3
  hint: ''
- type: select
  name: c
  label: Question C
  options:
    - option 1
    - option 2
    - option 3
  value: 1
  hint: ''
- type: radio
  name: d
  label: Question D
  options:
    - option 1
    - option 2
    - option 3
  value: 1
  hint: ''
- type: checkbox
  name: e
  label: Question E
  options:
  - option 1
  - option 2
  - option 3
  value: [1,2,3]
  hint: ''
*/

type BoldifyBackticksProps = {
    children: string;
  };

const BoldifyBackticks:React.FC<BoldifyBackticksProps> = ({ children }) => {
  const boldify = (str: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    let isBold = false;

    str.split('`').forEach((part, index) => {
      if (index === 0 && part === "") {
        isBold = true;
        return;
      }

      if (isBold) {
        parts.push(<code key={index}>{`${part}`}</code>);
      } else {
        parts.push(part);
      }

      isBold = !isBold;
    });

    return parts;
  }

  return <>{boldify(children)}</>;
}
  

interface Props {
    yml: string;
    token?: string;
    lastStep?: number;
    index?: number;
    refInfo?:string;
    video?:string;
    row?: boolean;
    order?: boolean;
    onSubmit: (uuid: string, data: any) => void;
    callback?: (index: number, result: any) => void;
}

const FormBlock = (props: Props) => {
    const [errors, setErrors] = useState<any>({})
    const [hint, setHint] = useState('')
    const [showHint, setShowHint] = useState(false)
    const [showPass, setShowPass] = useState<any>(false)
    const elements: any = yaml.load(props.yml)

    const searchParams = useSearchParams()
 
    const assignmentToken = searchParams.get('t')

    const callbackRef = useRef(false);


    useEffect(() => {

        if(props.lastStep && props.index && props.lastStep > props.index) {
            setShowPass(true)
        }

    }, [])

    const removeElement = (arr: any, val: any) => {
        const index = arr.indexOf(val);
        if (index > -1) {
            arr.splice(index, 1);
        }
        return arr;
    }

    return <form className={`flex flex-col gap-4 mt-4 mb-4`} onSubmit={async (e: any) => {
        e.preventDefault();
        let pass = true

        setErrors({})
        setShowPass(false)

        let results: any = []

        for (let element of elements) {
            console.log(element.name)
            errors[element.name] = 'Pleae finish the test.'

            switch (element.type) {
                case 'checkbox':
                    {
                        let checked = false
                        let incorrect = false
                        let answer = element.value
                        var cboxes = document.getElementsByName(element.name + '[]') as any;
                        var len = cboxes.length;
                        var selected: any = [];
                        for (var i = 0; i < len; i++) {
                            if (cboxes[i].checked) {
                                selected.push(i)
                                checked = true
                                if( answer.indexOf(i) > -1)
                                    answer = removeElement(answer, i)
                                else {
                                    incorrect = true
                                    break
                                }
                            }
                        }
                        if (checked) {
                            if (answer.length > 0 || incorrect) {
                                errors[element.name] = 'Please check your selection!'
                                pass = false

                                results.push({question: element, failedAnswer: selected})

                            } else {
                                errors[element.name] = ''
                                results.push({question: element})
                            }

                        } else {
                            errors[element.name] = 'Your answer is required!'
                            pass = false
                        }
                    }

                    break
                case 'radio':
                    {
                        let answer = element.value
                        let rboxes = document.getElementsByName(element.name) as any;
                        let len = rboxes.length;
                        var selected: any = [];
                        errors[element.name] = 'Please check your selection!'
                        for (let i = 0; i < len; i++) {
                            if (rboxes[i].checked) {
                                selected.push(i)
                                if(answer == i) {
                                    errors[element.name] = ''
                                }
                                break
                            }
                        }
                        if (errors[element.name] != '') {
                            pass = false

                            results.push({question: element, failedAnswer: selected})
                        } else {
                            results.push({question: element})
                        }
                    }
                    break
                case 'select':
                    {
                        let answer = element.value
                        let sel = document.getElementById(element.name) as any;
                        errors[element.name] = 'Please check your selection!'
                        if (answer == sel?.selectedIndex - 1) {
                            errors[element.name] = ''
                        } else if (sel?.selectedIndex == 0) {
                            errors[element.name] = 'Your answer is required!'
                            pass = false
                        }
                        if (errors[element.name] != '') {
                            pass = false
                            results.push({question: element, failedAnswer: [sel?.selectedIndex - 1]})
                        } else {
                            results.push({question: element})
                        }
                    }
                    break
                default:
                    {
                        if (element.value.toLowerCase().trim() == (document.getElementById(element.name) as any)?.value.toLowerCase().trim()) {
                            errors[element.name] = ''
                            results.push({question: element})
                        } else if((document.getElementById(element.name) as any)?.value.trim() == '') {
                            pass = false
                            errors[element.name] = 'Your answer is required!'
                        } else {
                            pass = false
                            errors[element.name] = 'Please check your answer!'
                            results.push({question: element, failedAnswer: [(document.getElementById(element.name) as any)?.value]})
                        }
                    }
            }
  
        }

        setErrors({ ...errors })

        if(pass) {
            setShowPass(true)

            if(assignmentToken) {
                let ref = null
                if(elements[0]) ref = elements[0].name

                props.onSubmit(elements[0].name, {assignment_token: assignmentToken, test: results, action: 'test', ref, isPassed: true});
            }

            if(!props.callback) return
            if(callbackRef.current) return
            callbackRef.current = true
            props.callback!(props.index??0, 1)
        } else {
            if(assignmentToken) {
                let ref = null
                if(elements[0]) ref = elements[0].name

                props.onSubmit(elements[0].name, {assignment_token: assignmentToken, test: results, action: 'test', ref, isPassed: false});
            }

            if(!props.callback) return
            props.callback!(props.index??0, 0)
        }

    }}>
        {
            elements.map((element: any, index: number) => {
                switch (element.type) {
                    case 'text':
                        return (
                            <div key={index} >
                                {element.markdown ? <MarkdownRenderer noActions={true} readOnly={true} markdown={element.markdown} /> : null}
                                <label htmlFor={element.name} className="block text-base font-bold leading-6 text-gray-900"><Markdown>{element.label}</Markdown></label>
                                <input className="mt-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-base sm:leading-6" type="text" onChange={(e)=>{setErrors({})}} id={element.name} name={element.name} placeholder={element.placeholder} />
                                {errors[element.name] ? <div className="block text-base font-normal leading-6 text-red mt-2">{errors[element.name]} 
                                    {element.hint && <a href="#" className='ml-2' onClick={(e)=> {
                                        e.preventDefault()
                                        setHint(element.hint)
                                        setShowHint(!showHint)
                                    }}>Show Hint?</a>}
                                </div> : null}
                            </div>)
                    case 'textarea':
                        return (
                            <div key={index}>
                                {element.markdown ? <MarkdownRenderer noActions={true} readOnly={true} markdown={element.markdown} /> : null}
                                <label htmlFor={element.name} className="block text-base font-bold leading-6 text-gray-900"><Markdown>{element.label}</Markdown></label>
                                <textarea id={element.name} name={element.name} rows={element.rows} placeholder={element.placeholder} onChange={(e)=>{setErrors({})}} className="mt-1 block w-full rounded-md border-0 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:py-1.5 sm:text-base sm:leading-6"></textarea>
                                {errors[element.name] ? <div className="block text-base font-normal leading-6 text-red mt-2">{errors[element.name]}
                                    {element.hint && <a href="#" className='ml-2' onClick={(e)=> {
                                        e.preventDefault()
                                        setHint(element.hint)
                                        setShowHint(!showHint)
                                    }}>Show Hint?</a>}
                                </div> : null}
                            </div>)
                    case 'select':
                        return (
                            <div key={index}>
                                {element.markdown ? <MarkdownRenderer noActions={true} readOnly={true} markdown={element.markdown} /> : null}
                                <label htmlFor={element.name} className="block text-base font-bold leading-6 text-gray-900"><Markdown>{element.label}</Markdown></label>
                                <select id={element.name} name={element.name} className="mt-2 block w-full rounded-md border-0 bg-white py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-base sm:leading-6" onChange={(e)=>{setErrors({})}}>
                                    <option>Select</option>
                                    {
                                        element.options.map((option: any, idx: number) => {
                                            return <option key={idx}>{`${props.order ? `${idx + 1}. `:""}${option}`}</option>
                                        })
                                    }
                                </select>
                                {errors[element.name] ? <div className="block text-base font-normal leading-6 text-red mt-2">{errors[element.name]}
                                    {element.hint && <a href="#" className='ml-2' onClick={(e)=> {
                                        e.preventDefault()
                                        setHint(element.hint)
                                        setShowHint(!showHint)
                                    }}>Show Hint?</a>}
                                </div> : null}
                            </div>)
                    case 'checkbox':
                        return (
                            <div key={index}>
                                {element.markdown ? <MarkdownRenderer noActions={true} readOnly={true} markdown={element.markdown} /> : null}
                                <label htmlFor={element.name} className="block text-base font-bold leading-6 text-gray-900"><Markdown>{element.label}</Markdown></label>
                                <div className={`flex ${props.row? 'flex-row gap-8':'flex-col gap-2'} mt-2`}>
                                {
                                    element.options.map((option: any, idx: number) => {
                                        return (<div className="flex items-start" key={element.name + idx}>
                                            <input className="h-4 w-4 mt-1 border-black-300 text-indigo-600 focus:ring-indigo-600" type="checkbox" key={idx} name={element.name + '[]'} id={element.name + idx} value={option} onChange={(e)=>{setErrors({})}} />
                                            <label
                                                htmlFor={element.name + idx}
                                                className="ml-3 block text-base font-normal leading-6 text-gray-900"
                                            >
                                                <BoldifyBackticks>{`${props.order ? `${idx + 1}. `:""}${option}`}</BoldifyBackticks>
                                            </label></div>)
                                    })
                                }
                                </div>
                                {errors[element.name] ? <div className="block text-base font-normal leading-6 text-red mt-2">{errors[element.name]}
                                    {element.hint && <a href="#" className='ml-2' onClick={(e)=> {
                                        e.preventDefault()
                                        setHint(element.hint)
                                        setShowHint(!showHint)
                                    }}>Show Hint?</a>}
                                </div> : null}
                            </div>)
                    case 'radio':
                        return (
                            <div key={index}>
                                {element.markdown ? <MarkdownRenderer noActions={true} readOnly={true} markdown={element.markdown} /> : null}
                                <label htmlFor={element.name} className="block text-base font-bold leading-6 text-gray-900"><Markdown>{element.label}</Markdown></label>
                                <div className={`flex ${props.row? 'flex-row gap-8':'flex-col gap-2'} mt-2`}>
                                {
                                    element.options.map((option: any, idx: number) => {
                                        return (<div className="flex items-start" key={element.name + idx}>
                                            <input className="h-4 w-4 mt-1 border-black-300 text-indigo-600 focus:ring-indigo-600" type="radio" key={idx} name={element.name} id={element.name + idx} value={option} onChange={(e)=>{setErrors({})}} />
                                            <label
                                                htmlFor={element.name + idx}
                                                className="ml-3 block text-base font-normal leading-6 text-gray-900"
                                            >
                                                <BoldifyBackticks>{`${props.order ? `${idx + 1}. `:""}${option}`}</BoldifyBackticks>
                                            </label></div>)
                                    })
                                }
                                </div>
                                {errors[element.name] ? <div className="block text-base font-normal leading-6 text-red mt-2">{errors[element.name]}
                                    {element.hint && <a href="#" className='ml-2' onClick={(e)=> {
                                        e.preventDefault()
                                        setHint(element.hint)
                                        setShowHint(!showHint)
                                    }}>Show Hint?</a>}
                                </div> : null}
                            </div>)
                }
            })

        }
        { Object.keys(errors).length > 0 && !showPass && props.video && <div><MarkdownRenderer markdown={`You can check this video ${props.video} for answer.`}></MarkdownRenderer></div> }
        <div className='flex gap-5 items-end'>
            <input type='submit' value='Submit' disabled={showPass} className={`w-28 rounded h-10 border-primary-blue text-white font-medium bg-primary-blue ${showPass&& 'disabled:opacity-25'}`} /> 
            {showPass?<span className="inline-block text-base font-medium leading-6 text-secondary-green ml-5">Your have passed this test!</span>:null}
            { Object.keys(errors).length > 0 && !showPass && props.refInfo &&
             ( props.refInfo.startsWith("http")?<div>If you need help for this topic, please check this {props.refInfo.includes('youtube')?'video':'url'}: <a href={props.refInfo} target="_blank">props.refInfo</a></div>
             :(
                 props.refInfo=="ai"? "If you need help for this topic, please use the AI prompts section above.":
                 (props.refInfo=="ask"?'':props.refInfo)
                 
             ))
             }
        </div>
        { Object.keys(errors).length > 0 && !showPass && showHint && <MarkdownRenderer linkTarget='_blank' markdown={hint.replaceAll("\\```", "```")}></MarkdownRenderer>}
        { Object.keys(errors).length > 0 && !showPass && props.refInfo && props.refInfo=="ask" &&
        <>
        <div>If you need help with this topic, please ask the AI using the prompt box below::</div>
        <MarkdownRenderer markdown={`\`\`\`markdown {type:chat}

 \`\`\``}></MarkdownRenderer></>}
    </form>
}

export default memo(FormBlock)