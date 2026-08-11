// Kiosk tweaks for the AquaGen dashboard on the small 7" screen:
//  1) thin, always-visible scrollbars
//  2) make the left navigation menu scrollable when it's taller than the screen
(function () {
  // 1) Thin scrollbars everywhere ------------------------------------------
  var css = [
    "::-webkit-scrollbar{width:8px !important;height:8px !important;}",
    "::-webkit-scrollbar-thumb{background:rgba(100,116,139,.7) !important;border-radius:4px !important;}",
    "::-webkit-scrollbar-track{background:rgba(0,0,0,.06) !important;}",
    "*{scrollbar-width:thin !important;}"
  ].join("");
  var style = document.createElement("style");
  style.id = "kiosk-tweak-style";
  style.textContent = css;
  (document.head || document.documentElement).appendChild(style);

  // 2) Make the side menu scrollable ---------------------------------------
  // Find the nav item labelled "Monitoring", then walk up to the tall, left,
  // narrow column that is the sidebar, and let it scroll.
  function fixSidebar() {
    var nodes = document.querySelectorAll("a,div,li,span,button,p");
    var anchor = null;
    for (var i = 0; i < nodes.length; i++) {
      if ((nodes[i].textContent || "").trim() === "Monitoring") { anchor = nodes[i]; break; }
    }
    if (!anchor) return false;
    var el = anchor;
    for (var d = 0; d < 10 && el && el.parentElement; d++) {
      el = el.parentElement;
      var r = el.getBoundingClientRect();
      var tall = r.height > window.innerHeight * 0.55;
      var leftSide = r.left < 80;
      var narrow = r.width < window.innerWidth * 0.5;
      if (tall && leftSide && narrow) {
        el.style.setProperty("overflow-y", "auto", "important");
        el.style.setProperty("max-height", "100vh", "important");
        el.setAttribute("data-kiosk-scroll", "1");
        return true;
      }
    }
    return false;
  }

  var tries = 0;
  var iv = setInterval(function () {
    tries++;
    if (fixSidebar() || tries > 60) clearInterval(iv);
  }, 500);

  // Re-apply after SPA route changes.
  var mo = new MutationObserver(function () {
    if (!document.querySelector('[data-kiosk-scroll="1"]')) fixSidebar();
  });
  if (document.body) mo.observe(document.body, { childList: true, subtree: true });
  else document.addEventListener("DOMContentLoaded", function () {
    mo.observe(document.body, { childList: true, subtree: true });
  });
})();
