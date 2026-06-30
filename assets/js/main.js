/* =========================================================
   FarmacoMatch Site — interações simples
   - Menu mobile (toggle)
   - Fecha menu ao clicar em link
   - Reveal on scroll (IntersectionObserver)
   ========================================================= */

(function () {
  'use strict';

  // ---- Menu mobile ----
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');

  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var isOpen = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // fecha ao clicar em qualquer link
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // ---- Reveal on scroll ----
  var revealTargets = [
    '.section', '.step-card', '.info-card', '.app-cta', '.hero-cta'
  ];

  var elements = [];
  revealTargets.forEach(function (sel) {
    document.querySelectorAll(sel).forEach(function (el) {
      el.classList.add('reveal');
      elements.push(el);
    });
  });

  if ('IntersectionObserver' in window && elements.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    elements.forEach(function (el) { io.observe(el); });
  } else {
    // fallback: mostra tudo
    elements.forEach(function (el) { el.classList.add('is-visible'); });
  }
})();