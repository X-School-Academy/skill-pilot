import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import MainLayout from '../../components/main-layout';
import {
  Alert,
  Button,
  Group,
  Loader,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconCamera, IconPlus } from '@tabler/icons-react';
import { selectApiServerToken } from '../../features/apiServerToken/apiServerSlice';

// ─── FRAME constants (preserved exactly from original) ────────────────────────
const FRAME = {
  HEAD1_SIZE: 6,
  HEAD2_SIZE: 18,
  CMD_SOF: 0xff,
  HEART_BEAT: 0xfe,
  NO_DECODE: 0xfd,
  REQ: 0x00,
  RES: 0x01,
  ADDR_SERVER: 0xffffffff,
  PLAYER_CAMERA_CONTROLLER: 0x53,
  COMMAND_H264_PLAY: 11,
  COMMAND_H264_ALIVE: 12,
  COMMAND_H264_STOP: 13,
  COMMAND_JPEG_PLAY: 21,
  COMMAND_JPEG_ALIVE: 22,
  COMMAND_JPEG_STOP: 23,
  PLAYER_CAMERA_CHANNEL: 0x54,
  PACKET_TYPE_JPEG: 0x04,
  CONTROL_CMD: 0,
  WEBRTC_CMD: 13,
} as const;

// ─── Types ────────────────────────────────────────────────────────────────────
interface Camera {
  id: number;
  hub_id: string;
  name: string;
}

type HubList = Record<string, Camera[]>;

interface PeerConnCallbacks {
  onJpegFrame: (cameraId: number, buffer: ArrayBuffer) => void;
  onAuthFail: () => void;
  getToken: () => string;
  onTrack: (hubId: string, stream: MediaStream) => void;
  sendWsMsg: (payload: object) => void;
}

// ─── Binary buffer helper (preserved from original) ───────────────────────────
function appendBuffer(a: ArrayBuffer, b: ArrayBuffer): ArrayBuffer {
  const tmp = new Uint8Array(a.byteLength + b.byteLength);
  tmp.set(new Uint8Array(a), 0);
  tmp.set(new Uint8Array(b), a.byteLength);
  return tmp.buffer;
}

// ─── PeerConn class ───────────────────────────────────────────────────────────
class PeerConn {
  readonly localUUID: string;
  readonly hubId: string;
  remoteUUID: string | null = null;

  private pc: RTCPeerConnection;
  private dc: RTCDataChannel | null = null;
  private dcReady = false;
  private lastBuffer = new ArrayBuffer(0);
  private pendingICE: string[] = [];
  private localPendingICE: RTCIceCandidateInit[] = [];
  private frameSeq = 0;
  private callbacks: PeerConnCallbacks;
  // Mirror original: auto-start JPEG on DC open (playing=true, cameraId=0)
  private playing = true;
  private cameraId = 0;

  constructor(
    localUUID: string,
    hubId: string,
    turnServers: RTCIceServer[],
    callbacks: PeerConnCallbacks
  ) {
    this.localUUID = localUUID;
    this.hubId = hubId;
    this.callbacks = callbacks;
    this.pc = new RTCPeerConnection({ iceServers: turnServers });
    this.init();
  }

