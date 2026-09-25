document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('.menu');
  const navMenu = document.querySelector('.site-header nav, .links');

  if (menuButton && navMenu) {
    menuButton.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = navMenu.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(isOpen));
      menuButton.textContent = isOpen ? '×' : '☰';
    });

    // Sayfa linklerine tıklandığında menüyü kapat
    navMenu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        navMenu.classList.remove('open');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.textContent = '☰';
        document.querySelectorAll('.nav-item.open').forEach(el => el.classList.remove('open'));
      });
    });

    // Dışarı tıklandığında menüyü kapat
    document.addEventListener('click', (e) => {
      if (navMenu.classList.contains('open') && !navMenu.contains(e.target) && e.target !== menuButton) {
        navMenu.classList.remove('open');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.textContent = '☰';
        document.querySelectorAll('.nav-item.open').forEach(el => el.classList.remove('open'));
      }
    });
  }

  // Mega Menü / Dropdown tetikleyicisi (Özellikle Mobil ve Dokunmatik Ekranlar için)
  const dropdownTriggers = document.querySelectorAll('.nav-dropdown-trigger');
  dropdownTriggers.forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const parent = trigger.closest('.nav-item');
      if (parent) {
        const wasOpen = parent.classList.contains('open');
        document.querySelectorAll('.nav-item.open').forEach(el => el.classList.remove('open'));
        if (!wasOpen) {
          parent.classList.add('open');
        }
      }
    });
  });

  // Dropdown dışına tıklandığında kapat
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-item')) {
      document.querySelectorAll('.nav-item.open').forEach(el => el.classList.remove('open'));
    }
  });
});
