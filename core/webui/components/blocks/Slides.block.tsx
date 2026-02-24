import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkStringify from "remark-stringify";
import RJSON from "relaxed-json";
import MarkdownRenderer from "./MarkdownRenderer";

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const SlidesBlock = (props: any) => {
  const callbackRef = useRef(false);
  const [current, setCurrent] = useState(0);
  const startXRef = useRef<number | null>(null);
  const deltaXRef = useRef(0);

  let content = props.content || "";
  content = content.replaceAll("\\```", "```").replaceAll("\\`\\`\\`", "```");

  let meta: any = {};
  try {
    if (props.meta) {
      meta = RJSON.parse(props.meta ?? "{}");
    }
  } catch (err: any) {
    console.error(err?.message || err);
  }

  const ast: any = useMemo(() => unified().use(remarkParse).parse(content), [content]);
  const slides = useMemo(() => {
    const root = ast || { children: [] };
    return (root.children || [])
      .map((node: any, index: number) => {
        const markdown = unified().use(remarkStringify).stringify({ type: "root", children: [node] });
        return { index, markdown };
      })
      .filter((item: any) => (item.markdown || "").trim().length > 0);
  }, [ast]);

  const slideCount = slides.length;
  const minHeight = Number(meta.minHeight || 220);

  useEffect(() => {
    if (props.callback) {
      if (callbackRef.current) return;
      callbackRef.current = true;
      props.callback(props.index, 1);
    }
  }, []);

  useEffect(() => {
    setCurrent((prev) => clamp(prev, 0, Math.max(slideCount - 1, 0)));
  }, [slideCount]);

  const goPrev = () => setCurrent((prev) => clamp(prev - 1, 0, Math.max(slideCount - 1, 0)));
  const goNext = () => setCurrent((prev) => clamp(prev + 1, 0, Math.max(slideCount - 1, 0)));

  const onPointerDown = (e: React.PointerEvent) => {
    startXRef.current = e.clientX;
    deltaXRef.current = 0;
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (startXRef.current == null) return;
    deltaXRef.current = e.clientX - startXRef.current;
  };

  const onPointerUp = () => {
    if (startXRef.current == null) return;
    const delta = deltaXRef.current;
    if (Math.abs(delta) > 40) {
      if (delta < 0) goNext();
      if (delta > 0) goPrev();
    }
    startXRef.current = null;
    deltaXRef.current = 0;
  };

  if (slideCount === 0) {
    return (
      <div className="mb-6 rounded-xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-500">
        No slides content found.
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-slate-200 bg-white/90 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="text-sm font-semibold text-slate-700">Slides</div>
        <div className="text-xs text-slate-500">
          {current + 1} / {slideCount}
        </div>
      </div>

      <div
        className="relative overflow-hidden"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="flex transition-transform duration-300 ease-out"
          style={{ transform: `translateX(-${current * 100}%)` }}
        >
          {slides.map((slide: any) => (
            <div key={slide.index} className="w-full shrink-0 px-4 py-4" style={{ minHeight }}>
              <MarkdownRenderer markdown={slide.markdown} />
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
        <button
          type="button"
          onClick={goPrev}
          disabled={current <= 0}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Left
        </button>

        <div className="flex items-center gap-2">
          {slides.map((_: any, idx: number) => (
            <button
              key={idx}
              type="button"
              onClick={() => setCurrent(idx)}
              aria-label={`Go to slide ${idx + 1}`}
              className={`h-2.5 w-2.5 rounded-full transition-all ${idx === current ? "bg-blue-500" : "bg-slate-300 hover:bg-slate-400"}`}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={goNext}
          disabled={current >= slideCount - 1}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Right
        </button>
      </div>
    </div>
  );
};

export default memo(SlidesBlock);
