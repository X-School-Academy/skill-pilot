package main

import (
	"flag"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

var (
	listenAddr string
	targetBase string
	allowIP    string
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

	// Dial upstream target.
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

		// Tell client the upstream is unavailable.
		_ = clientConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "upstream unavailable"),
			time.Now().Add(2*time.Second),
		)
		return
	}
	defer upstreamConn.Close()

	log.Printf("[proxy] connected %s -> %s", r.RemoteAddr, targetURL.String())

	// Keep read limits reasonable for a debug proxy; adjust if needed.
	clientConn.SetReadLimit(32 << 20)
	upstreamConn.SetReadLimit(32 << 20)

	var once sync.Once
	closeBoth := func() {
		once.Do(func() {
			_ = clientConn.Close()
			_ = upstreamConn.Close()
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

	// Forward pings/pongs/close cleanly enough for a simple proxy.
	clientConn.SetPingHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return upstreamConn.WriteControl(websocket.PingMessage, []byte(appData), deadline)
	})
	clientConn.SetPongHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return upstreamConn.WriteControl(websocket.PongMessage, []byte(appData), deadline)
	})
	upstreamConn.SetPingHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return clientConn.WriteControl(websocket.PingMessage, []byte(appData), deadline)
	})
	upstreamConn.SetPongHandler(func(appData string) error {
		deadline := time.Now().Add(5 * time.Second)
		return clientConn.WriteControl(websocket.PongMessage, []byte(appData), deadline)
	})

	go pipe(upstreamConn, clientConn, "client->upstream")
	pipe(clientConn, upstreamConn, "upstream->client")

	log.Printf("[proxy] disconnected %s", r.RemoteAddr)
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

func main() {
	flag.StringVar(&listenAddr, "listenAddr", "0.0.0.0:9223", "Address to listen on (e.g. 0.0.0.0:9223)")
	flag.StringVar(&targetBase, "targetBase", "ws://127.0.0.1:9222", "Upstream WebSocket target base URL (e.g. ws://127.0.0.1:9222)")
	flag.StringVar(&allowIP, "allowIP", "*", "Remote IP allowed to connect; '*' permits any address (e.g. 192.168.1.50)")
	flag.Parse()

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

		// Print remote connection hint.
		_, port, _ := net.SplitHostPort(listenAddr)
		ip := localIP()
		log.Printf("[proxy] connect from remote: agent-browser open URL --cdp ws://%s:%s/devtools/browser/", ip, port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[proxy] server error: %v", err)
		}
	}()

	// Graceful shutdown on Ctrl+C
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	<-sigCh

	log.Printf("[proxy] shutting down")
	shutdownCtx, cancel := signal.NotifyContext(nil)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)
}
