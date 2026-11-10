/* Sticky-nav scroll state + ad slots. Ad slots render nothing until ADSENSE_CLIENT and a
   slot id are set in site.json (which build.py writes into assets/config.js). */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var head = document.querySelector('.site-head');
    if (head) {
      var onScroll = function () { head.classList.toggle('is-stuck', window.scrollY > 8); };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }

    var cfg = window.SITE_CONFIG || {};
    if (!cfg.ADSENSE_CLIENT) return;
    var slots = document.querySelectorAll('.ad-slot[data-ad]');
    var used = 0;
    Array.prototype.forEach.call(slots, function (el) {
      var id = (cfg.AD_SLOTS || {})[el.getAttribute('data-ad')];
      if (!id) return;
      if (el.getAttribute('data-ad') === 'sidebar' && window.innerWidth < 1100) return;
      var ins = document.createElement('ins');
      ins.className = 'adsbygoogle';
      ins.style.display = 'block';
      ins.setAttribute('data-ad-client', cfg.ADSENSE_CLIENT);
      ins.setAttribute('data-ad-slot', id);
      ins.setAttribute('data-ad-format', 'auto');
      ins.setAttribute('data-full-width-responsive', 'true');
      el.appendChild(ins);
      el.classList.add('ad-live');
      used++;
    });
    if (!used) return;
    var s = document.createElement('script');
    s.async = true;
    s.crossOrigin = 'anonymous';
    s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(cfg.ADSENSE_CLIENT);
    document.head.appendChild(s);
    for (var k = 0; k < used; k++) { (window.adsbygoogle = window.adsbygoogle || []).push({}); }
  });
})();
