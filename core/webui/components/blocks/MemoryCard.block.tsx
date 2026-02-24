import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import yaml from "js-yaml";
import RJSON from "relaxed-json";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkStringify from "remark-stringify";
import MarkdownRenderer from "./MarkdownRenderer";

type CardItem = {
  front: string;
  back: string;
};

const parseCards = (raw: string): CardItem[] => {
  try {
    const data: any = yaml.load(raw) || [];
    const list = Array.isArray(data) ? data : Array.isArray(data?.cards) ? data.cards : [];
    return list
      .map((item: any) => ({
        front: String(item?.front ?? "").trim(),
        back: String(item?.back ?? "").trim(),
      }))
      .filter((item: CardItem) => item.front.length > 0 && item.back.length > 0);
  } catch (err) {
    console.error(err);
    return [];
  }
};

const parseSlidesLikeCards = (raw: string): CardItem[] => {
  try {
    const ast: any = unified().use(remarkParse).parse(raw || "");
    const byName: Record<string, { title?: string; front?: string; back?: string }> = {};
    const order: string[] = [];

    for (const node of ast.children || []) {
      if (node?.type !== "code") continue;
      let blockMeta: any = {};
      try {
        if (node.meta) blockMeta = RJSON.parse(node.meta ?? "{}");
      } catch {
        blockMeta = {};
      }
      const cardName = String(blockMeta.card_name || "").trim();
      const cardFace = String(blockMeta.card_face || "").trim().toLowerCase();
      if (!cardName) continue;
      if (cardFace !== "front" && cardFace !== "back") continue;

      if (!byName[cardName]) {
        byName[cardName] = {};
        order.push(cardName);
      }

      const markdown = unified().use(remarkStringify).stringify({ type: "root", children: [node] }).trim();
      if (!markdown) continue;

      if (cardFace === "front") {
        byName[cardName].front = byName[cardName].front ? `${byName[cardName].front}\n\n${markdown}` : markdown;
      } else {
        byName[cardName].back = byName[cardName].back ? `${byName[cardName].back}\n\n${markdown}` : markdown;
      }
    }

    return order
      .map((name) => ({
        front: String(byName[name].front || "").trim(),
        back: String(byName[name].back || "").trim(),
      }))
      .filter((item) => item.front.length > 0 && item.back.length > 0);
  } catch (err) {
    console.error(err);
    return [];
  }
};

const MemoryCardBlock = (props: any) => {
  const callbackRef = useRef(false);
  const [flipped, setFlipped] = useState<Record<number, boolean>>({});

  let meta: any = {};
  try {
    if (props.meta) {
      meta = RJSON.parse(props.meta ?? "{}");
    }
  } catch (err: any) {
    console.error(err?.message || err);
  }

  const cards = useMemo(() => {
    const raw = props.content || "";
    const yamlCards = parseCards(raw);
    const slidesLikeCards = parseSlidesLikeCards(raw);
    const parsed = slidesLikeCards.length > 0 ? slidesLikeCards : yamlCards;
    return parsed.slice(0, 9);
  }, [props.content]);

  useEffect(() => {
    if (props.callback) {
      if (callbackRef.current) return;
      callbackRef.current = true;
      props.callback(props.index, 1);
    }
  }, []);

  const visibleCards = cards.length >= 3 ? cards : cards.slice(0, cards.length);
  const cardMinHeight = Number(meta.cardMinHeight || 180);

  const toggle = (index: number) => {
    setFlipped((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  if (visibleCards.length === 0) {
    return (
      <div className="mb-6 rounded-xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-500">
        Memory card block requires 3 to 9 cards with front/back fields, or slides-style blocks using card_name/card_face.
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-700">{meta.title || "Memory Cards"}</div>
        <div className="text-xs text-slate-500">Click any card to flip</div>
      </div>

      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        }}
      >
        {visibleCards.map((card, idx) => {
          const isFlipped = Boolean(flipped[idx]);
          return (
            <button
              key={idx}
              type="button"
              onClick={() => toggle(idx)}
              className="group relative w-full rounded-xl border border-slate-200 text-left"
              style={{ perspective: "1000px", minHeight: cardMinHeight }}
            >
              <div
                className="relative h-full w-full rounded-xl transition-transform duration-400"
                style={{
                  transformStyle: "preserve-3d",
                  transform: isFlipped ? "rotateY(180deg)" : "rotateY(0deg)",
                }}
              >
                <div
                  className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-50 to-white p-3"
                  style={{ backfaceVisibility: "hidden" }}
                >
                  <div className="prose max-w-none prose-sm">
                    <MarkdownRenderer markdown={card.front} />
                  </div>
                </div>

                <div
                  className="absolute inset-0 rounded-xl bg-gradient-to-br from-emerald-50 to-white p-3"
                  style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
                >
                  <div className="prose max-w-none prose-sm">
                    <MarkdownRenderer markdown={card.back} />
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default memo(MemoryCardBlock);
