import React, { useState, useEffect, useRef} from "react";
import { useRouter } from 'next/router'
import YouTube, { YouTubeProps, YouTubeEvent } from 'react-youtube';

const VideoPlayer = () => {
    const router = useRouter()
    const playerRef = useRef<YouTube>(null)
    const [videoID, setVideoID] = useState<string>('')
    const [start, setStart] = useState(0)
    const [end, setEnd] = useState(0)
    const [showNotice, setShowNotice] = useState(false)
    const [startedPlaying, setStartedPlaying] = useState(false)

    const opts: YouTubeProps['opts'] = {
        width: '100%', 
        height: '100%',
        playerVars: {
            autoplay: 1,
            disablekb: 0,
            rel: 0,
            fs: 0
        },
    };

    const onTimeUpdate = async() => {
        if (playerRef.current && playerRef.current.getInternalPlayer() && end) {
            const currentTime = await playerRef.current.getInternalPlayer().getCurrentTime()
            console.log(currentTime)
            if(currentTime >= end) {
                if(currentTime < end + 10) playerRef.current.getInternalPlayer().pauseVideo()
                setEnd(0)
                setShowNotice(true)
                setTimeout(()=>{
                    setShowNotice(false)
                }, 15*1000)
            }
        }
    }

    const onPlayerReady: YouTubeProps['onReady'] = (event) => {
        //set to min 1 to avoid one chrome issue
        event.target.seekTo(start == 0? 1 : start)
        console.log("seekTo", start)

        //using event.target to avoid one bug
        //if (playerRef.current && playerRef.current.getInternalPlayer()) {
        //    playerRef.current.getInternalPlayer().seekTo(start == 0? 1 : start)
        //}
    }

    const onStateChange = (event: YouTubeEvent<number>) => {
        console.log("onStateChange: ", event.data)
        if(event.data == 1 && !startedPlaying) setStartedPlaying(true)
    }

    const handleKeyPress = async (event: any) => {
        const player = playerRef.current?.getInternalPlayer();
        if (!player) return;

        switch (event.key) {
            case ' ':
            case 'k':
                const state = await player.getPlayerState();
                state === 1 ? player.pauseVideo() : player.playVideo();
                break;
            case 'ArrowLeft':
                player.seekTo(await player.getCurrentTime() - 5);
                break;
            case 'ArrowRight':
                player.seekTo(await player.getCurrentTime() + 5);
                break;
            case 'ArrowUp':
                player.setVolume(Math.min(await player.getVolume() + 10, 100));
                break;
            case 'ArrowDown':
                player.setVolume(Math.max(await player.getVolume() - 10, 0));
                break;
            case 'j':
                player.seekTo(await player.getCurrentTime() - 10);
                break;
            case 'l':
                player.seekTo(await player.getCurrentTime() + 10);
                break;
            case 'm':
                const isMuted = await player.isMuted();
                isMuted ? player.unMute() : player.mute();
                break;
            default:
                if (!isNaN(event.key)) {
                    const fraction = parseInt(event.key) / 10;
                    player.seekTo(await player.getDuration() * fraction);
                }
                break;
        }
    };

    useEffect(() => {
        const { slugs } = router.query;
        if (slugs && slugs[0]) {
            if(slugs[1]) setStart(Number.parseInt(slugs[1]))
            if(slugs[2]) setEnd( Number.parseInt(slugs[2]))
            setVideoID(slugs[0])
        }
    }, [router.query])

    useEffect(() => {

        let interval:any

        if(end && startedPlaying) interval = setInterval(onTimeUpdate, 1000)

        return () => {
            if(interval) clearInterval(interval)
        }

    }, [end, startedPlaying])

    useEffect(() => {
        window.addEventListener('keydown', handleKeyPress);

        return () => {
            window.removeEventListener('keydown', handleKeyPress);
        }
    }, []);

    if(!videoID) return null

    return <>
        <div style={{ backgroundColor: '#303030', position: 'relative'}} className="flex flex-col items-center justify-center h-screen">
            {showNotice && <h1 style={{color: 'red', backgroundColor: 'yellow', padding: 10, position: 'fixed', top: '10%', opacity: 0.4, borderRadius: 10}}>You can return to the assignment or continue watching the video now.</h1>}
            <YouTube ref={playerRef} className="aspect-video w-full m-5" videoId={videoID} opts={opts} onReady={onPlayerReady} onStateChange={onStateChange} />
        </div>
        <style jsx>{`
            body {
                margin: 0px;
                background-color: #303030;
            }
        `}</style>
    </>;
}

export default VideoPlayer;