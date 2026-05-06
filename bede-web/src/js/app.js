import Alpine from "alpinejs";
import { marked } from "marked";
import DOMPurify from "dompurify";

window.Alpine = Alpine;

window.renderMarkdown = (md) => {
  return DOMPurify.sanitize(marked.parse(md || ""));
};

window.api = async (path) => {
  try {
    const res = await fetch(`/api${path}`);
    if (!res.ok) {
      return { error: `HTTP ${res.status}`, data: null };
    }
    return { error: null, data: await res.json() };
  } catch (e) {
    return { error: e.message, data: null };
  }
};

Alpine.start();
