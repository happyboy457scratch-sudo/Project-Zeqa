export function search(items,q){
q=q.toLowerCase();
return items.filter(i=>i.name.toLowerCase().includes(q));
}
