import "../styles/globals.css";
import "@xterm/xterm/css/xterm.css";
import type { AppProps } from "next/app";
import type { NextComponentType, NextPage } from "next";
import { ReactElement, ReactNode, useEffect } from "react";
import { Provider } from "react-redux";
import store from "../store";
import Layout from "../components/layout";
import { appWithTranslation } from "next-i18next";
import { MantineProvider, createEmotionCache } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import TipsModal from "../components/tips-modal";
import Script from 'next/script'
import { getApiBase } from "../libs/api-base";

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

  useEffect(() => {
    if (window.self !== window.top) {
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
  }, []);

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
          <WrapLayout ChildComponent={Component} childPageProps={pageProps} />
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
