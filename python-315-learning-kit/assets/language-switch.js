(() => {
  "use strict";

  const payload = document.getElementById("guide-translations");
  if (!payload) return;
  const translations = JSON.parse(payload.textContent);
  const storageKey = "python315-guide-language";
  const elements = Array.from(document.querySelectorAll("[data-i18n]"));
  const originals = new Map(elements.map((element) => [element, element.innerHTML]));
  const navigation = Array.from(document.querySelectorAll("nav a[data-heading]"));
  const images = Array.from(document.querySelectorAll("img[data-diagram]"));
  const originalImages = new Map(images.map((image) => [image, {
    src: image.getAttribute("src"),
    alt: image.getAttribute("alt"),
  }]));
  const buttons = Array.from(document.querySelectorAll("button[data-language]"));
  const status = document.getElementById("language-status");
  const originalTitle = document.title;

  function normalizeLanguage(value) {
    if (typeof value !== "string") return null;
    if (value.toLowerCase() === "en") return "en";
    if (["zh", "zh-hant", "zh-tw"].includes(value.toLowerCase())) return "zh-Hant";
    return null;
  }

  function savedLanguage() {
    try {
      return normalizeLanguage(window.localStorage.getItem(storageKey));
    } catch {
      return null;
    }
  }

  function readingPosition() {
    const toolbar = document.querySelector(".language-bar");
    const offset = (toolbar ? toolbar.getBoundingClientRect().height : 0) + 16;
    const main = document.querySelector("main");
    const mainBounds = main.getBoundingClientRect();
    // Leave the title and contents in place until the reader enters the article.
    if (mainBounds.top > offset || mainBounds.bottom <= offset) return null;
    let overlapping = null;
    let following = null;
    let previous = null;
    for (const element of document.querySelectorAll("main [data-i18n], main pre, main tr, main figure")) {
      // A translated parent replaces its children; bookmark only a stable node.
      if (element.parentElement.closest("[data-i18n]")) continue;
      const bounds = element.getBoundingClientRect();
      const top = bounds.top;
      const position = { element, top };
      if (top <= offset && bounds.bottom > offset && (!overlapping || top > overlapping.top)) overlapping = position;
      if (top > offset && (!following || top < following.top)) following = position;
      if (top <= offset && (!previous || top > previous.top)) previous = position;
    }
    // A chapter often starts just below the reading line after anchor navigation.
    return overlapping || following || previous;
  }

  function applyLanguage(language, { initial = false, fromHistory = false } = {}) {
    const selected = normalizeLanguage(language) || "zh-Hant";
    if (!initial && document.documentElement.dataset.language === selected) return;
    const english = selected === "en";
    const position = initial || fromHistory ? null : readingPosition();

    for (const element of elements) {
      const key = element.dataset.i18n;
      element.innerHTML = english ? translations.messages[key] : originals.get(element);
    }

    // Keep one set of section IDs so existing links work in either language.
    for (const anchor of navigation) {
      const heading = document.getElementById(anchor.dataset.heading);
      if (heading) anchor.textContent = heading.textContent;
    }

    for (const image of images) {
      const value = english ? translations.diagrams[image.dataset.diagram] : originalImages.get(image);
      image.setAttribute("src", value.src);
      image.setAttribute("alt", value.alt);
    }

    document.documentElement.lang = selected;
    document.documentElement.dataset.language = selected;
    document.title = english ? translations.title : originalTitle;
    document.querySelector("nav").setAttribute("aria-label", english ? "Chapter contents" : "章節目錄");
    document.querySelector(".language-buttons").setAttribute("aria-label", english ? "Reading language" : "閱讀語言");

    for (const button of buttons) {
      button.setAttribute("aria-pressed", String(button.dataset.language === selected));
    }

    try {
      window.localStorage.setItem(storageKey, selected);
    } catch {
      // The current selection still works when file:// or privacy settings block storage.
    }

    if (!fromHistory) {
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("lang", selected === "en" ? "en" : "zh-Hant");
        window.history.replaceState(window.history.state, "", url);
      } catch {
        // Some offline viewers do not allow history updates.
      }
    }
    if (!initial) status.textContent = english ? "Reading language changed to English." : "已切換為繁體中文。";

    if (position) {
      const delta = position.element.getBoundingClientRect().top - position.top;
      if (Math.abs(delta) > 1) {
        const root = document.documentElement;
        const previous = root.style.scrollBehavior;
        root.style.scrollBehavior = "auto";
        window.scrollBy(0, delta);
        root.style.scrollBehavior = previous;
      }
    }
  }

  for (const button of buttons) {
    button.addEventListener("click", () => applyLanguage(button.dataset.language));
  }

  window.addEventListener("popstate", () => {
    const requested = normalizeLanguage(new URLSearchParams(window.location.search).get("lang"));
    applyLanguage(requested || savedLanguage() || "zh-Hant", { fromHistory: true });
  });

  const requested = normalizeLanguage(new URLSearchParams(window.location.search).get("lang"));
  applyLanguage(requested || savedLanguage() || "zh-Hant", { initial: true });
})();
