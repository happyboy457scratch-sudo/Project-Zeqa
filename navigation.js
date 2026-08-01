export function navigate(page){
document.querySelectorAll('[data-page]').forEach(p=>p.style.display='none');
const el=document.querySelector(`[data-page="${page}"]`);
if(el) el.style.display='block';
localStorage.setItem('lastPage',page);
}