  private init() {
    const pc = this.pc;

    pc.onconnectionstatechange = () => {
      if (
        (pc.connectionState === 'failed' || pc.connectionState === 'closed') &&
        (pc.iceConnectionState === 'disconnected' ||
          pc.iceConnectionState === 'failed' ||
          pc.iceConnectionState === 'closed')
      ) {
        console.warn('[PeerConn] connection failed, hub:', this.hubId);
      }
    };

    pc.ontrack = (event) => {
      if (event.streams[0]) {
        this.callbacks.onTrack(this.hubId, event.streams[0]);
      }
    };

    pc.onicecandidate = (event) => {
      if (event.candidate === null) {
        // All ICE gathered → send offer
        this.callbacks.sendWsMsg({
          action: 'offer',
          desc: JSON.stringify(pc.localDescription),
          src: this.localUUID,
          hubId: this.hubId,
        });
      } else {
        if (this.remoteUUID !== null) {
          this.callbacks.sendWsMsg({
            action: 'ice',
            ice: event.candidate.candidate,
            src: this.localUUID,
            dest: this.remoteUUID,
            hubId: this.hubId,
          });
        } else {
          this.pendingICE.push(event.candidate.candidate);
        }
      }
    };

    pc.addTransceiver('video', { direction: 'sendrecv' });

    const dc = pc.createDataChannel('data', { ordered: true });
    dc.binaryType = 'arraybuffer';
    this.dc = dc;

    dc.onopen = () => {
      this.dcReady = true;
      // Auto-start on connect, matching original behaviour
      if (this.playing) {
        const cmd = this.cameraId === 0 ? FRAME.COMMAND_JPEG_PLAY : FRAME.COMMAND_H264_PLAY;
        this.sendPlayFrame(this.cameraId, cmd, this.callbacks.getToken());
      }
    };

    dc.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      this.processFrame(event.data);
    };

    dc.onclose = () => {
      this.dcReady = false;
    };

