document.addEventListener('DOMContentLoaded', () => {
  const countdown = document.querySelector('[data-countdown]');
  if (countdown) {
    const target = new Date(countdown.getAttribute('data-countdown'));
    const els = {
      days: countdown.querySelector('[data-days]'),
      hours: countdown.querySelector('[data-hours]'),
      minutes: countdown.querySelector('[data-minutes]'),
      seconds: countdown.querySelector('[data-seconds]'),
    };
    const update = () => {
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

  const body = document.body;
  const drawer = document.getElementById('site-drawer');
  const backdrop = document.querySelector('.drawer-backdrop');
  const openButton = document.querySelector('[data-menu-toggle]');
  const closeButtons = document.querySelectorAll('[data-menu-close]');

  const closeMenu = () => {
    if (!drawer) return;
    drawer.classList.remove('is-open');
    backdrop?.classList.remove('is-open');
    body.classList.remove('menu-open');
    if (openButton) openButton.setAttribute('aria-expanded', 'false');
    drawer.setAttribute('aria-hidden', 'true');
  };

  const openMenu = () => {
    if (!drawer) return;
    drawer.classList.add('is-open');
    backdrop?.classList.add('is-open');
    body.classList.add('menu-open');
    if (openButton) openButton.setAttribute('aria-expanded', 'true');
    drawer.setAttribute('aria-hidden', 'false');
  };

  openButton?.addEventListener('click', () => {
    if (drawer?.classList.contains('is-open')) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  closeButtons.forEach((button) => {
    button.addEventListener('click', closeMenu);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });
});
