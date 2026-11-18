// The banner is fixed to the top of the screen, and photos are sized to fit
// the space below it (see --banner in vqvz.css). Its height depends on how
// its text wraps, so measure it and keep the CSS variable in step.
// Loaded right after the banner, so this runs before the photos are laid out.
(function () {
  "use strict";
  var banner = document.getElementById("gallery-banner");
  if (!banner) return;
  function update() {
    document.documentElement.style.setProperty("--banner", banner.offsetHeight + "px");
  }
  update();
  if (window.ResizeObserver) new ResizeObserver(update).observe(banner);
})();