    pc.createOffer().then((d) => pc.setLocalDescription(d)).catch(console.error);
  }

  private processFrame(buffer: ArrayBuffer) {
    if (this.lastBuffer.byteLength === 0) {
      const b0 = new DataView(buffer).getUint8(0);
      if (b0 !== FRAME.CMD_SOF && b0 !== FRAME.HEART_BEAT) return;
    } else {
      buffer = appendBuffer(this.lastBuffer, buffer);
    }

    while (true) {
      if (buffer.byteLength === 0) break;

      const view = new DataView(buffer);
      const b0 = view.getUint8(0);

      if (b0 === FRAME.HEART_BEAT) {
        buffer = buffer.slice(1);
        continue;
      }
      if (b0 !== FRAME.CMD_SOF) {
        this.lastBuffer = new ArrayBuffer(0);
        return;
      }
      if (buffer.byteLength < FRAME.HEAD1_SIZE + 1) break;

      const len = view.getUint32(FRAME.HEAD1_SIZE - 4);
      if (len > (3 * 4096 * 4096) / 1.5) {
        this.lastBuffer = new ArrayBuffer(0);
        return;
      }
      if (buffer.byteLength < len + FRAME.HEAD1_SIZE + 1) break;

      // Verify checksum
      let checksum = 0xff;
      for (let i = 1; i < len + FRAME.HEAD1_SIZE; i++) {
        checksum ^= view.getUint8(i);
      }
      if (checksum !== view.getUint8(len + FRAME.HEAD1_SIZE)) {
        this.lastBuffer = new ArrayBuffer(0);
        return;
      }

      if (view.getUint8(1) !== FRAME.NO_DECODE) {
        this.lastBuffer = new ArrayBuffer(0);
        return;
      }

      const frame = buffer.slice(FRAME.HEAD1_SIZE, FRAME.HEAD1_SIZE + len);

      if (frame.byteLength > FRAME.HEAD2_SIZE) {
        const fv = new DataView(frame);
        const cmd = fv.getUint8(FRAME.HEAD2_SIZE - 6);
        const type = fv.getUint8(FRAME.HEAD2_SIZE - 5);

        if (cmd === FRAME.PLAYER_CAMERA_CHANNEL && type === FRAME.REQ) {
          const payload = frame.slice(FRAME.HEAD2_SIZE);
          const pv = new DataView(payload);
          if (pv.getUint8(0) === FRAME.PACKET_TYPE_JPEG) {
            const camId = pv.getUint32(1);
            this.callbacks.onJpegFrame(camId, payload.slice(5));
          }
        } else if (cmd === FRAME.PLAYER_CAMERA_CONTROLLER && type === FRAME.RES) {
          try {
            const str = String.fromCharCode(...Array.from(new Uint8Array(frame.slice(FRAME.HEAD2_SIZE))));
            const resp = JSON.parse(str) as { status: number };
            if (resp.status === -1) this.callbacks.onAuthFail();
          } catch {
            // ignore parse errors
          }
        }
      }

      buffer = buffer.slice(len + FRAME.HEAD1_SIZE + 1);
    }

    this.lastBuffer = buffer;
  }

  play(cameraId: number, command: number, token: string) {
    this.cameraId = cameraId;
    this.playing = command === FRAME.COMMAND_H264_PLAY || command === FRAME.COMMAND_JPEG_PLAY;
    if (this.dcReady) this.sendPlayFrame(cameraId, command, token);
  }

  private sendPlayFrame(cameraId: number, command: number, token: string) {
    if (!this.dc || this.dc.readyState !== 'open') return;

    const payloadBuf = new Uint8Array(
      JSON.stringify({ cameraId, command, token })
        .split('')
        .map((c) => c.charCodeAt(0))
    );

    this.frameSeq++;
    const total = FRAME.HEAD1_SIZE + FRAME.HEAD2_SIZE + payloadBuf.byteLength + 1;
    const data = new ArrayBuffer(total);
    const view = new DataView(data);

    view.setUint8(0, FRAME.CMD_SOF);
    view.setUint8(1, FRAME.NO_DECODE);
    view.setUint32(2, FRAME.HEAD2_SIZE + payloadBuf.byteLength);
    view.setUint32(FRAME.HEAD1_SIZE, this.frameSeq);
    view.setUint32(FRAME.HEAD1_SIZE + 4, FRAME.ADDR_SERVER);
    view.setUint32(FRAME.HEAD1_SIZE + 8, 0);
    view.setUint8(FRAME.HEAD1_SIZE + 12, FRAME.PLAYER_CAMERA_CONTROLLER);
    view.setUint8(FRAME.HEAD1_SIZE + 13, FRAME.REQ);
    view.setUint8(FRAME.HEAD1_SIZE + 14, payloadBuf.byteLength);
    new Uint8Array(data).set(payloadBuf, FRAME.HEAD1_SIZE + FRAME.HEAD2_SIZE);

    let cs = 0xff;
    for (let i = 1; i < total - 1; i++) cs ^= view.getUint8(i);
    view.setUint8(total - 1, cs);

    this.dc.send(data);
  }

  startSession(remoteDesc: string, remoteUUID: string) {
    const cleaned = remoteDesc.replace(/a=candidate:[0-9 a-z.]*relay[0-9 a-z.]*\\r\\n/gm, '');
    this.remoteUUID = remoteUUID;

    this.pc
      .setRemoteDescription(new RTCSessionDescription(JSON.parse(cleaned)))
      .then(() => {
        this.pendingICE.forEach((candidate) => {
          this.callbacks.sendWsMsg({
            action: 'ice',
            ice: candidate,
            src: this.localUUID,
            dest: this.remoteUUID,
            hubId: this.hubId,
          });
        });
        this.pendingICE = [];

        this.localPendingICE.forEach((init) => {
          void this.pc.addIceCandidate({ ...init, sdpMid: '0', sdpMLineIndex: 0 });
          void this.pc.addIceCandidate({ ...init, sdpMid: '1', sdpMLineIndex: 1 });
        });
        this.localPendingICE = [];
      })
      .catch(console.error);
  }

  newIce(candidate: string) {
    if (candidate.includes('relay')) return;
    const init: RTCIceCandidateInit = { candidate, sdpMid: '0', sdpMLineIndex: 0 };
    if (this.pc.remoteDescription === null) {
      this.localPendingICE.push(init);
    } else {
      void this.pc.addIceCandidate({ candidate, sdpMid: '0', sdpMLineIndex: 0 });
      void this.pc.addIceCandidate({ candidate, sdpMid: '1', sdpMLineIndex: 1 });
    }
  }

  close() {
    this.pc.close();
  }
}

