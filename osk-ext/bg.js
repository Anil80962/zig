// Background service worker: relays show/hide requests to the local keyboard
// helper. Runs in the extension origin, so it can reach http://127.0.0.1
// from the HTTPS page without mixed-content restrictions.
chrome.runtime.onMessage.addListener(function (msg) {
  if (!msg || (msg.k !== "show" && msg.k !== "hide")) return;
  fetch("http://127.0.0.1:8577/" + msg.k).catch(function () {});
});
