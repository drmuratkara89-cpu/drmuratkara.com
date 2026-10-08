/* Premium V2 homepage navigation accessibility enhancements. */
document.addEventListener('DOMContentLoaded', () => {
  if (!document.body.classList.contains('premium-home')) return;
  const menuButton = document.querySelector('.site-header .menu');
  const nav = document.querySelector('.site-header nav');
  const triggers = [...document.querySelectorAll('.nav-dropdown-trigger')];

  function syncState() {
    if (menuButton && nav) {
      const expanded = nav.classList.contains('open');
      menuButton.setAttribute('aria-expanded', String(expanded));
      menuButton.setAttribute('aria-label', expanded ? 'Menüyü kapat' : 'Menüyü aç');
    }
    triggers.forEach(trigger => {
      trigger.setAttribute(
        'aria-expanded',
        String(Boolean(trigger.closest('.nav-item')?.classList.contains('open')))
      );
    });
  }
  if (menuButton) menuButton.addEventListener('click', syncState);
  triggers.forEach(trigger => trigger.addEventListener('click', syncState));
  document.addEventListener('click', syncState);
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const wasOpen = Boolean(nav?.classList.contains('open')) ||
      triggers.some(t => t.closest('.nav-item')?.classList.contains('open'));
    nav?.classList.remove('open');
    document.querySelectorAll('.nav-item.open').forEach(el => el.classList.remove('open'));
    syncState();
    if (wasOpen) menuButton?.focus();
  });
  syncState();
});
