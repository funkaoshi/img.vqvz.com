// j / k to move between photos, crossing page boundaries.
// A dependency-free take on hiddenloop's paging_keys.js.
(function () {
  "use strict";

  function photos() { return Array.from(document.querySelectorAll(".photo")); }
  function top(el) { return el.getBoundingClientRect().top + window.scrollY; }
  function go(el) { window.scrollTo({ top: top(el), behavior: "instant" }); }

  function follow(selector, hash) {
    var link = document.querySelector("a." + selector);
    if (link) window.location.href = link.href + (hash || "");
  }

  function next() {
    var y = window.scrollY + 2;
    var target = photos().find(function (p) { return top(p) > y; });
    target ? go(target) : follow("next_page");
  }

  function prev() {
    var y = window.scrollY - 2;
    var target = photos().reverse().find(function (p) { return top(p) < y; });
    target ? go(target) : follow("prev_page", "#last");
  }

  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if (e.key === "j") { e.preventDefault(); next(); }
    else if (e.key === "k") { e.preventDefault(); prev(); }
  });

  // Arriving from "previous page" via k: start at the last photo.
  window.addEventListener("load", function () {
    if (window.location.hash === "#last") {
      var all = photos();
      if (all.length) go(all[all.length - 1]);
    }
  });
})();
