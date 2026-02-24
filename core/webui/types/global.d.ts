export {};

declare global {
  interface Window {
    MathJax?: {
      typeset?: () => void;
      typesetClear?: () => void;
    };
  }
}
