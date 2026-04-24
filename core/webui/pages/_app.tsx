import "../styles/globals.css";
import "@xterm/xterm/css/xterm.css";
import "@svar-ui/react-filemanager/all.css";
import type { AppProps } from "next/app";
import type { NextComponentType, NextPage } from "next";
import { ReactElement, ReactNode, useEffect, useState } from "react";
import { Provider } from "react-redux";
import store from "../store";
import Layout from "../components/layout";
import { appWithTranslation } from "next-i18next";
import { MantineProvider, createEmotionCache } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import TipsModal from "../components/tips-modal";
import Script from 'next/script'
import { getApiBase, probeApiHealth, waitForApiReady } from "../libs/api-base";

export type NextPageWithLayout<P = {}, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

const WrapLayout = ({ ChildComponent, childPageProps }: any) => {
  if (ChildComponent.useLayout) {
    return (
      <Layout>
        <ChildComponent {...childPageProps} />
      </Layout>
    );
  } else {
    return <ChildComponent {...childPageProps} />;
  }
};

function App({ Component, pageProps }: AppPropsWithLayout) {
  // Creating emotion cache 📦
  const cache = createEmotionCache({ key: "css" });
  const [bootState, setBootState] = useState<"checking" | "ready" | "degraded">("checking");
  const [bootMessage, setBootMessage] = useState("Waiting for the core engine to finish starting.");

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const result = await waitForApiReady({
        maxWaitMs: 20000,
        intervalMs: 600,
        requestTimeoutMs: 1200,
      });

      if (cancelled) return;

      if (result.ready) {
        if (typeof window !== "undefined") {
          const url = new URL(window.location.href);
          const urlToken = (url.searchParams.get("token") || "").trim();
          if (urlToken) {
            try {
              await fetch(`${getApiBase()}/api/auth/session`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ auth_token: urlToken }),
              });
            } finally {
              // Remove the token from the URL even if auth fails so it is not left in browser history.
              url.searchParams.delete("token");
              window.history.replaceState({}, "", url.toString());
            }
          }
        }
        setBootState("ready");
        return;
      }

      setBootState("degraded");
      setBootMessage("The engine is taking longer than expected. You can keep waiting or continue anyway.");
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (bootState !== "ready") {
      return;
    }

    const currentPath = window.location.pathname;
    const isTerminalPage = currentPath === "/terminal" || currentPath.startsWith("/terminal/");
    if (window.self !== window.top && isTerminalPage) {
      // Avoid heartbeat/cleanup from embedded terminal iframes.
      return;
    }

    // Heartbeat: notify backend every 5s that the browser is alive.
    const heartbeatUrl = `${getApiBase()}/api/heartbeat`;
    const sendHeartbeat = () => {
      void fetch(heartbeatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
        keepalive: true,
      }).catch(() => {});
    };
    sendHeartbeat();
    const heartbeatInterval = window.setInterval(sendHeartbeat, 5000);

    // Session cleanup relies on the heartbeat timeout (10s) in the backend.
    // No beforeunload cleanup — it fires on normal page navigation too,
    // which would kill sessions prematurely.

    return () => {
      window.clearInterval(heartbeatInterval);
    };
  }, [bootState]);

  useEffect(() => {
    if (bootState !== "degraded") {
      return;
    }

    let cancelled = false;

    const intervalId = window.setInterval(() => {
      void probeApiHealth().then((ready) => {
        if (!cancelled && ready) {
          setBootState("ready");
        }
      });
    }, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [bootState]);

  const bootScreen = (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        background:
          "radial-gradient(circle at top, rgba(99, 102, 241, 0.16), transparent 35%), linear-gradient(180deg, #f8fbff 0%, #edf2ff 100%)",
      }}
    >
      <div
        style={{
          width: "min(32rem, 100%)",
          padding: "2rem",
          borderRadius: "1.5rem",
          border: "1px solid rgba(76, 93, 175, 0.16)",
          background: "rgba(255, 255, 255, 0.92)",
          boxShadow: "0 24px 60px rgba(31, 41, 85, 0.12)",
          color: "#172554",
        }}
      >
        <div
          style={{
            width: "3rem",
            height: "3rem",
            borderRadius: "999px",
            border: "3px solid rgba(99, 102, 241, 0.18)",
            borderTopColor: "#4f46e5",
            animation: "skill-pilot-boot-spin 0.9s linear infinite",
            marginBottom: "1.25rem",
          }}
        />
        <h1 style={{ margin: 0, fontSize: "1.5rem", lineHeight: 1.2 }}>Starting Skill Pilot</h1>
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.98rem", color: "#475569" }}>{bootMessage}</p>
        <p style={{ margin: "0.5rem 0 0", fontSize: "0.88rem", color: "#64748b" }}>
          The UI waits for the backend health check at <code>/api/health</code> before mounting screens that fetch data on load.
        </p>
        {bootState === "degraded" && (
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.25rem", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{
                border: 0,
                borderRadius: "999px",
                padding: "0.75rem 1rem",
                background: "#4f46e5",
                color: "#fff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Retry startup
            </button>
            <button
              type="button"
              onClick={() => setBootState("ready")}
              style={{
                borderRadius: "999px",
                padding: "0.75rem 1rem",
                background: "transparent",
                color: "#334155",
                border: "1px solid rgba(100, 116, 139, 0.3)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Continue anyway
            </button>
          </div>
        )}
      </div>
      <style jsx global>{`
        @keyframes skill-pilot-boot-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );

  return (<>
    <Provider store={store}>
      <MantineProvider
        withGlobalStyles
        withNormalizeCSS
        emotionCache={cache}
        theme={{
          colors:{
            brand: ['#eaecff','#c6c9ee','#a2a5dd','#7d82ce','#595ec0','#3f44a6','#313582','#22265e','#14173b','#05071a',],
          },
          primaryColor: 'brand',
        }}
      >
        <Notifications />
        <ModalsProvider modals={{tipsModal: TipsModal}}>
          {bootState === "ready" ? (
            <WrapLayout ChildComponent={Component} childPageProps={pageProps} />
          ) : (
            bootScreen
          )}
        </ModalsProvider>
      </MantineProvider>
    </Provider>
    

    <Script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" onLoad={()=>{
      if( typeof window?.MathJax !== "undefined"){
        //window.MathJax.typesetClear()
        // fix one firefox or other refresh issue
        setTimeout(()=>window.MathJax?.typeset?.(), 100)
      }
    }}></Script>
    </>
  );
}

export default appWithTranslation(App);
