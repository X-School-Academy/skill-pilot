import { useState, useEffect, useRef, useCallback } from 'react';
import { Text, Button, Group, Stack, Textarea, Select } from '@mantine/core';
import { apiUrl } from '../../libs/api-base';
import MainLayout from '../../components/main-layout';

// ─── Live avatar server URL — direct ws connection, mirrors camera pattern ────
const LIVE_AVATAR_WS_URL =
  process.env.NEXT_PUBLIC_LIVE_AVATAR_WS_URL ?? 'ws://127.0.0.1:8008';

// ─── Types ────────────────────────────────────────────────────────────────────
interface TurnConfig {
  turn_server_urls: string;
  turn_server_username: string;
  turn_server_password: string;
}

const predefinedMessages: { message: string; emotion: string; title: string }[] = [];

const dropdownOptions = predefinedMessages.map((item) => {
  const value =
    item.message.endsWith('.wav') || item.message.endsWith('.jpg')
      ? item.message
      : `Repeat exactly: '${item.message}' in a '${item.emotion}' style. No additional words or commentary.`;
  return { value, label: item.title };
});

// ─── Page component ───────────────────────────────────────────────────────────
export default function LiveAvatarPage() {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [serverAudioMuted, setServerAudioMuted] = useState(false);
  const [micMuted, setMicMuted] = useState(true);
  const [chatInput, setChatInput] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [selectedMessage, setSelectedMessage] = useState<string | null>(null);
  const [loadingVisible, setLoadingVisible] = useState(true);
  const [turnConfig, setTurnConfig] = useState<TurnConfig | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
    localStreamRef.current?.getTracks().forEach((t) => t.stop());
    localStreamRef.current = null;
    setConnected(false);
    setLoadingVisible(true);
  }, []);

  // Fetch TURN config on mount (WS URL comes from env/constant, not config)
  useEffect(() => {
    fetch(apiUrl('/api/live-avatar/config'))
      .then((r) => r.json())
      .then((d: TurnConfig) => setTurnConfig(d))
      .catch(() => setTurnConfig({ turn_server_urls: '', turn_server_username: '', turn_server_password: '' }));

    return () => { disconnect(); };
  }, [disconnect]);

  const sendWs = useCallback((payload: object) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  }, []);

  const connect = useCallback(async () => {
    setConnecting(true);
    setLoadingVisible(true);
    setStatusMsg('');

    // ── Direct WS to avatar server ──────────────────────────────────────────
    const ws = new WebSocket(`${LIVE_AVATAR_WS_URL}/ws`);
    wsRef.current = ws;

    // ── RTCPeerConnection ───────────────────────────────────────────────────
    const iceServers: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }];
    if (turnConfig?.turn_server_urls) {
      iceServers.push({
        urls: turnConfig.turn_server_urls.split(',').map((u) => u.trim()).filter(Boolean),
        username: turnConfig.turn_server_username,
        credential: turnConfig.turn_server_password,
      });
    }
    const pc = new RTCPeerConnection({ iceServers });
    pcRef.current = pc;
    pc.addTransceiver('video', { direction: 'recvonly' });

    pc.onicecandidate = (event) => {
      if (!event.candidate) return;
      const state = pc.connectionState || pc.iceConnectionState;
      if (state === 'closed' || state === 'failed' || state === 'disconnected') return;
      const { candidate, sdpMid, sdpMLineIndex } = event.candidate;
      sendWs({ type: 'candidate', candidate: { candidate, sdpMid, sdpMLineIndex } });
    };

    pc.ontrack = (event) => {
      const video = videoRef.current;
      if (!video) return;
      if (event.track.kind === 'video') {
        video.srcObject = event.streams[0];
      } else if (event.track.kind === 'audio') {
        const stream = (video.srcObject as MediaStream) ?? new MediaStream();
        event.streams[0].getAudioTracks().forEach((t) => stream.addTrack(t));
        video.srcObject = stream;
      }
    };

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data as string) as {
          type: string; sdp?: string; sdpType?: RTCSdpType; candidate?: RTCIceCandidateInit; error?: string;
        };
        if (msg.type === 'answer') {
          await pc.setRemoteDescription(new RTCSessionDescription({ sdp: msg.sdp!, type: msg.sdpType! }));
        } else if (msg.type === 'candidate' && msg.candidate) {
          await pc.addIceCandidate(msg.candidate);
        } else if (msg.type === 'error') {
          setStatusMsg(`Error: ${msg.error ?? 'unknown'}`);
        }
      } catch (e) {
        console.error('[live-avatar] ws parse error', e);
      }
    };

    ws.onclose = () => setConnected(false);

    ws.onopen = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        localStreamRef.current = stream;
        stream.getAudioTracks().forEach((t) => {
          t.enabled = !micMuted;
          pc.addTrack(t, stream);
        });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Wait for ICE gathering to complete
        await new Promise<void>((resolve) => {
          if (pc.iceGatheringState === 'complete') { resolve(); return; }
          const check = () => {
            if (pc.iceGatheringState === 'complete') {
              pc.removeEventListener('icegatheringstatechange', check);
              resolve();
            }
          };
          pc.addEventListener('icegatheringstatechange', check);
        });

        sendWs({ type: 'offer', sdp: pc.localDescription!.sdp, sdpType: pc.localDescription!.type });
        setConnected(true);
      } catch (err) {
        console.error('[live-avatar] connection error', err);
        setStatusMsg('Connection failed. Is the Live Avatar server running?');
        disconnect();
      } finally {
        setConnecting(false);
      }
    };

    ws.onerror = () => {
      setStatusMsg('WebSocket error — check that the avatar server is running.');
      disconnect();
      setConnecting(false);
    };
  }, [turnConfig, micMuted, sendWs, disconnect]);

  const handleToggleServerAudio = () => {
    const next = !serverAudioMuted;
    setServerAudioMuted(next);
    if (videoRef.current) videoRef.current.muted = next;
  };

  const handleToggleMic = () => {
    const next = !micMuted;
    setMicMuted(next);
    localStreamRef.current?.getAudioTracks().forEach((t) => { t.enabled = !next; });
    sendWs({ type: 'mic_mute', muted: next });
  };

  const handleStop = () => {
    sendWs({ type: 'text', message: 'Please stop, that is OK' });
    setStatusMsg('"stop" sent');
  };

  const handleSendText = () => {
    if (!chatInput.trim()) return;
    sendWs({ type: 'text', message: chatInput });
    setStatusMsg(`"${chatInput}" sent`);
    setChatInput('');
  };

  const handleSendSelected = () => {
    if (!selectedMessage) return;
    sendWs({ type: 'predefined', message: selectedMessage });
    const title = dropdownOptions.find((o) => o.value === selectedMessage)?.label ?? selectedMessage;
    setStatusMsg(`"${title}" sent`);
    setSelectedMessage(null);
  };

  return (
    <MainLayout title="Live Avatar">
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column' }}>
        <Text size="xl" weight={700} mb={16}>
          Live Avatar
        </Text>

        {/* Connect / status */}
        {!connected && (
          <Stack spacing="sm" mb={16} style={{ maxWidth: 640 }}>
            <Group spacing="xs">
              <Button onClick={() => void connect()} loading={connecting}>
                Connect
              </Button>
            </Group>
            {statusMsg && (
              <Text size="sm" color="red">{statusMsg}</Text>
            )}
          </Stack>
        )}

        {/* Video */}
        <div style={{ position: 'relative', width: 640, height: 480, background: '#000', marginBottom: 12 }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            controls
            style={{ width: '100%', height: '100%' }}
            onCanPlay={() => setLoadingVisible(false)}
          />
          {loadingVisible && connected && (
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)', color: '#fff', fontSize: 18,
            }}>
              Loading…
            </div>
          )}
        </div>

        {/* Controls */}
        {connected && (
          <>
            <Group spacing="xs" mb={12}>
              <Button size="sm" variant="outline" onClick={handleToggleServerAudio}>
                {serverAudioMuted ? 'Unmute Server Audio' : 'Mute Server Audio'}
              </Button>
              <Button size="sm" variant="outline" onClick={handleToggleMic}>
                {micMuted ? 'Unmute Mic' : 'Mute Mic'}
              </Button>
              <Button size="sm" variant="outline" color="red" onClick={handleStop}>
                Stop
              </Button>
              <Button size="sm" variant="outline" color="orange" onClick={disconnect}>
                Disconnect
              </Button>
            </Group>

            {dropdownOptions.length > 0 && (
              <Group spacing="xs" mb={16}>
                <Select
                  placeholder="Select a message"
                  data={dropdownOptions}
                  value={selectedMessage}
                  onChange={(val) => {
                    setSelectedMessage(val);
                    if (val) {
                      const title = dropdownOptions.find((o) => o.value === val)?.label ?? val;
                      setStatusMsg(`"${title}" selected`);
                    }
                  }}
                  style={{ minWidth: 220 }}
                  clearable
                />
                <Button size="sm" onClick={handleSendSelected} disabled={!selectedMessage}>
                  Send
                </Button>
              </Group>
            )}

            <div style={{ maxWidth: 640 }}>
              <Text size="md" weight={600} mb={8}>Chat</Text>
              <Textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.currentTarget.value)}
                placeholder="Enter text message"
                minRows={3}
                mb={8}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendText();
                  }
                }}
              />
              <Group spacing="xs">
                <Button size="sm" onClick={handleSendText} disabled={!chatInput.trim()}>
                  Send
                </Button>
                {statusMsg && (
                  <Text size="sm" color="green">{statusMsg}</Text>
                )}
              </Group>
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}
