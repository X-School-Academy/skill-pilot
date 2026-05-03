package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

var (
	listenAddr string
	targetBase string
	allowIP    string
	tunnelURL  string
	tunnelPool int
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

// isAllowed checks the request's remote IP against the allowIP setting.
// "*" permits any address; otherwise the client IP must match exactly.
func isAllowed(r *http.Request) bool {
	if allowIP == "*" {
		return true
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		host = r.RemoteAddr
	}
	return host == allowIP
}

func copyHeaders(dst, src http.Header) {
	for k, vv := range src {
		// Skip hop-by-hop / handshake-managed headers.
		switch http.CanonicalHeaderKey(k) {
		case "Connection", "Upgrade", "Sec-Websocket-Key", "Sec-Websocket-Version",
			"Sec-Websocket-Extensions", "Sec-Websocket-Accept":
			continue
		}
		for _, v := range vv {
			dst.Add(k, v)
		}
	}
}

// relay runs the bidirectional pump between two already-connected websockets.
// It is shared by forward-proxy mode (incoming local client ↔ upstream Chrome)
// and tunnel-client mode (outbound parked tunnel ↔ upstream Chrome).
func relay(client, upstream *websocket.Conn, label string) {
	client.SetReadLimit(32 << 20)
	upstream.SetReadLimit(32 << 20)

	var once sync.Once
	closeBoth := func() {
		once.Do(func() {
			_ = client.Close()
			_ = upstream.Close()
		})
	}

	pipe := func(dst, src *websocket.Conn, name string) {
		defer closeBoth()
		for {
			msgType, reader, err := src.NextReader()
			if err != nil {
				if !websocket.IsCloseError(err,
					websocket.CloseNormalClosure,
					websocket.CloseGoingAway,
					websocket.CloseNoStatusReceived) {
					log.Printf("[%s] read error: %v", name, err)
				}
				return
			}
			writer, err := dst.NextWriter(msgType)
			if err != nil {
				log.Printf("[%s] write open error: %v", name, err)
				return
			}
			if _, err := io.Copy(writer, reader); err != nil {
				_ = writer.Close()
				log.Printf("[%s] copy error: %v", name, err)
				return
			}
			if err := writer.Close(); err != nil {
				log.Printf("[%s] write close error: %v", name, err)
				return
			}
		}
	}

	client.SetPingHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return upstream.WriteControl(websocket.PingMessage, []byte(appData), deadline)
	})
	client.SetPongHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return upstream.WriteControl(websocket.PongMessage, []byte(appData), deadline)
	})
	upstream.SetPingHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return client.WriteControl(websocket.PingMessage, []byte(appData), deadline)
	})
	upstream.SetPongHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return client.WriteControl(websocket.PongMessage, []byte(appData), deadline)
	})

	go pipe(upstream, client, label+":client->upstream")
	pipe(client, upstream, label+":upstream->client")
}

func proxyWS(w http.ResponseWriter, r *http.Request) {
	targetURL, err := url.Parse(targetBase + r.URL.RequestURI())
	if err != nil {
		http.Error(w, "bad target url", http.StatusInternalServerError)
		return
	}

	// Upgrade incoming client connection.
	clientConn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[client] upgrade error: %v", err)
		return
	}
	defer clientConn.Close()

	dialer := websocket.Dialer{
		Proxy:            http.ProxyFromEnvironment,
		HandshakeTimeout: 10 * time.Second,
	}

	reqHeader := http.Header{}
	copyHeaders(reqHeader, r.Header)

	upstreamConn, resp, err := dialer.Dial(targetURL.String(), reqHeader)
	if err != nil {
		if resp != nil {
			log.Printf("[upstream] dial error: %v (status=%s)", err, resp.Status)
		} else {
			log.Printf("[upstream] dial error: %v", err)
		}
		_ = clientConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "upstream unavailable"),
			time.Now().Add(2*time.Second),
		)
		return
	}
	defer upstreamConn.Close()

	log.Printf("[proxy] connected %s -> %s", r.RemoteAddr, targetURL.String())
	relay(clientConn, upstreamConn, "proxy")
	log.Printf("[proxy] disconnected %s", r.RemoteAddr)
}

