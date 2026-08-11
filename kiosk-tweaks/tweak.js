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

  // 3) Floating WiFi button (top-left) -> opens the local WiFi manager --------
  function addWifiButton() {
    if (document.getElementById("kiosk-wifi-btn")) return;
    var b = document.createElement("button");
    b.id = "kiosk-wifi-btn";
    b.title = "Change WiFi";
    b.innerHTML =
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">' +
      '<path d="M12 21l3-3a4.24 4.24 0 0 0-6 0l3 3zm-6-6l1.8 1.8a8.49 8.49 0 0 1 8.4 0L18 15a11 11 0 0 0-12 0zm-3-3l1.8 1.8a13 13 0 0 1 16.4 0L23 12a15.5 15.5 0 0 0-20 0z"/></svg>';
    b.style.cssText = [
      "position:fixed", "top:6px", "left:6px", "z-index:2147483647",
      "width:40px", "height:40px", "border-radius:50%", "border:none",
      "background:rgba(37,99,235,.92)", "box-shadow:0 2px 6px rgba(0,0,0,.4)",
      "display:flex", "align-items:center", "justify-content:center",
      "cursor:pointer", "padding:0"
    ].join(";");
    b.addEventListener("click", function () {
      location.href = "http://127.0.0.1:8088/";
    });
    document.body.appendChild(b);
  }

  var tries = 0;
  var iv = setInterval(function () {
    tries++;
    addWifiButton();
    if (fixSidebar() || tries > 60) clearInterval(iv);
  }, 500);

  // Re-apply after SPA route changes.
  var mo = new MutationObserver(function () {
    addWifiButton();
    if (!document.querySelector('[data-kiosk-scroll="1"]')) fixSidebar();
  });
  if (document.body) mo.observe(document.body, { childList: true, subtree: true });
  else document.addEventListener("DOMContentLoaded", function () {
    mo.observe(document.body, { childList: true, subtree: true });
  });
})();
