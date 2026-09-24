const button=document.querySelector('.menu');
const menu=document.querySelector('.site-header nav, .links');
if(button&&menu){
  button.addEventListener('click',(e)=>{
    e.stopPropagation();
    const open=menu.classList.toggle('open');
    button.setAttribute('aria-expanded',String(open));
    button.textContent=open?'×':'☰';
  });
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
    menu.classList.remove('open');
    button.setAttribute('aria-expanded','false');
    button.textContent='☰';
  }));
  document.addEventListener('click',(e)=>{
    if(menu.classList.contains('open') && !menu.contains(e.target) && e.target !== button){
      menu.classList.remove('open');
      button.setAttribute('aria-expanded','false');
      button.textContent='☰';
    }
  });
}
