export const timeHandler = (timeStr: string): string => {
  const date = new Date(timeStr);
  const diff = (Date.now() - date.getTime()) / 1000; // 毫秒转成秒

  if (diff < 60) {
    return `${Math.floor(diff)} seconds ago`;
  } else if (diff < 3600) {
    return `${Math.floor(diff / 60)} minutes ago`;
  } else if (diff < 86400) {
    return `${Math.floor(diff / 3600)} hours ago`;
  } else {
    return `${Math.floor(diff / 86400)} days ago`;
  }
};

export const timeHandler2 = (timestamp: string): string => {
  const date = new Date(timestamp);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    // 如果是今天，显示 小时:分钟 的格式
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${hours}:${minutes}`;
  } else {
    // 否则显示 小时, 分钟, 日期 的格式
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${hours}:${minutes}, ${year}-${month}-${day}`;
  }
};

export function generateFormattedDate() {
  const date = new Date();

  // 获取年份、月份、日期、小时、分钟和秒数
  const year = date.getFullYear().toString().padStart(4, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  const seconds = date.getSeconds().toString().padStart(2, "0");

  // 拼接生成ISO 8601格式的时间字符串
  const formattedDate = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.000Z`;

  return formattedDate;
}

export const encodeBase64 = (str: string) => {
  const buffer = Buffer.from(str);
  return buffer.toString("base64");
};

export const decodeBase64 = (str: string) => {
  const buffer = Buffer.from(str, "base64");
  return buffer.toString("utf-8");
};

export class Throttle {
  private timeout: NodeJS.Timeout | undefined;

  constructor() {}

  public onHandle(func: () => void, wait: number) {
    if (this.timeout) {
      clearTimeout(this.timeout);
    }
    this.timeout = setTimeout(() => {
      func();
    }, wait);
  }
}

export function smoothScrollTo(
  x: number,
  y: number,
  duration: number,
  onScroll: (value: number) => void
) {
  const start = window.scrollY;
  const change = y - start;
  const startTime = performance.now();

  function animateScroll(currentTime: number) {
    const elapsedTime = currentTime - startTime;
    const easing = easeInOutQuad(elapsedTime, start, change, duration);
    onScroll(easing);

    if (elapsedTime < duration) {
      requestAnimationFrame(animateScroll);
    }
  }

  function easeInOutQuad(t: number, b: number, c: number, d: number): number {
    t /= d / 2;
    if (t < 1) return (c / 2) * t * t + b;
    t--;
    return (-c / 2) * (t * (t - 2) - 1) + b;
  }

  requestAnimationFrame(animateScroll);
}

const eventEmitter = new EventTarget();

export default eventEmitter;

//eventName
export const ASSIGNED_AND_REFRESH = "assigned-task-need-refresh";
