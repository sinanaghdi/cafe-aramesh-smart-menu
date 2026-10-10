(function(){
const C=window.ArameshClient, $=id=>document.getElementById(id);
let view="pending",refreshTimer=null;
const labels={pending_verification:"در انتظار تأیید",confirmed:"تأیید شده",preparing:"در حال آماده‌سازی",ready:"آماده تحویل",served:"تحویل شده",cancelled:"لغو شده",expired:"منقضی شده"};
const viewTitles={pending:"درخواست‌های در انتظار تأیید",active:"درخواست‌های در جریان",history:"سابقه درخواست‌ها"};
function errorOn(id,message){const box=$(id);box.textContent=message;box.hidden=false;}
function showApp(user){$("login-view").hidden=true;$("staff-view").hidden=false;$("logout").hidden=false;$("staff-greeting").textContent="خوش آمدی، "+user.full_name+"؛ درخواست‌های کافه را از این بخش پیگیری کن.";render();}
function showLogin(){clearInterval(refreshTimer);refreshTimer=null;$("login-view").hidden=false;$("staff-view").hidden=true;$("logout").hidden=true;}
async function render(){
$("queue-title").textContent=viewTitles[view];$("queue-error").hidden=true;$("order-list").innerHTML='<div class="role-empty">در حال بارگذاری درخواست‌ها…</div>';
try{
const rows=await C.api("/api/staff/orders?view="+view);
if(!rows.length){$("order-list").innerHTML='<div class="role-empty"><strong>'+C.escape(view==="pending"?"درخواست منتظر تأیید وجود ندارد.":view==="active"?"در حال حاضر درخواستی در جریان نیست.":"سابقه‌ای برای نمایش وجود ندارد.")+'</strong><br>با ثبت یا تغییر وضعیت درخواست‌ها، این فهرست به‌روز می‌شود.</div>';return;}
$("order-list").innerHTML=rows.map(o=>{
let actions="";
if(view==="pending")actions='<div class="role-order-actions"><label for="code-'+C.escape(o.id)+'" class="role-muted">کد مشتری</label><input id="code-'+C.escape(o.id)+'" inputmode="numeric" autocomplete="one-time-code" maxlength="4" placeholder="----" aria-label="کد تأیید مشتری"><button class="role-button" data-verify="'+C.escape(o.id)+'">بررسی و تأیید</button></div>';
else if(view==="active"){
if(o.status==="confirmed")actions='<button class="role-button" data-status="preparing" data-order="'+C.escape(o.id)+'">شروع آماده‌سازی</button>';
if(o.status==="preparing")actions='<button class="role-button" data-status="ready" data-order="'+C.escape(o.id)+'">آماده تحویل</button>';
if(o.status==="ready")actions='<button class="role-button" data-status="served" data-order="'+C.escape(o.id)+'">تحویل به مشتری</button>';
if(!actions)actions='<span class="role-muted">وضعیت فعلی نیاز به اقدام دیگری ندارد.</span>';
}else actions='<span class="role-muted">این درخواست در وضعیت «'+C.escape(labels[o.status]||o.status)+'» پایان یافته است.</span>';
return '<article class="role-order"><div class="role-order-head"><div><h3>درخواست <span dir="ltr">'+C.escape(o.id)+'</span> · '+C.escape(o.table_label)+'</h3><p>'+C.escape(C.date(o.created_at))+' · '+(view==="pending"?'انتظار '+C.number(o.waiting_minutes)+' دقیقه':'')+'</p></div><span class="role-status '+(o.status==="served"?"ok":o.status==="ready"?"info":"")+'">'+C.escape(labels[o.status]||o.status)+'</span></div><div class="role-order-items">'+o.items.map(i=>C.escape(i.name)+' × '+C.number(i.quantity)+' — '+C.money(i.line_total_toman)).join("<br>")+'<hr style="border:0;border-top:1px solid #e4dbce"><strong>جمع درخواست: '+C.money(o.total_toman)+'</strong></div><div class="role-order-actions">'+actions+'</div><div class="role-error" id="order-error-'+C.escape(o.id)+'" hidden></div></article>';
}).join("");
}catch(e){
$("order-list").innerHTML="";
errorOn("queue-error",e.message+" اگر سایت روی GitHub Pages اجرا می‌شود، ابتدا API را مستقر و نشانی آن را در config.js تنظیم کنید.");
}
}
$("login-form").addEventListener("submit",async e=>{
e.preventDefault();$("login-error").hidden=true;
try{
const data=await C.api("/api/auth/login",{method:"POST",body:JSON.stringify({email:$("email").value.trim(),password:$("password").value})});
if(data.user.role!=="waiter")throw new Error("این حساب مجوز پنل کارکنان را ندارد.");
C.saveSession(data);showApp(data.user);
clearInterval(refreshTimer);refreshTimer=setInterval(()=>{if(!$("staff-view").hidden)render();},15000);
}catch(err){errorOn("login-error",err.message);}
});
$("logout").addEventListener("click",()=>{C.clearSession();showLogin();$("login-form").reset();});
$("refresh-orders").addEventListener("click",render);
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{view=b.dataset.view;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b));render();}));
$("order-list").addEventListener("click",async e=>{
const verify=e.target.closest("[data-verify]");
if(verify){
const id=verify.dataset.verify,code=document.getElementById("code-"+id).value.trim(),box=document.getElementById("order-error-"+id);verify.disabled=true;
try{const result=await C.api("/api/staff/orders/"+id+"/verify",{method:"POST",body:JSON.stringify({code})});C.notify(result.message,"success");await render();}
catch(err){box.textContent=err.message;box.hidden=false;verify.disabled=false;}return;
}
const status=e.target.closest("[data-status]");
if(status){status.disabled=true;
try{const result=await C.api("/api/staff/orders/"+status.dataset.order+"/status",{method:"PATCH",body:JSON.stringify({status:status.dataset.status})});C.notify(result.message,"success");await render();}
catch(err){C.notify(err.message,"error");status.disabled=false;}
}
});
async function restore(){
const user=C.who(),token=localStorage.getItem("aramesh-token");if(!user||!token)return;
try{const current=await C.api("/api/auth/me");if(current.role==="waiter"){showApp(current);refreshTimer=setInterval(()=>{if(!$("staff-view").hidden)render();},15000);}}
catch(_){C.clearSession();}
}
restore();
window.addEventListener("pagehide",()=>clearInterval(refreshTimer));
})();