// ─── Camera server URL — configured via env var, mirrors live_avatar pattern ──
const CAMERA_WS_URL = process.env.NEXT_PUBLIC_CAMERA_WS_URL ?? 'ws://127.0.0.1:8081';

// ─── Page component ───────────────────────────────────────────────────────────
export default function CameraPage() {
  const apiTokenState = useSelector(selectApiServerToken);

  // ── UI state ────────────────────────────────────────────────────────────────
  const [hubList, setHubList] = useState<HubList | null>(null);
  const [currentView, setCurrentView] = useState<2 | 3 | 4>(2);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Modals
  const [onvifOpen, setOnvifOpen] = useState(false);
  const [rtspOpen, setRtspOpen] = useState(false);
  const [addCameraOpen, setAddCameraOpen] = useState(false);

  // Form fields
  const [onvifIp, setOnvifIp] = useState('');
  const [onvifUser, setOnvifUser] = useState('');
  const [onvifPass, setOnvifPass] = useState('');
  const [rtspUrl, setRtspUrl] = useState('');
  const [cameraName, setCameraName] = useState('');
  const [cameraLocation, setCameraLocation] = useState('');

  // ── Refs (no re-renders) ─────────────────────────────────────────────────────
  const wsRef = useRef<WebSocket | null>(null);
  const peerListRef = useRef<Map<string, PeerConn>>(new Map());
  const imageRefsRef = useRef<Map<number, HTMLImageElement>>(new Map());
  const iconRefsRef = useRef<Map<number, HTMLDivElement>>(new Map());
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const tokenRef = useRef('');
  const addCameraDataRef = useRef<Record<string, unknown>>({});
  const onvifDisabled = useRef(false);
  const rtspDisabled = useRef(false);
  const addCamDisabled = useRef(false);

  // Keep token ref current
  useEffect(() => {
    tokenRef.current = apiTokenState?.apiServerToken ?? '';
  }, [apiTokenState]);

  // ── WebSocket + peer lifecycle ────────────────────────────────────────────────
  useEffect(() => {
    let destroyed = false;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    // Track hub list locally to avoid stale closure on reconnect
    let localHubList: HubList | null = null;

    const sendWs = (payload: object) => {
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
    };

    const createPeer = (localUUID: string, hubId: string, turnServers: RTCIceServer[]) => {
      // One peer per hub
      let exists = false;
      peerListRef.current.forEach((p) => { if (p.hubId === hubId) exists = true; });
      if (exists) return;

      const peer = new PeerConn(localUUID, hubId, turnServers, {
        onJpegFrame: (camId, buffer) => {
          const img = imageRefsRef.current.get(camId);
          if (!img) return;
          const url = URL.createObjectURL(new Blob([buffer]));
          img.onload = () => {
            URL.revokeObjectURL(url);
            const icon = iconRefsRef.current.get(camId);
            if (icon) icon.style.display = 'none';
          };
          img.src = url;
        },
        onAuthFail: () => setAuthError('Authentication failed. Check your API server token.'),
        getToken: () => tokenRef.current,
        onTrack: (_hubId, stream) => {
          if (videoRef.current) videoRef.current.srcObject = stream;
        },
        sendWsMsg: sendWs,
      });

      peerListRef.current.set(localUUID, peer);
    };

    const handleMessage = (raw: string) => {
      let p: Record<string, unknown>;
      try { p = JSON.parse(raw) as Record<string, unknown>; } catch { return; }

      // Original protocol (action field)
      if (p.action === 'hubs') {
        localHubList = p.hubs as HubList;
        setHubList(localHubList);
        for (const hubId in localHubList) sendWs({ action: 'peer', hubId });
      } else if (p.action === 'peer') {
        createPeer(p.uuid as string, p.hubId as string, (p.turns ?? []) as RTCIceServer[]);
      } else if (p.action === 'answer') {
        peerListRef.current.get(p.dest as string)?.startSession(p.desc as string, p.src as string);
      } else if (p.action === 'ice') {
        peerListRef.current.get(p.dest as string)?.newIce(p.ice as string);
      }
      // Newer protocol (command + method fields)
      else if (typeof p.command === 'number') {
        const method = p.method as string;
        if (method === 'getHubInfoCallback') {
          localHubList = p.hubs as HubList;
          setHubList(localHubList);
          for (const hubId in localHubList) sendWs({ action: 'peer', hubId });
        } else if (method === 'getHubStatusCallback') {
          // hub status info available if needed
        } else if (method === 'getONVIFCameraStreamsCallback') {
          addCameraDataRef.current = (p.streamData ?? {}) as Record<string, unknown>;
          onvifDisabled.current = false;
          setOnvifOpen(false);
          setAddCameraOpen(true);
        } else if (method === 'checkRTSPCameraVideoUrlCallback') {
          addCameraDataRef.current = (p.streamData ?? {}) as Record<string, unknown>;
          rtspDisabled.current = false;
          setRtspOpen(false);
          setAddCameraOpen(true);
        } else if (method === 'addCameraCallback') {
          addCamDisabled.current = false;
          setAddCameraOpen(false);
          // Refresh hub list
          sendWs({ action: 'hubs' });
        } else if (method === 'onCameraAdded' || method === 'onCameraUpdated' || method === 'onCameraRemoved') {
          sendWs({ action: 'hubs' });
        }
      }
    };

    const connect = () => {
      if (destroyed) return;

      const ws = new WebSocket(CAMERA_WS_URL + '/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);

        const uuids: string[] = [];
        peerListRef.current.forEach((_, uuid) => uuids.push(uuid));
        ws.send(JSON.stringify({ action: 'sync', uuids }));

        if (localHubList === null) ws.send(JSON.stringify({ action: 'hubs' }));

        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('');
          else ws.close();
        }, 30000);
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
        if (!destroyed) reconnectTimer = setTimeout(connect, 10000);
      };

      ws.onmessage = (event) => {
        if (event.data && typeof event.data === 'string') handleMessage(event.data);
      };

      ws.onerror = (e) => console.error('[camera] ws error', e);
    };

    connect();

    return () => {
      destroyed = true;
      if (pingTimer) clearInterval(pingTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
      wsRef.current = null;
      peerListRef.current.forEach((p) => p.close());
      peerListRef.current.clear();
    };
  }, [CAMERA_WS_URL]);

  // ── WS send helper (stable ref-based) ────────────────────────────────────────
  const sendWs = (payload: object) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  };

  // ── View switching ─────────────────────────────────────────────────────────
  const switchToGrid = (cols: 2 | 3 | 4) => {
    setCurrentView(cols);
    setSelectedCamera(null);
    const token = tokenRef.current;
    peerListRef.current.forEach((p) => p.play(0, FRAME.COMMAND_H264_STOP, token));
    setTimeout(() => {
      peerListRef.current.forEach((p) => p.play(0, FRAME.COMMAND_JPEG_PLAY, token));
    }, 100);
  };

  const switchToCamera = (camera: Camera) => {
    setSelectedCamera(camera);
    const token = tokenRef.current;
    peerListRef.current.forEach((p) => {
      p.play(0, FRAME.COMMAND_JPEG_STOP, token);
      p.play(0, FRAME.COMMAND_H264_STOP, token);
    });
    peerListRef.current.forEach((p) => {
      if (p.hubId === camera.hub_id) p.play(camera.id, FRAME.COMMAND_H264_PLAY, token);
    });
  };

  // ── Flat camera list for the grid ─────────────────────────────────────────
  const allCameras: Camera[] = hubList ? Object.values(hubList).flat() : [];

  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <MainLayout title="Security Cameras">
      {/* ── Camera toolbar ── */}
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          padding: '0 1rem',
          gap: '0.5rem',
          height: 48,
          borderBottom: '1px solid #2c2e33',
          background: 'var(--mantine-color-body)',
        }}
      >
        <Text size="sm" weight={700} color="dimmed" style={{ marginRight: 'auto' }}>
          Security Cameras
        </Text>

        <Button
          variant={currentView === 2 && !selectedCamera ? 'filled' : 'subtle'}
          size="xs"
          onClick={() => switchToGrid(2)}
        >
          2COL
        </Button>
        <Button
          variant={currentView === 3 && !selectedCamera ? 'filled' : 'subtle'}
          size="xs"
          onClick={() => switchToGrid(3)}
        >
          3COL
        </Button>
        <Button
          variant={currentView === 4 && !selectedCamera ? 'filled' : 'subtle'}
          size="xs"
          onClick={() => switchToGrid(4)}
        >
          4COL
        </Button>

        <Button
          size="xs"
          variant="subtle"
          leftIcon={<IconCamera size={14} />}
          onClick={() => setOnvifOpen(true)}
        >
          ONVIF
        </Button>
        <Button
          size="xs"
          leftIcon={<IconPlus size={14} />}
          onClick={() => setRtspOpen(true)}
        >
          Add RTSP
        </Button>

        {!wsConnected && <Loader size="xs" color="yellow" variant="dots" />}
      </div>

      {/* ── Main content ── */}
      <div style={{ minHeight: 'calc(100vh - 108px)' }}>
        {authError && (
          <Alert color="red" m="md" withCloseButton onClose={() => setAuthError(null)}>
            {authError}
          </Alert>
        )}

        {selectedCamera ? (
          /* Single H264 view */
          <div style={{ padding: '1rem' }}>
            <Group mb="sm" spacing="xs">
              <Button size="xs" variant="subtle" onClick={() => switchToGrid(currentView)}>
                ← Back
              </Button>
              <Text color="white">{selectedCamera.name}</Text>
            </Group>
            <video
              ref={videoRef}
              autoPlay
              controls
              playsInline
              style={{ width: '100%', maxHeight: '80vh', background: '#000', display: 'block' }}
              onPause={() => {
                const token = tokenRef.current;
                peerListRef.current.forEach((p) => {
                  if (selectedCamera && p.hubId === selectedCamera.hub_id)
                    p.play(selectedCamera.id, FRAME.COMMAND_H264_STOP, token);
                });
              }}
              onPlay={() => {
                const token = tokenRef.current;
                peerListRef.current.forEach((p) => {
                  if (selectedCamera && p.hubId === selectedCamera.hub_id)
                    p.play(selectedCamera.id, FRAME.COMMAND_H264_PLAY, token);
                });
              }}
            />
          </div>
        ) : hubList === null ? (
          /* Loading */
          <Stack align="center" justify="center" style={{ height: '70vh' }} spacing="sm">
            <Loader color="blue" />
            <Text color="dimmed" size="sm">
              Connecting to camera server…
            </Text>
          </Stack>
        ) : allCameras.length === 0 ? (
          /* No cameras */
          <Stack align="center" justify="center" style={{ height: '70vh' }} spacing="sm">
            <IconCamera size={64} stroke={1} color="gray" />
            <Text color="dimmed">No cameras found.</Text>
            <Button size="sm" leftIcon={<IconPlus size={14} />} onClick={() => setRtspOpen(true)}>
              Add Camera
            </Button>
          </Stack>
        ) : (
          /* Camera grid */
          <SimpleGrid cols={currentView} p="md" spacing="sm">
            {allCameras.map((camera) => (
              <div
                key={`${camera.hub_id}-${camera.id}`}
                onClick={() => switchToCamera(camera)}
                style={{ cursor: 'pointer' }}
              >
                {/* Thumbnail container */}
                <div
                  style={{
                    position: 'relative',
                    background: '#0f1117',
                    aspectRatio: '16/9',
                    overflow: 'hidden',
                  }}
                >
                  <img
                    ref={(el) => {
                      if (el) imageRefsRef.current.set(camera.id, el);
                      else imageRefsRef.current.delete(camera.id);
                    }}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      display: 'block',
                    }}
                    alt={camera.name}
                  />
                  {/* Icon placeholder — hidden once first JPEG frame arrives */}
                  <div
                    ref={(el) => {
                      if (el) iconRefsRef.current.set(camera.id, el);
                      else iconRefsRef.current.delete(camera.id);
                    }}
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      pointerEvents: 'none',
                    }}
                  >
                    <IconCamera size={64} stroke={1} color="#555" />
                  </div>
                </div>
                <Text size="sm" align="center" color="dimmed" mt={4}>
                  {camera.name}
                </Text>
              </div>
            ))}
          </SimpleGrid>
        )}
      </div>

      {/* ── ONVIF modal ── */}
      <Modal opened={onvifOpen} onClose={() => setOnvifOpen(false)} title="Add ONVIF Camera">
        <Stack spacing="sm">
          <TextInput
            label="IP Address"
            placeholder="192.168.1.100"
            value={onvifIp}
            onChange={(e) => setOnvifIp(e.currentTarget.value)}
          />
          <TextInput
            label="Username"
            value={onvifUser}
            onChange={(e) => setOnvifUser(e.currentTarget.value)}
          />
          <TextInput
            label="Password"
            type="password"
            value={onvifPass}
            onChange={(e) => setOnvifPass(e.currentTarget.value)}
          />
          <Group position="right" mt="xs">
            <Button variant="subtle" onClick={() => setOnvifOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!onvifIp.trim() || onvifDisabled.current) return;
                onvifDisabled.current = true;
                sendWs({
                  command: FRAME.CONTROL_CMD,
                  method: 'getONVIFCameraStreams',
                  ip: onvifIp,
                  user: onvifUser,
                  pass: onvifPass,
                });
              }}
            >
              Discover & Continue
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* ── RTSP modal ── */}
      <Modal opened={rtspOpen} onClose={() => setRtspOpen(false)} title="Add RTSP Camera">
        <Stack spacing="sm">
          <TextInput
            label="RTSP URL"
            placeholder="rtsp://192.168.1.100:554/stream"
            value={rtspUrl}
            onChange={(e) => setRtspUrl(e.currentTarget.value)}
          />
          <Group position="right" mt="xs">
            <Button variant="subtle" onClick={() => setRtspOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!rtspUrl.trim() || rtspDisabled.current) return;
                rtspDisabled.current = true;
                sendWs({
                  command: FRAME.CONTROL_CMD,
                  method: 'checkRTSPCameraVideoUrl',
                  url: rtspUrl,
                });
              }}
            >
              Check & Continue
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* ── Add camera settings modal (step 2) ── */}
      <Modal opened={addCameraOpen} onClose={() => setAddCameraOpen(false)} title="Camera Settings">
        <Stack spacing="sm">
          <TextInput
            label="Camera Name"
            value={cameraName}
            onChange={(e) => setCameraName(e.currentTarget.value)}
          />
          <TextInput
            label="Location"
            value={cameraLocation}
            onChange={(e) => setCameraLocation(e.currentTarget.value)}
          />
          <Group position="right" mt="xs">
            <Button variant="subtle" onClick={() => setAddCameraOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!cameraName.trim() || addCamDisabled.current) return;
                addCamDisabled.current = true;
                sendWs({
                  command: FRAME.CONTROL_CMD,
                  method: 'addCamera',
                  name: cameraName,
                  location: cameraLocation,
                  ...addCameraDataRef.current,
                });
              }}
            >
              Add Camera
            </Button>
          </Group>
        </Stack>
      </Modal>
    </MainLayout>
  );
}
