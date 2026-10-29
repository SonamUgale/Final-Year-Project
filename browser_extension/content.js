/**
 * DarkShield AI - Content Script (DOM & Visual Metadata Extractor)
 *
 * Extracts rendered DOM structures, interactive elements, bounding boxes,
 * and computed styling while strictly preserving user privacy (no cookies,
 * no passwords, no tokens, no credentials, no storage).
 */

(() => {
  const SENSITIVE_INPUT_REGEX = /password|passwd|card|cvv|ccnum|credit|debit|ssn|social.*security|auth|token|secret|api[_-]?key/i;

  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    try {
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const style = window.getComputedStyle(el);
      if (!style) return false;
      return style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity || '1') > 0.05;
    } catch {
      return false;
    }
  }

  function getComputedStylesSubset(el) {
    if (!el) return {};
    try {
      const style = window.getComputedStyle(el);
      if (!style) return {};
      return {
        color: style.color || "",
        backgroundColor: style.backgroundColor || "",
        fontSize: style.fontSize || "",
        fontWeight: style.fontWeight || "",
        textDecoration: style.textDecorationLine || "",
        opacity: style.opacity || "1",
        display: style.display || "",
        position: style.position || ""
      };
    } catch {
      return {};
    }
  }

  function getBoundingBox(el) {
    if (!el || !el.getBoundingClientRect) return null;
    try {
      const rect = el.getBoundingClientRect();
      return {
        top: Math.round(rect.top),
        left: Math.round(rect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        bottom: Math.round(rect.bottom),
        right: Math.round(rect.right)
      };
    } catch {
      return null;
    }
  }

  function extractInteractiveElements() {
    const elements = [];
    const seenTexts = new Set();

    // 1. Buttons & Action Links
    try {
      const buttons = document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"], a.btn, a.button');
      buttons.forEach((btn, index) => {
        if (index >= 120) return;
        try {
          const text = (btn.innerText || btn.value || btn.getAttribute('aria-label') || "").trim();
          elements.push({
            element_type: "button",
            tag: btn.tagName ? btn.tagName.toLowerCase() : "button",
            text: String(text).slice(0, 150),
            id: typeof btn.id === "string" ? btn.id : null,
            classes: btn.className ? String(btn.className).slice(0, 100) : null,
            bbox: getBoundingBox(btn),
            style: getComputedStylesSubset(btn),
            is_visible: isVisible(btn),
            role: btn.getAttribute('role') || null
          });
          if (text) seenTexts.add(String(text).toLowerCase());
        } catch (e) {}
      });
    } catch (e) {}

    // 2. Navigation & Content Links
    try {
      const links = document.querySelectorAll('a[href]');
      let linkCount = 0;
      links.forEach((link) => {
        if (linkCount >= 150) return;
        try {
          const href = String(link.getAttribute('href') || "");
          const text = String(link.innerText || link.getAttribute('aria-label') || "").trim();
          if (!href || href.startsWith("javascript:")) return;

          const isExternal = href.startsWith("http://") || href.startsWith("https://")
            ? !href.includes(window.location.hostname)
            : false;

          elements.push({
            element_type: "link",
            tag: "a",
            text: text.slice(0, 150),
            href: href.slice(0, 300),
            is_external: isExternal,
            bbox: getBoundingBox(link),
            style: getComputedStylesSubset(link),
            is_visible: isVisible(link)
          });
          linkCount++;
        } catch (e) {}
      });
    } catch (e) {}

    // 3. Inputs, Checkboxes, Selects (Strict Privacy Filter)
    try {
      const formControls = document.querySelectorAll('input, select, textarea');
      formControls.forEach((fc, index) => {
        if (index >= 80) return;
        try {
          const type = String(fc.type || fc.tagName.toLowerCase()).toLowerCase();
          const name = typeof fc.name === "string" ? fc.name : "";
          const id = typeof fc.id === "string" ? fc.id : "";
          const placeholder = typeof fc.placeholder === "string" ? fc.placeholder : "";
          const ariaLabel = String(fc.getAttribute('aria-label') || "");
          const autocomplete = String(fc.autocomplete || "");

          // PRIVACY SAFEGUARD: Completely skip sensitive credential/financial fields
          if (
            type === 'password' ||
            SENSITIVE_INPUT_REGEX.test(name) ||
            SENSITIVE_INPUT_REGEX.test(id) ||
            SENSITIVE_INPUT_REGEX.test(placeholder) ||
            SENSITIVE_INPUT_REGEX.test(ariaLabel) ||
            autocomplete === 'current-password' ||
            autocomplete === 'new-password' ||
            autocomplete === 'cc-number'
          ) {
            return; // Excluded from capture
          }

          elements.push({
            element_type: type === 'checkbox' ? 'checkbox' : type === 'radio' ? 'radio' : 'input',
            tag: fc.tagName ? fc.tagName.toLowerCase() : "input",
            type: type,
            name: name.slice(0, 60),
            id: id.slice(0, 60),
            placeholder: placeholder.slice(0, 120),
            checked: Boolean(fc.checked),
            required: Boolean(fc.required),
            bbox: getBoundingBox(fc),
            is_visible: isVisible(fc)
          });
        } catch (e) {}
      });
    } catch (e) {}

    // 4. Urgency, Scarcity, Countdown & Banner Elements
    try {
      const urgencyCandidates = document.querySelectorAll(
        '[class*="timer"], [class*="countdown"], [class*="urgency"], [class*="stock"], [class*="alert"], [class*="popup"], [class*="modal"], [class*="banner"], [id*="timer"], [id*="countdown"], [data-timer], [role="alert"], [role="dialog"]'
      );
      urgencyCandidates.forEach((el, index) => {
        if (index >= 60) return;
        try {
          const text = String(el.innerText || "").trim();
          if (!text || text.length < 3 || seenTexts.has(text.toLowerCase())) return;

          elements.push({
            element_type: "urgency_banner",
            tag: el.tagName ? el.tagName.toLowerCase() : "div",
            text: text.slice(0, 250),
            bbox: getBoundingBox(el),
            style: getComputedStylesSubset(el),
            is_visible: isVisible(el),
            role: el.getAttribute('role') || null
          });
          seenTexts.add(text.toLowerCase());
        } catch (e) {}
      });
    } catch (e) {}

    // 5. Headings & High-Impact Text Blocks
    try {
      const headings = document.querySelectorAll('h1, h2, h3, [role="heading"]');
      headings.forEach((h, index) => {
        if (index >= 40) return;
        try {
          const text = String(h.innerText || "").trim();
          if (!text || seenTexts.has(text.toLowerCase())) return;

          elements.push({
            element_type: "heading",
            tag: h.tagName ? h.tagName.toLowerCase() : "h2",
            text: text.slice(0, 200),
            bbox: getBoundingBox(h),
            style: getComputedStylesSubset(h),
            is_visible: isVisible(h)
          });
          seenTexts.add(text.toLowerCase());
        } catch (e) {}
      });
    } catch (e) {}

    return elements;
  }

  function extractPageData() {
    try {
      const url = window.location.href;
      const title = document.title || "Captured Webpage";
      const rawText = document.body ? (document.body.innerText || "") : "";
      const visibleText = rawText.length > 100000 ? rawText.slice(0, 100000) : rawText;
      const rawHtml = document.documentElement ? (document.documentElement.outerHTML || "") : "";
      const html = rawHtml.length > 400000 ? rawHtml.slice(0, 400000) : rawHtml;
      const elements = extractInteractiveElements();

      // Extract discovered links for crawler (bounded and cleaned at source)
      const rawLinks = Array.from(document.querySelectorAll('a[href]'));
      const discoveredLinks = [];
      const seenLinks = new Set();
      const currentHost = window.location.hostname.toLowerCase();
      const STATIC_EXTS = /\.(jpg|jpeg|png|gif|svg|webp|ico|mp4|mp3|pdf|doc|docx|zip|rar|exe|css|js|woff|woff2|ttf)$/i;

      for (const a of rawLinks) {
        if (discoveredLinks.length >= 150) break;
        try {
          const href = a.href;
          if (!href || typeof href !== "string") continue;
          if (!href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("file://")) continue;

          // Parse and normalize
          const u = new URL(href);
          u.hash = "";

          // Exclude static extensions
          if (STATIC_EXTS.test(u.pathname)) continue;

          // Strip tracking & volatile parameters
          const keysToDelete = [];
          u.searchParams.forEach((_, key) => {
            const k = key.toLowerCase();
            if (
              k.startsWith("utm_") ||
              k === "gclid" || k === "fbclid" || k === "msclkid" ||
              k === "ref" || k === "ref_" || k === "tag" ||
              k === "page" || k === "p" || k === "sort" || k === "order"
            ) {
              keysToDelete.push(key);
            }
          });
          keysToDelete.forEach(k => u.searchParams.delete(k));

          const cleanUrl = u.toString();
          if (!seenLinks.has(cleanUrl)) {
            seenLinks.add(cleanUrl);
            discoveredLinks.push(cleanUrl);
          }
        } catch (e) {}
      }

      return {
        url: url,
        title: title,
        html: html,
        visible_text: visibleText,
        elements: elements,
        discovered_links: discoveredLinks,
        browser_metadata: {
          source: "darkshield_chrome_extension",
          version: "1.0.0",
          viewport: {
            width: window.innerWidth || 1440,
            height: window.innerHeight || 900
          },
          device_pixel_ratio: window.devicePixelRatio || 1,
          user_agent: navigator.userAgent
        }
      };
    } catch (err) {
      console.warn("[DarkShield Content Script] Extraction error, returning safe baseline:", err);
      return {
        url: window.location.href,
        title: document.title || "Captured Webpage",
        html: document.documentElement ? document.documentElement.outerHTML.slice(0, 200000) : "",
        visible_text: document.body ? document.body.innerText.slice(0, 50000) : "",
        elements: [],
        discovered_links: [],
        browser_metadata: { source: "darkshield_content_script_safeguard" }
      };
    }
  }

  // Handle messages or direct script evaluation
  window.__darkshield_extract_page = extractPageData;
  return extractPageData();
})();