// controlFrame is the single text message the engine sends on the parked
// tunnel right after a local CDP client arrives. It tells the remote Go
// proxy which Chrome target path to dial. After this frame, traffic is
// transparent CDP frames in both directions.
type controlFrame struct {
	Path string `json:"path"`
}

// runTunnelWorker maintains one parked tunnel connection forever (with backoff).
// Each successful tunnel handles exactly one CDP session, then re-dials.
func runTunnelWorker(workerID int, stop <-chan struct{}) {
	backoff := time.Second
	maxBackoff := 30 * time.Second

	for {
		select {
		case <-stop:
			return
		default:
		}

		if err := dialAndServeTunnel(workerID); err != nil {
			log.Printf("[tunnel-%d] %v; retrying in %s", workerID, err, backoff)
			select {
			case <-stop:
				return
			case <-time.After(backoff):
			}
			if backoff < maxBackoff {
				backoff *= 2
				if backoff > maxBackoff {
					backoff = maxBackoff
				}
			}
			continue
		}
		backoff = time.Second
	}
}

func dialAndServeTunnel(workerID int) error {
	dialer := websocket.Dialer{
		Proxy:            http.ProxyFromEnvironment,
		HandshakeTimeout: 15 * time.Second,
	}

	tunnelConn, resp, err := dialer.Dial(tunnelURL, nil)
	if err != nil {
		if resp != nil {
			return &tunnelError{stage: "dial", err: err, status: resp.Status}
		}
		return &tunnelError{stage: "dial", err: err}
	}
	defer tunnelConn.Close()

	log.Printf("[tunnel-%d] parked at %s", workerID, redactedTunnelURL())

	tunnelConn.SetReadLimit(32 << 20)

	// Block until the engine sends the control frame (when a local client connects).
	msgType, msg, err := tunnelConn.ReadMessage()
	if err != nil {
		return &tunnelError{stage: "wait-control", err: err}
	}
	if msgType != websocket.TextMessage {
		_ = tunnelConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseProtocolError, "expected text control frame"),
			time.Now().Add(2*time.Second),
		)
		return &tunnelError{stage: "wait-control", err: errStringf("non-text control frame: type=%d", msgType)}
	}

	var ctrl controlFrame
	if err := json.Unmarshal(msg, &ctrl); err != nil {
		_ = tunnelConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseProtocolError, "bad control frame json"),
			time.Now().Add(2*time.Second),
		)
		return &tunnelError{stage: "parse-control", err: err}
	}
	if ctrl.Path == "" || !strings.HasPrefix(ctrl.Path, "/") {
		_ = tunnelConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseProtocolError, "missing or invalid path"),
			time.Now().Add(2*time.Second),
		)
		return &tunnelError{stage: "parse-control", err: errStringf("invalid path: %q", ctrl.Path)}
	}

	upstreamURL := targetBase + ctrl.Path
	log.Printf("[tunnel-%d] session opening, upstream=%s", workerID, upstreamURL)

	upstreamConn, resp, err := dialer.Dial(upstreamURL, nil)
	if err != nil {
		status := ""
		if resp != nil {
			status = resp.Status
		}
		_ = tunnelConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "upstream unavailable"),
			time.Now().Add(2*time.Second),
		)
		return &tunnelError{stage: "dial-upstream", err: err, status: status}
	}
	defer upstreamConn.Close()

	relay(tunnelConn, upstreamConn, "tunnel")
	log.Printf("[tunnel-%d] session closed", workerID)
	return nil
}

type tunnelError struct {
	stage  string
	err    error
	status string
}

func (e *tunnelError) Error() string {
	if e.status != "" {
		return e.stage + ": " + e.err.Error() + " (status=" + e.status + ")"
	}
	return e.stage + ": " + e.err.Error()
}

func errStringf(format string, args ...any) error {
	return fmt.Errorf(format, args...)
}

