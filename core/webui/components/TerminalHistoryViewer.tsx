import React from "react";
import Head from "next/head";

interface TerminalHistoryViewerProps {
  pageTitle: string;
  topBarText: string;
  loading: boolean;
  loadingText: string;
  error: string;
  content: string;
  fitParent?: boolean;
}

const TerminalHistoryViewer = ({
  pageTitle,
  topBarText,
  loading,
  loadingText,
  error,
  content,
  fitParent = false,
}: TerminalHistoryViewerProps) => {
  return (
    <>
      <Head>
        <title>{pageTitle}</title>
      </Head>
      <main className={`${fitParent ? "h-full" : "h-screen"} bg-[#0b0f19] text-[#d7e2ff] flex flex-col overflow-hidden`}>
        <div className="h-[42px] border-b border-[#2f3645] px-4 flex items-center bg-[#121826] flex-shrink-0">
          <div className="text-sm font-medium whitespace-nowrap overflow-hidden text-ellipsis">
            {topBarText}
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-auto bg-[#0b0f19]">
          {loading ? (
            <div className="h-full flex items-center justify-center text-sm text-[#9fb0d9]">
              {loadingText}
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center p-6 text-sm text-[#ff9ca8]">
              {error}
            </div>
          ) : (
            <pre className="min-h-full w-full p-4 m-0 whitespace-pre-wrap break-words font-mono text-[13px] leading-5 text-[#d7e2ff] select-text">
              {content || "\n"}
            </pre>
          )}
        </div>
      </main>
    </>
  );
};

export default TerminalHistoryViewer;
