export function compare(a,b){const s=x=>x.reduce((t,i)=>t+(i.value||0),0);return{left:s(a),right:s(b),difference:s(a)-s(b)}}
