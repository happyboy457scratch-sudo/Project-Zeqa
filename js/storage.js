export const loadCollection=()=>JSON.parse(localStorage.getItem('collection')||'[]');export const saveCollection=i=>localStorage.setItem('collection',JSON.stringify(i));
