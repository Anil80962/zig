// Content script: detects focus on editable fields and asks the background
// worker to show/hide the on-screen keyboard. A short delay on hide prevents
// flicker when moving between the username and password fields.
(function () {
  var hideTimer = null;

  function isEditable(el) {
    if (!el) return false;
    var tag = el.tagName;
    if (tag === "TEXTAREA") return true;
    if (el.isContentEditable) return true;
    if (tag === "INPUT") {
      var t = (el.type || "text").toLowerCase();
      var nonText = ["button", "submit", "reset", "checkbox", "radio",
                     "range", "color", "file", "image", "hidden"];
      return nonText.indexOf(t) === -1;
    }
    return false;
  }

  function send(kind) {
    try { chrome.runtime.sendMessage({ k: kind }); } catch (e) {}
  }

  document.addEventListener("focusin", function (e) {
    if (isEditable(e.target)) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      send("show");
    }
  }, true);

  document.addEventListener("focusout", function (e) {
    if (isEditable(e.target)) {
      if (hideTimer) clearTimeout(hideTimer);
      hideTimer = setTimeout(function () { send("hide"); }, 350);
    }
  }, true);
})();
