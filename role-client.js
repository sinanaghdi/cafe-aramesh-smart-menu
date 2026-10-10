(function(){
 const config=window.CAFE_ARAMESH_CONFIG||{};
 const base=String(config.apiBaseUrl||"").replace(/\/$/,"");
 const digits=new Intl.NumberFormat("fa-IR",{maximumFractionDigits:0});
 const money=n=>digits.format(Number(n||0))+" تومان";
 const number=n=>digits.format(Number(n||0));
 const escape=v=>String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const date=v=>{try{return new Intl.DateTimeFormat("fa-IR-u-ca-persian",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Tehran"}).format(new Date(v));}catch(_){return String(v||"");}};
 async function api(path,options){
   options=options||{};
   const headers=Object.assign({"Content-Type":"application/json"},options.headers||{});
   const token=localStorage.getItem("aramesh-token");
   if(token)headers.Authorization="Bearer "+token;
   const response=await fetch(base+path,Object.assign({},options,{headers:headers}));
   let body={};try{body=await response.json();}catch(_){}
   if(!response.ok){const err=new Error(body.detail||body.message||("خطای سرور: "+response.status));err.status=response.status;throw err;}
   return body;
 }
 function notify(message,kind){
   let el=document.getElementById("role-toast");
   if(!el){el=document.createElement("div");el.id="role-toast";el.className="role-toast";el.setAttribute("role","status");document.body.appendChild(el);}
   el.textContent=message;el.style.background=kind==="error"?"#873b34":kind==="success"?"#426347":"#34281f";
   clearTimeout(notify.timer);notify.timer=setTimeout(()=>{el.remove();},4000);
 }
 function saveSession(data){localStorage.setItem("aramesh-token",data.access_token);localStorage.setItem("aramesh-user",JSON.stringify(data.user));}
 function clearSession(){localStorage.removeItem("aramesh-token");localStorage.removeItem("aramesh-user");}
 function who(){try{return JSON.parse(localStorage.getItem("aramesh-user")||"null");}catch(_){return null;}}
 window.ArameshClient={base,api,money,number,escape,date,notify,saveSession,clearSession,who};
})();