/* ==========================================================================
   app.js — motion layer for the signed-in pages.
   Progressive enhancement only: every page is fully usable with JS disabled,
   because the CSS entrance states resolve to "visible" without this file
   (see the .no-js fallback and the animation section in main.css).
   ========================================================================== */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.documentElement.classList.add('js-on');

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {

    /* --- stagger table rows and cards into view ---------------------------
       Index is written to a custom property so the CSS owns the timing. */
    var groups = document.querySelectorAll('.table-wrap table');
    groups.forEach(function (g) {
      var rows = g.querySelectorAll('tr');
      var n = 0;
      rows.forEach(function (r) {
        if (r.querySelector('th')) return;          // skip the header row
        r.style.setProperty('--row', n++);
        r.classList.add('row-in');
      });
    });

    /* --- reveal blocks as they enter the viewport ------------------------- */
    var targets = document.querySelectorAll('.reveal-up');
    if (reduced || !('IntersectionObserver' in window)) {
      targets.forEach(function (el) { el.classList.add('is-in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add('is-in');
            io.unobserve(e.target);
          }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
      targets.forEach(function (el) { io.observe(el); });
    }

    /* --- count the KPI tiles up from zero -------------------------------- */
    var tiles = document.querySelectorAll('table[name="Dashboard"] td');
    tiles.forEach(function (td) {
      var end = parseInt((td.textContent || '').trim(), 10);
      if (isNaN(end)) return;
      if (reduced) return;
      var dur = 900, t0 = null;
      td.textContent = '0';
      function frame(t) {
        if (t0 === null) t0 = t;
        var p = Math.min((t - t0) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        td.textContent = Math.round(end * eased);
        if (p < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });

    /* --- flash messages: dismissable, and they retire on their own ------- */
    document.querySelectorAll('.flash').forEach(function (f) {
      var x = document.createElement('button');
      x.type = 'button';
      x.className = 'flash-x';
      x.setAttribute('aria-label', 'Dismiss message');
      x.innerHTML = '&times;';
      x.addEventListener('click', function () { retire(f); });
      f.appendChild(x);
      setTimeout(function () { retire(f); }, 6000);
    });
    function retire(el) {
      el.classList.add('is-out');
      el.addEventListener('transitionend', function () { el.remove(); }, { once: true });
      setTimeout(function () { if (el.parentNode) el.remove(); }, 500);
    }

    /* --- confirm before anything destructive ------------------------------ */
    var DESTRUCTIVE = {
      '/delete_trek': 'Delete this trek? Its bookings will be removed too.',
      '/blacklist':   'Blacklist this person? They will not be able to sign in.',
      '/reject':      'Reject and delete this account? This cannot be undone.'
    };
    document.querySelectorAll('form[action]').forEach(function (form) {
      var msg = null;
      Object.keys(DESTRUCTIVE).forEach(function (prefix) {
        if (form.getAttribute('action').indexOf(prefix) === 0) msg = DESTRUCTIVE[prefix];
      });
      if (!msg) return;
      form.addEventListener('submit', function (e) {
        if (!window.confirm(msg)) e.preventDefault();
      });
    });

    /* --- keep the end date from preceding the start date ------------------ */
    var start = document.getElementById('str_date');
    var end = document.getElementById('end_date');
    if (start && end) {
      var sync = function () { if (start.value) end.min = start.value; };
      start.addEventListener('change', sync);
      sync();
    }

    /* --- pointer-tracked sheen on the KPI tiles and action cards ---------- */
    if (!reduced) {
      var sheened = 'table[name="Dashboard"] th, table[name="Dashboard"] td, .quick';
      document.querySelectorAll(sheened).forEach(function (cell) {
        cell.addEventListener('pointermove', function (e) {
          var r = cell.getBoundingClientRect();
          cell.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
        });
      });
    }
  });
})();
