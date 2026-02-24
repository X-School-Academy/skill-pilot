import React, { useEffect, useRef, memo } from "react"
import sleep from 'sleep-promise'
import RJSON from 'relaxed-json';
import yaml from 'js-yaml';
import logger from '../../libs/logger';

const isYouTubeUrl = (url: string) => {
    return url.includes('youtube.com') || url.includes('youtu.be');
}

const getYouTubeEmbedUrl = (url: string) => {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return match && match[2] ? `https://www.youtube.com/embed/${match[2]}` : url;
}

const MediaBlock = (props: any) => {
    const callbackRef = useRef(false);

    const ref = useRef<HTMLDivElement>(null)
 
    let meta: any = {}
    try {
      meta = RJSON.parse(props.meta ?? "{}")
    } catch (e: any) {
      logger.error(e.message)
    }

    const links: any = yaml.load(props.yml);

    let className = 'flex space-x-5';
    if(links.length > 1) {
        className = `grid grid-cols-2 gap-5 md:grid-cols-${links.length > 4 ? 4 : links.length}`;
    }

    useEffect(() => {
        const init = async () => {
            await sleep(1)
            ref.current!.style.opacity = '1'

            if(meta.during) await sleep(meta.during)
            
            if (props.callback) {
                if(callbackRef.current) return
                callbackRef.current = true
                props.callback(props.index, 1)
            }
        }
        init()
    }, [])

    return <div ref={ref} style={{ opacity: 0, transition: 'opacity 1s ease-in-out'}} className={className}>    
       {
            links.map((link: any, index: number) => (
                <div key={index} className="w-full">
                    {link.url.match(/\.(jpeg|jpg|gif|png)$/i) ? (
                        <div className={`w-full flex flex-col items-center`}>
                            <img src={link.url} title={link.title??''} className="w-full h-auto" />
                            {link.title && <div>{link.title}</div>}
                        </div>
                    ) : isYouTubeUrl(link.url) ? (
                        <div className={`w-full flex flex-col items-center`}>
                            <div style={{position: "relative", width: "100%", paddingTop: "56.25%"}}>
                                <iframe
                                    style={{position: "absolute", top: 0, left: 0, width: "100%", height: "100%"}}
                                    src={getYouTubeEmbedUrl(link.url)}
                                    allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                                    allowFullScreen
                                    title={`YouTube video ${index}`}
                                ></iframe>
                            </div>
                            {link.title && <div>{link.title}</div>}
                        </div>
                    ) : (
                        link.url.match(/\.(wave|mp3)$/i) ?
                        <audio controls>
                            <source src={link.url} type={`audio/${link.url.match(/\.mp3$/i) ? "mpeg":"wav"}`} />
                            Your browser does not support the audio element.
                        </audio>
                        :
                        <video controls playsInline src={link.url} className="w-full h-auto">
                        </video>
                    )}
                </div>
            ))
       }
    </div>
}

export default memo(MediaBlock)