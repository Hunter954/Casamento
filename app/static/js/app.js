document.addEventListener('DOMContentLoaded', () => {
  const countdown = document.querySelector('[data-countdown]');
  if (countdown) {
    const targetValue = countdown.getAttribute('data-countdown');
    const target = targetValue ? new Date(targetValue) : null;
    const els = {
      days: countdown.querySelector('[data-days]'),
      hours: countdown.querySelector('[data-hours]'),
      minutes: countdown.querySelector('[data-minutes]'),
      seconds: countdown.querySelector('[data-seconds]'),
    };
    const update = () => {
      if (!target || Number.isNaN(target.getTime())) return;
      const now = new Date();
      const diff = Math.max(0, target - now);
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);
      if (els.days) els.days.textContent = String(days).padStart(2, '0');
      if (els.hours) els.hours.textContent = String(hours).padStart(2, '0');
      if (els.minutes) els.minutes.textContent = String(minutes).padStart(2, '0');
      if (els.seconds) els.seconds.textContent = String(seconds).padStart(2, '0');
    };
    update();
    setInterval(update, 1000);
  }

  const generateBtn = document.getElementById('generate-message-btn');
  const messageArea = document.getElementById('gift-message');
  if (generateBtn && messageArea) {
    generateBtn.addEventListener('click', async () => {
      const res = await fetch('/gerar-mensagem');
      const data = await res.json();
      messageArea.value = data.message;
    });
  }

  const drawer = document.getElementById('mobile-drawer');
  const backdrop = document.querySelector('[data-drawer-backdrop]');
  const toggle = document.querySelector('[data-menu-toggle]');
  const closeBtn = document.querySelector('[data-menu-close]');

  const closeDrawer = () => {
    if (!drawer || !toggle || !backdrop) return;
    drawer.classList.remove('is-open');
    backdrop.classList.remove('is-visible');
    toggle.setAttribute('aria-expanded', 'false');
    drawer.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('drawer-open');
  };

  const openDrawer = () => {
    if (!drawer || !toggle || !backdrop) return;
    drawer.classList.add('is-open');
    backdrop.classList.add('is-visible');
    toggle.setAttribute('aria-expanded', 'true');
    drawer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
  };

  if (toggle && drawer && backdrop) {
    toggle.addEventListener('click', () => {
      if (drawer.classList.contains('is-open')) closeDrawer();
      else openDrawer();
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);
  if (drawer) {
    drawer.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeDrawer));
  }
});