// localIP returns the first non-loopback IPv4 address, or "localhost" as fallback.
func localIP() string {
	ifaces, err := net.Interfaces()
	if err != nil {
		return "localhost"
	}
	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}
			if ip == nil || ip.IsLoopback() || ip.To4() == nil {
				continue
			}
			return ip.String()
		}
	}
	return "localhost"
}

// redactedTunnelURL strips the token query value for logs.
func redactedTunnelURL() string {
	u, err := url.Parse(tunnelURL)
	if err != nil {
		return tunnelURL
	}
	q := u.Query()
	if q.Get("token") != "" {
		q.Set("token", "***")
		u.RawQuery = q.Encode()
	}
	return u.String()
}

func main() {
	flag.StringVar(&listenAddr, "listenAddr", "0.0.0.0:9223", "Forward-proxy mode: address to listen on (e.g. 0.0.0.0:9223). Ignored when -tunnelURL is set.")
	flag.StringVar(&targetBase, "targetBase", "ws://127.0.0.1:9222", "Upstream WebSocket target base URL (e.g. ws://127.0.0.1:9222)")
	flag.StringVar(&allowIP, "allowIP", "*", "Forward-proxy mode: remote IP allowed to connect; '*' permits any address. Ignored when -tunnelURL is set.")
	flag.StringVar(&tunnelURL, "tunnelURL", "", "Optional. If set, run in tunnel-client mode and dial out to this ws://or wss:// URL (e.g. wss://engine.example.com/chrome-proxy?token=abc).")
	flag.IntVar(&tunnelPool, "tunnelPool", 1, "Tunnel-client mode: number of concurrent parked tunnels.")
	flag.Parse()

	if tunnelURL != "" {
		runTunnelMode()
		return
	}
	runForwardMode()
}

func runForwardMode() {
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if !isAllowed(r) {
			host, _, _ := net.SplitHostPort(r.RemoteAddr)
			log.Printf("[proxy] rejected connection from %s (not in allow-ip: %s)", host, allowIP)
			http.Error(w, "forbidden", http.StatusForbidden)
			return
		}
		// Chrome DevTools clients typically connect to:
		// /devtools/browser/<id>
		if websocket.IsWebSocketUpgrade(r) {
			proxyWS(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ws proxy is running\n"))
	})

	server := &http.Server{
		Addr:              listenAddr,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("[proxy] listening on ws://%s", listenAddr)
		log.Printf("[proxy] forwarding to %s", targetBase)
		if allowIP == "*" {
			log.Printf("[proxy] allow-ip: any")
		} else {
			log.Printf("[proxy] allow-ip: %s only", allowIP)
		}
		_, port, _ := net.SplitHostPort(listenAddr)
		ip := localIP()
		log.Printf("[proxy] connect from remote: agent-browser open URL --cdp ws://%s:%s/devtools/browser/", ip, port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[proxy] server error: %v", err)
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	<-sigCh
	log.Printf("[proxy] shutting down")
	_ = server.Close()
}

func runTunnelMode() {
	if tunnelPool < 1 {
		tunnelPool = 1
	}
	log.Printf("[tunnel] mode: dialing %s with pool=%d", redactedTunnelURL(), tunnelPool)
	log.Printf("[tunnel] upstream Chrome target base: %s", targetBase)
	if listenAddr != "0.0.0.0:9223" {
		log.Printf("[tunnel] note: -listenAddr is ignored in tunnel mode")
	}
	if allowIP != "*" {
		log.Printf("[tunnel] note: -allowIP is ignored in tunnel mode")
	}

	stop := make(chan struct{})
	var wg sync.WaitGroup
	for i := 0; i < tunnelPool; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			runTunnelWorker(id, stop)
		}(i)
	}

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	<-sigCh
	log.Printf("[tunnel] shutting down")
	close(stop)
	// Give workers a brief window to exit; their dials/relays will unblock on Close.
	done := make(chan struct{})
	go func() { wg.Wait(); close(done) }()
	select {
	case <-done:
	case <-time.After(3 * time.Second):
	}
}
