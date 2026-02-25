import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconArrowLeft, IconCamera, IconPlus, IconSearch, IconTrash, IconSettings } from '@tabler/icons-react';
import MainLayout from '../../components/main-layout';
import { apiUrl } from '../../libs/api-base';

// ─── Types ────────────────────────────────────────────────────────────────────

interface DetectionConfig {
  enabled: boolean;
  fps: number;
  model: string;
}

interface Camera {
  id: string;
  name: string;
  source: 'onvif' | 'manual';
  rtsp_url: string;
  snapshot_url: string;
  onvif_host: string;
  onvif_port: number;
  username: string;
  added_at: string;
  detection: DetectionConfig;
  added?: boolean; // for discovered-not-yet-added
}

interface TurnConfig {
  turn_server_urls: string;
  turn_server_username: string;
  turn_server_password: string;
}

interface IceCandidatePayload {
  candidate?: string;
  sdpMid?: string | null;
  sdpMLineIndex?: number | null;
}

// ─── Data channel helpers ─────────────────────────────────────────────────────

function dcSend(dc: RTCDataChannel | null, type: string, payload: object = {}) {
  if (dc?.readyState === 'open') {
    dc.send(JSON.stringify({ type, payload }));
  }
}

function cameraLog(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: unknown) {
  const prefix = '[webui.camera]';
  const fn = (
    level === 'error' ? console.error
      : level === 'warn' ? console.warn
        : level === 'debug' ? console.debug
          : console.info
  );
  if (data === undefined) fn(prefix, message);
  else fn(prefix, message, data);
  void fetch(apiUrl('/api/webui/log'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tag: 'webui.camera', level, message, data }),
  }).catch(() => {});
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CamerasPage() {
  // ── Connection state ──────────────────────────────────────────────────────
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // ── Camera state ──────────────────────────────────────────────────────────
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [discovered, setDiscovered] = useState<Camera[]>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<'idle' | 'running'>('idle');
  const [screenshots, setScreenshots] = useState<Record<string, string>>({}); // camera_id → base64 JPEG
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);

  // ── Modal state ───────────────────────────────────────────────────────────
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState<Camera | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState<Camera | null>(null);

  // Add camera form
  const [addName, setAddName] = useState('');
  const [addRtsp, setAddRtsp] = useState('');
  const [addSnapshot, setAddSnapshot] = useState('');
  const [addUsername, setAddUsername] = useState('');
  const [addPassword, setAddPassword] = useState('');
  const [addFromDiscovered, setAddFromDiscovered] = useState<Camera | null>(null);

  // Per-camera settings form
  const [settingsDetEnabled, setSettingsDetEnabled] = useState(false);
  const [settingsDetFps, setSettingsDetFps] = useState<number>(1);
  const [settingsDetModel, setSettingsDetModel] = useState('yolov8n');

  // ── WebRTC refs ───────────────────────────────────────────────────────────
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const screenshotTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const turnConfigRef = useRef<TurnConfig | null>(null);
  const cameraListRef = useRef<Camera[]>([]);
  const signalReadyRef = useRef(false);
  const pendingIceRef = useRef<RTCIceCandidateInit[]>([]);
  const selectedCameraRef = useRef<Camera | null>(null);
  const autoConnectStartedRef = useRef(false);
  const connectStartedAtRef = useRef<number>(0);
  const iceRecoveryInFlightRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  // Keep refs in sync so callbacks don't capture stale closures
  useEffect(() => { cameraListRef.current = cameras; }, [cameras]);
  useEffect(() => { selectedCameraRef.current = selectedCamera; }, [selectedCamera]);

  // ── Fetch TURN config once ────────────────────────────────────────────────
  useEffect(() => {
    fetch(apiUrl('/api/cameras/config'), { credentials: 'include' })
      .then((r) => r.json())
      .then((d: TurnConfig) => { turnConfigRef.current = d; })
      .catch(() => {});
  }, []);

  // ── Disconnect cleanup ────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    cameraLog('info', 'disconnect requested');
    if (screenshotTimerRef.current) {
      clearInterval(screenshotTimerRef.current);
      screenshotTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    iceRecoveryInFlightRef.current = false;
    dcRef.current?.close();
    dcRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
    signalReadyRef.current = false;
    pendingIceRef.current = [];
    setConnected(false);
    setConnecting(false);
    setSelectedCamera(null);
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [disconnect]);

  // ── Connect ───────────────────────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (!isMountedRef.current) return;
    if (connecting) return;
    connectStartedAtRef.current = performance.now();
    cameraLog('info', 'connect start');
    setConnecting(true);
    setStatusMsg('');
    signalReadyRef.current = false;
    pendingIceRef.current = [];
    const sentIceKeys = new Set<string>();

    const iceKey = (candidate: IceCandidatePayload) =>
      `${candidate.candidate ?? ''}|${candidate.sdpMid ?? ''}|${candidate.sdpMLineIndex ?? -1}`;

    const sendIceCandidate = async (candidate: IceCandidatePayload) => {
      if (!candidate.candidate) return;
      const key = iceKey(candidate);
      if (sentIceKeys.has(key)) return;
      sentIceKeys.add(key);
      try {
        await fetch(apiUrl('/api/cameras/signal'), {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'ice_candidate', candidate }),
        });
      } catch (err) {
        cameraLog('warn', 'failed to send ICE candidate', err instanceof Error ? err.message : String(err));
      }
    };

    const scheduleReconnect = (delayMs: number, reason: string) => {
      if (!isMountedRef.current) return;
      if (reconnectTimerRef.current) return;
      cameraLog('warn', 'schedule reconnect', { reason, delay_ms: delayMs });
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        if (!isMountedRef.current) return;
        disconnect();
        void connect();
      }, delayMs);
    };

    const applyOffer = async (iceRestart: boolean) => {
      // During offer/answer exchange (including ICE restart), buffer local
      // candidates and flush only after remote answer is applied.
      signalReadyRef.current = false;
      pendingIceRef.current = [];
      const offer = await pc.createOffer(iceRestart ? { iceRestart: true } : undefined);
      await pc.setLocalDescription(offer);
      cameraLog('info', iceRestart ? 'ice-restart offer created' : 'offer created');

      await new Promise<void>((resolve) => {
        if (pendingIceRef.current.length > 0 || pc.iceGatheringState === 'complete') {
          resolve();
          return;
        }
        const startedAt = Date.now();
        const timer = setInterval(() => {
          if (pendingIceRef.current.length > 0 || pc.iceGatheringState === 'complete' || Date.now() - startedAt >= 250) {
            clearInterval(timer);
            resolve();
          }
        }, 20);
      });

      const initialCandidates = [...pendingIceRef.current] as IceCandidatePayload[];
      initialCandidates.forEach((c) => sentIceKeys.add(iceKey(c)));

      const resp = await fetch(apiUrl('/api/cameras/signal'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'offer',
          sdp: pc.localDescription!.sdp,
          sdpType: pc.localDescription!.type,
          iceRestart,
          candidates: initialCandidates,
        }),
      });
      cameraLog('info', iceRestart ? 'ice-restart offer sent' : 'offer sent', { initial_candidates: initialCandidates.length });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: resp.statusText }));
        throw new Error(err.error ?? resp.statusText);
      }

      const answerRaw = await resp.json() as Record<string, unknown>;
      const answerSdp = typeof answerRaw.sdp === 'string' ? answerRaw.sdp : '';
      const answerTypeRaw =
        (typeof answerRaw.type === 'string' && answerRaw.type)
        || (typeof answerRaw.sdpType === 'string' && answerRaw.sdpType)
        || (typeof answerRaw.sdp_type === 'string' && answerRaw.sdp_type)
        || '';

      if (!answerSdp || !answerTypeRaw) {
        throw new Error(`Invalid offer answer payload: ${JSON.stringify(answerRaw).slice(0, 400)}`);
      }

      await pc.setRemoteDescription(
        new RTCSessionDescription({ sdp: answerSdp, type: answerTypeRaw as RTCSdpType }),
      );
      cameraLog('info', iceRestart ? 'ice-restart answer applied' : 'answer applied');
      const remoteCandidates = Array.isArray(answerRaw.candidates)
        ? (answerRaw.candidates as IceCandidatePayload[])
        : [];
      for (const rc of remoteCandidates) {
        if (!rc?.candidate) continue;
        await pc.addIceCandidate(rc as RTCIceCandidateInit);
      }
      cameraLog('info', 'remote candidates applied', { count: remoteCandidates.length, ice_restart: iceRestart });
      signalReadyRef.current = true;
      const pending = [...pendingIceRef.current] as IceCandidatePayload[];
      pendingIceRef.current = [];
      await Promise.all(pending.map((c) => sendIceCandidate(c)));
    };

    const turn = turnConfigRef.current;
    const iceServers: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }];
    if (turn?.turn_server_urls) {
      iceServers.push({
        urls: turn.turn_server_urls.split(',').map((u) => u.trim()).filter(Boolean),
        username: turn.turn_server_username,
        credential: turn.turn_server_password,
      });
    }

    const pc = new RTCPeerConnection({ iceServers });
    pcRef.current = pc;
    pc.onconnectionstatechange = () => {
      if (pc !== pcRef.current) return;
      cameraLog('info', 'pc connectionstate', pc.connectionState);
    };
    pc.oniceconnectionstatechange = () => {
      if (pc !== pcRef.current) return;
      cameraLog('info', 'pc iceconnectionstate', pc.iceConnectionState);
      if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
        if (iceRecoveryInFlightRef.current) return;
        iceRecoveryInFlightRef.current = true;
        void (async () => {
          try {
            await applyOffer(true);
            cameraLog('info', 'ice recovery success');
          } catch (err) {
            cameraLog('warn', 'ice recovery failed', err instanceof Error ? err.message : String(err));
            scheduleReconnect(300, `ice-${pc.iceConnectionState}`);
          } finally {
            iceRecoveryInFlightRef.current = false;
          }
        })();
      }
    };

    pc.onicecandidate = (event) => {
      if (pc !== pcRef.current) return;
      if (!event.candidate) return;
      const candidate = event.candidate.toJSON();
      cameraLog('debug', 'local ice candidate gathered');
      if (signalReadyRef.current) {
        void sendIceCandidate(candidate);
      } else {
        pendingIceRef.current.push(candidate);
      }
    };

    const dc = pc.createDataChannel('cameras', { ordered: true });
    dcRef.current = dc;

    dc.onopen = () => {
      if (dc !== dcRef.current) return;
      const elapsedMs = Math.round(performance.now() - connectStartedAtRef.current);
      cameraLog('info', 'datachannel open', { elapsed_ms: elapsedMs });
      setConnected(true);
      setConnecting(false);
      setStatusMsg('');
      dcSend(dc, 'get_cameras');
      screenshotTimerRef.current = setInterval(() => {
        const cams = cameraListRef.current.filter((c) => c.added !== false);
        cams.forEach((c) => dcSend(dcRef.current, 'get_screenshot', { camera_id: c.id }));
      }, 3000);
      heartbeatTimerRef.current = setInterval(() => {
        dcSend(dcRef.current, 'ping', { ts: Date.now() });
      }, 5000);
    };

    dc.onclose = () => {
      if (dc !== dcRef.current) return;
      cameraLog('warn', 'datachannel closed');
      setConnected(false);
      setConnecting(false);
      scheduleReconnect(300, 'datachannel-close');
    };

    dc.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as { type: string; payload: Record<string, unknown> };
        handleDcMessage(msg.type, msg.payload);
      } catch {
        cameraLog('error', 'bad datachannel message', event.data);
      }
    };

    pc.ontrack = (event) => {
      const video = videoRef.current;
      if (!video) return;
      if (event.track.kind === 'video') {
        cameraLog('info', 'remote video track received');
        const stream = event.streams[0] ?? new MediaStream([event.track]);
        video.srcObject = stream;
      } else if (event.track.kind === 'audio') {
        cameraLog('info', 'remote audio track received');
        const stream = (video.srcObject as MediaStream) ?? new MediaStream();
        event.streams[0]?.getAudioTracks().forEach((t) => stream.addTrack(t));
        video.srcObject = stream;
      }
    };

    try {
      await applyOffer(false);
    } catch (err) {
      cameraLog('error', 'connect error', err instanceof Error ? err.message : String(err));
      setStatusMsg(
        'Unable to connect to the camera server. Please check local firewall settings, '
        + 'or configure a TURN server to relay the connection.',
      );
      disconnect();
    }
  }, [connecting, disconnect]);

  useEffect(() => {
    if (connected || connecting) return;
    if (reconnectTimerRef.current) return;
    const delay = autoConnectStartedRef.current ? 3000 : 0;
    autoConnectStartedRef.current = true;
    const timer = setTimeout(() => { void connect(); }, delay);
    return () => clearTimeout(timer);
  }, [connect, connected, connecting]);

  // ── Data channel message handler ──────────────────────────────────────────
  const handleDcMessage = useCallback((type: string, payload: Record<string, unknown>) => {
    switch (type) {
      case 'pong':
        cameraLog('debug', 'pong recv', payload);
        break;
      case 'cameras_list': {
        const list = (payload.cameras as Camera[]) ?? [];
        const added = list.filter((c) => c.added !== false);
        const disc = list.filter((c) => c.added === false);
        setCameras(added);
        setDiscovered(disc);
        break;
      }
      case 'screenshot': {
        const cid = payload.camera_id as string;
        const img = payload.image as string;
        if (cid && img) {
          setScreenshots((prev) => ({ ...prev, [cid]: img }));
        }
        break;
      }
      case 'discovery_update': {
        const disc = (payload.discovered as Camera[]) ?? [];
        setDiscovered(disc.filter((c) => c.added === false));
        if ((payload.status as string) === 'running') {
          setDiscoveryStatus('running');
        } else if ((payload.status as string) === 'stopped') {
          setDiscoveryStatus('idle');
        }
        break;
      }
      case 'camera_added':
      case 'camera_deleted':
        // Refresh full list
        dcSend(dcRef.current, 'get_cameras');
        break;
      case 'detection_updated':
        dcSend(dcRef.current, 'get_cameras');
        break;
      case 'video_stopped':
        if (selectedCameraRef.current?.id === (payload.camera_id as string)) {
          setSelectedCamera(null);
        }
        break;
      case 'renegotiate': {
        // Server added a video track — handle re-negotiation
        cameraLog('info', 'renegotiate offer received');
        const sdp = payload.sdp as string;
        const sdpType = payload.sdpType as RTCSdpType;
        const pc = pcRef.current;
        if (!pc || !sdp) break;
        (async () => {
          await pc.setRemoteDescription(new RTCSessionDescription({ sdp, type: sdpType }));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          dcSend(dcRef.current, 'renegotiate_answer', { sdp: answer.sdp, sdpType: answer.type });
          cameraLog('info', 'renegotiate answer sent');
        })().catch((e) => cameraLog('error', 'renegotiate error', e instanceof Error ? e.message : String(e)));
        break;
      }
      case 'detection_event':
        cameraLog('info', 'detection event', payload);
        break;
      case 'error':
        cameraLog('warn', 'server error', payload);
        break;
      default:
        break;
    }
  }, []);

  // ── Actions ───────────────────────────────────────────────────────────────
  const startDiscovery = () => {
    setDiscoveryStatus('idle');
    setDiscovered([]);
    setShowDiscoveryModal(true);
    dcSend(dcRef.current, 'start_discovery');
  };

  const handleAddCamera = () => {
    if (addFromDiscovered) {
      dcSend(dcRef.current, 'add_camera', {
        name: addName || addFromDiscovered.name,
        onvif_camera_id: addFromDiscovered.id,
        onvif_host: addFromDiscovered.onvif_host,
        onvif_port: addFromDiscovered.onvif_port,
        username: addUsername,
        password: addPassword,
      });
    } else {
      dcSend(dcRef.current, 'add_camera', {
        name: addName,
        rtsp_url: addRtsp,
        snapshot_url: addSnapshot,
        username: addUsername,
        password: addPassword,
      });
    }
    setShowAddModal(false);
    setAddFromDiscovered(null);
    setAddName(''); setAddRtsp(''); setAddSnapshot(''); setAddUsername(''); setAddPassword('');
  };

  const handleDeleteCamera = (cam: Camera) => {
    dcSend(dcRef.current, 'delete_camera', { camera_id: cam.id });
    setShowDeleteModal(null);
    if (selectedCamera?.id === cam.id) setSelectedCamera(null);
  };

  const handlePlayCamera = (cam: Camera) => {
    cameraLog('info', 'start_video click', { camera_id: cam.id });
    setSelectedCamera(cam);
    dcSend(dcRef.current, 'start_video', { camera_id: cam.id });
  };

  const handleStopVideo = () => {
    if (selectedCamera) {
      dcSend(dcRef.current, 'stop_video', { camera_id: selectedCamera.id });
    }
    setSelectedCamera(null);
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const openSettings = (cam: Camera) => {
    setSettingsDetEnabled(cam.detection?.enabled ?? false);
    setSettingsDetFps(cam.detection?.fps ?? 1);
    setSettingsDetModel(cam.detection?.model ?? 'yolov8n');
    setShowSettingsModal(cam);
  };

  const saveSettings = () => {
    if (!showSettingsModal) return;
    dcSend(dcRef.current, 'update_detection', {
      camera_id: showSettingsModal.id,
      enabled: settingsDetEnabled,
      fps: settingsDetFps,
      model: settingsDetModel,
    });
    setShowSettingsModal(null);
  };

  // ── Grid layout ───────────────────────────────────────────────────────────
  const activeCameras = cameras.filter((c) => c.added !== false);
  const gridCols = activeCameras.length === 0 ? 1 : Math.ceil(Math.sqrt(activeCameras.length));

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <MainLayout title="Security Cameras">
      <div style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>

        {/* ── Header ── */}
        {!selectedCamera && (
          <Group position="apart" mb={12} style={{ flexShrink: 0 }}>
            <Group spacing="xs">
              <IconCamera size={20} />
              <Title order={4}>Security Cameras</Title>
              {!connected && connecting && (
                <Badge color="yellow" size="sm">Connecting...</Badge>
              )}
              {connected && (
                <Badge color="green" size="sm">Connected</Badge>
              )}
            </Group>
            <Group spacing="xs">
              {connected && (
                <>
                  <ActionIcon size="sm" variant="subtle" title="Discover ONVIF cameras" onClick={startDiscovery}>
                    <IconSearch size={16} />
                  </ActionIcon>
                  <ActionIcon
                    size="sm"
                    variant="subtle"
                    title="Add camera manually"
                    onClick={() => { setAddFromDiscovered(null); setShowAddModal(true); }}
                  >
                    <IconPlus size={16} />
                  </ActionIcon>
                </>
              )}
            </Group>
          </Group>
        )}

        {statusMsg && (
          <Text color="red" size="sm" mb={8}>{statusMsg}</Text>
        )}

        {/* ── Single camera video view ── */}
        {selectedCamera && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Group mb={8} spacing="xs">
              <ActionIcon onClick={handleStopVideo} variant="subtle">
                <IconArrowLeft size={18} />
              </ActionIcon>
              <Text weight={600}>{selectedCamera.name}</Text>
            </Group>
            <div style={{ flex: 1, background: '#000', borderRadius: 8, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                controls
                onLoadedData={() => cameraLog('info', 'first video frame rendered')}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
          </div>
        )}

        {/* ── Grid view ── */}
        {!selectedCamera && (
          <>
            {!connected && !statusMsg && !connecting && (
              <div style={{ textAlign: 'center', marginTop: 48 }}>
                <Text color="dimmed" mb={12}>Connecting to camera server…</Text>
              </div>
            )}
            {!connected && (connecting || !statusMsg) && (
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                }}
              >
                <Stack spacing="xs" align="center">
                  <Loader size="sm" />
                  <Text color="dimmed" size="sm">Connecting to camera server…</Text>
                </Stack>
              </div>
            )}
            {connected && activeCameras.length === 0 && (
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                }}
              >
                <Stack spacing="sm" align="center">
                  <Text color="dimmed">No cameras added yet.</Text>
                  <Group spacing="sm">
                    <Button size="sm" leftIcon={<IconSearch size={14} />} onClick={startDiscovery}>
                      Add ONVIF Camera
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      leftIcon={<IconPlus size={14} />}
                      onClick={() => { setAddFromDiscovered(null); setShowAddModal(true); }}
                    >
                      Add RTSP Camera
                    </Button>
                  </Group>
                </Stack>
              </div>
            )}
            {activeCameras.length > 0 && (
              <div
                style={{
                  flex: 1,
                  display: 'grid',
                  gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
                  gap: 8,
                  overflow: 'auto',
                }}
              >
                {activeCameras.map((cam) => (
                  <div
                    key={cam.id}
                    style={{
                      background: '#1a1b1e',
                      borderRadius: 8,
                      overflow: 'hidden',
                      cursor: 'pointer',
                      position: 'relative',
                      aspectRatio: '16/9',
                    }}
                    onClick={() => handlePlayCamera(cam)}
                  >
                    {screenshots[cam.id] ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`data:image/jpeg;base64,${screenshots[cam.id]}`}
                        alt={cam.name}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Loader size="sm" />
                      </div>
                    )}
                    {/* Overlay: name + actions */}
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        background: 'rgba(0,0,0,0.55)',
                        padding: '4px 8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Text size="xs" color="white" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {cam.name}
                      </Text>
                      <Group spacing={6}>
                        <ActionIcon
                          size="md"
                          variant="transparent"
                          color="gray"
                          title="Settings"
                          onClick={() => openSettings(cam)}
                        >
                          <IconSettings size={20} color="white" />
                        </ActionIcon>
                        <ActionIcon
                          size="md"
                          variant="transparent"
                          color="red"
                          title="Delete"
                          onClick={() => setShowDeleteModal(cam)}
                        >
                          <IconTrash size={20} />
                        </ActionIcon>
                      </Group>
                    </div>
                    {cam.detection?.enabled && (
                      <Badge
                        size="xs"
                        color="orange"
                        style={{ position: 'absolute', top: 4, right: 4 }}
                      >
                        AI
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── ONVIF Discovery Modal ── */}
        <Modal
          opened={showDiscoveryModal}
          onClose={() => {
            setShowDiscoveryModal(false);
            dcSend(dcRef.current, 'stop_discovery');
          }}
          title="ONVIF Camera Discovery"
          size="md"
        >
          <Stack spacing="xs">
            <Group spacing="xs">
              {discoveryStatus === 'running' && <Loader size="xs" />}
              <Text size="sm" color="dimmed">
                {discoveryStatus === 'running' ? 'Scanning local network…' : 'Waiting for results…'}
              </Text>
            </Group>
            {discovered.length === 0 && (
              <Text size="sm" color="dimmed">No cameras discovered yet.</Text>
            )}
            {discovered.map((cam) => (
              <Group key={cam.id} position="apart" style={{ border: '1px solid #373a40', borderRadius: 6, padding: '8px 12px' }}>
                <div>
                  <Text size="sm" weight={500}>{cam.name}</Text>
                  <Text size="xs" color="dimmed">{cam.onvif_host}:{cam.onvif_port}</Text>
                </div>
                <Button
                  size="xs"
                  onClick={() => {
                    setAddFromDiscovered(cam);
                    setAddName(cam.name);
                    setShowDiscoveryModal(false);
                    setShowAddModal(true);
                  }}
                >
                  Add
                </Button>
              </Group>
            ))}
          </Stack>
        </Modal>

        {/* ── Add Camera Modal ── */}
        <Modal
          opened={showAddModal}
          onClose={() => { setShowAddModal(false); setAddFromDiscovered(null); }}
          title={addFromDiscovered ? `Add ONVIF Camera: ${addFromDiscovered.name}` : 'Add Camera'}
          size="sm"
        >
          <Stack spacing="sm">
            <TextInput label="Name" value={addName} onChange={(e) => setAddName(e.currentTarget.value)} required />
            {!addFromDiscovered && (
              <>
                <TextInput label="RTSP URL" placeholder="rtsp://192.168.1.10/stream" value={addRtsp} onChange={(e) => setAddRtsp(e.currentTarget.value)} required />
                <TextInput label="Snapshot URL (optional)" placeholder="http://192.168.1.10/snapshot.jpg" value={addSnapshot} onChange={(e) => setAddSnapshot(e.currentTarget.value)} />
              </>
            )}
            <TextInput label="Username" value={addUsername} onChange={(e) => setAddUsername(e.currentTarget.value)} />
            <TextInput label="Password" type="password" value={addPassword} onChange={(e) => setAddPassword(e.currentTarget.value)} />
            <Group position="right" mt="xs">
              <Button variant="default" onClick={() => { setShowAddModal(false); setAddFromDiscovered(null); }}>Cancel</Button>
              <Button onClick={handleAddCamera} disabled={!addName || (!addFromDiscovered && !addRtsp)}>Add</Button>
            </Group>
          </Stack>
        </Modal>

        {/* ── Delete Confirm Modal ── */}
        <Modal
          opened={showDeleteModal !== null}
          onClose={() => setShowDeleteModal(null)}
          title="Delete Camera"
          size="xs"
        >
          <Text size="sm" mb={16}>
            Remove <strong>{showDeleteModal?.name}</strong> from your cameras?
          </Text>
          <Group position="right">
            <Button variant="default" onClick={() => setShowDeleteModal(null)}>Cancel</Button>
            <Button color="red" onClick={() => showDeleteModal && handleDeleteCamera(showDeleteModal)}>Delete</Button>
          </Group>
        </Modal>

        {/* ── Per-camera Settings Modal ── */}
        <Modal
          opened={showSettingsModal !== null}
          onClose={() => setShowSettingsModal(null)}
          title={`Settings: ${showSettingsModal?.name ?? ''}`}
          size="sm"
        >
          <Stack spacing="sm">
            <Text size="sm" weight={500}>Human Detection</Text>
            <Switch
              label="Enable detection"
              checked={settingsDetEnabled}
              onChange={(e) => setSettingsDetEnabled(e.currentTarget.checked)}
            />
            <NumberInput
              label="Target FPS (best-effort)"
              value={settingsDetFps}
              onChange={(v) => setSettingsDetFps(Number(v) || 1)}
              min={0.1}
              max={10}
              step={0.5}
              precision={1}
              disabled={!settingsDetEnabled}
            />
            <Select
              label="YOLO Model"
              value={settingsDetModel}
              onChange={(v) => setSettingsDetModel(v ?? 'yolov8n')}
              data={['yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x']}
              disabled={!settingsDetEnabled}
            />
            <Group position="right" mt="xs">
              <Button variant="default" onClick={() => setShowSettingsModal(null)}>Cancel</Button>
              <Button onClick={saveSettings}>Save</Button>
            </Group>
          </Stack>
        </Modal>

      </div>
    </MainLayout>
  );
}
