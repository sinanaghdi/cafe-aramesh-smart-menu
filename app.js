const sampleProducts = [
{id:"espresso",name:"اسپرسو",category:"قهوه گرم",price:95000,description:"کوتاه، عمیق و پرعطر؛ برای شروعی جدی.",tags:["گرم","قوی","تلخ"],flavors:["تلخ","قوی"],temperature:"گرم",caffeine:"زیاد",popular:true,available:true,bg:"#e8ded0",drink:"#583525",top:"#9a6b49"},
{id:"americano",name:"آمریکانو",category:"قهوه گرم",price:115000,description:"طعم شفاف قهوه با بافتی سبک‌تر.",tags:["گرم","متعادل"],flavors:["تلخ","متعادل"],temperature:"گرم",caffeine:"زیاد",popular:true,available:true,bg:"#e3e2d7",drink:"#76503a",top:"#b0835e"},
{id:"latte",name:"لاته",category:"قهوه گرم",price:155000,description:"ترکیب اسپرسو و شیر با بافتی نرم.",tags:["گرم","شیری","ملایم"],flavors:["ملایم","خامه‌ای"],temperature:"گرم",caffeine:"متوسط",popular:true,available:true,bg:"#eadcc9",drink:"#b78b65",top:"#f0e3cd",milk:true},
{id:"coldbrew",name:"کلد برو",category:"قهوه سرد",price:165000,description:"قهوه سرددم با طعمی عمیق و خنک.",tags:["سرد","قوی","بدون شیر"],flavors:["تلخ","قوی"],temperature:"سرد",caffeine:"زیاد",popular:true,available:true,bg:"#dce5dc",drink:"#5b392b",top:"#9a6e4e"},
{id:"lemon",name:"لیموناد خانگی",category:"نوشیدنی خنک",price:125000,description:"ترش و تازه؛ انتخابی سبک برای روزهای گرم.",tags:["سرد","ترش","تازه"],flavors:["ترش","مرکباتی","تازه"],temperature:"سرد",caffeine:"بدون کافئین",popular:false,available:true,bg:"#e9e8cb",drink:"#c9c66e",top:"#f1e8a1",caffeineFree:true},
{id:"berry",name:"آیس بری",category:"نوشیدنی خنک",price:145000,description:"ترکیبی میوه‌ای با حال‌وهوای توت‌های ترش.",tags:["سرد","میوه‌ای","ترش"],flavors:["ترش","میوه‌ای"],temperature:"سرد",caffeine:"بدون کافئین",popular:false,available:true,bg:"#e8dce0",drink:"#a84e66",top:"#d88b9c",caffeineFree:true},
{id:"matcha",name:"آیس ماچا",category:"نوشیدنی خنک",price:175000,description:"نوشیدنی خنک با طعمی گیاهی و خاص.",tags:["سرد","ملایم"],flavors:["گیاهی","ملایم"],temperature:"سرد",caffeine:"متوسط",popular:false,available:true,bg:"#dfe7d4",drink:"#8b9b63",top:"#bdcda1",milk:true},
{id:"cookie",name:"کوکی شکلاتی",category:"میان‌وعده",price:85000,description:"یک همراه کوچک برای قهوه و وقت استراحت.",tags:["شیرین","میان‌وعده"],flavors:["شیرین","شکلاتی"],temperature:"معمولی",caffeine:"کم",popular:true,available:true,bg:"#eadfd2",drink:"#9a6747",top:"#c69a73",milk:false}
];
let products=sampleProducts.slice(),categories=["همه","قهوه گرم","قهوه سرد","نوشیدنی خنک","میان‌وعده"],combos=[];
const cart=new Map();
let activeCategory="همه",query="",toastTimer,backendMode=false,workConfig=null,clubMode="login";
const cfg=window.CAFE_ARAMESH_CONFIG||{};
const API_BASE=String(cfg.apiBaseUrl||"").replace(/\/$/,"");
const fa=new Intl.NumberFormat("fa-IR");
const money=n=>fa.format(Number(n||0))+" تومان";
const num=n=>fa.format(Number(n||0));
const $=id=>document.getElementById(id);
const esc=v=>String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const normalize=s=>String(s||"").toLocaleLowerCase("fa").replace(/[يى]/g,"ی").replace(/ك/g,"ک").replace(/[ۀة]/g,"ه").replace(/[\u064B-\u065F\u0670]/g,"").replace(/[\u200c\u200e\u200fـ\s]+/g," ").trim();
const faDate=v=>{try{return new Intl.DateTimeFormat("fa-IR-u-ca-persian",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Tehran"}).format(new Date(v));}catch(_){return String(v||"");}};
async function api(path,options){
 options=options||{};
 const headers=Object.assign({"Content-Type":"application/json"},options.headers||{});
 const token=localStorage.getItem("aramesh-token");
 if(token)headers.Authorization="Bearer "+token;
 const response=await fetch(API_BASE+path,Object.assign({},options,{headers:headers}));
 let body={};try{body=await response.json();}catch(_){}
 if(!response.ok){const error=new Error(body.detail||body.message||("خطای سرور: "+response.status));error.status=response.status;throw error;}
 return body;
}
function canTryApi(){
 if(API_BASE)return true;
 if(!/^https?:$/.test(location.protocol))return false;
 return !location.hostname.endsWith("github.io");
}
function toast(message,error){
 const el=$("toast");el.textContent=message;el.classList.toggle("toast-error",!!error);el.classList.add("show");
 clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("show"),3600);
}
function announce(message){
 const el=$("menu-note");if(el)el.textContent=message;
}
function productColors(p){
 const colors={"espresso":["#e8ded0","#583525","#9a6b49"],"americano":["#e3e2d7","#76503a","#b0835e"],"latte":["#eadcc9","#b78b65","#f0e3cd"],"cappuccino":["#eadcc9","#b78b65","#f0e3cd"],"iced-coffee":["#dce5dc","#5b392b","#9a6e4e"],"lemonade":["#e9e8cb","#c9c66e","#f1e8a1"],"iced-latte":["#e3e2d7","#76503a","#d1bd9e"],"peach-tea":["#e8dce0","#a84e66","#d88b9c"],"tea":["#e5e7db","#8c9a74","#bfc9a5"],"herbal-tea":["#e5e7db","#8c9a74","#bfc9a5"],"cake":["#eadfd2","#9a6747","#c69a73"],"cookie":["#eadfd2","#9a6747","#c69a73"]};
 const v=colors[p.image_key]||[p.bg||"#e8e2d7",p.drink||"#755640",p.top||"#bba080"];
 return {bg:p.bg||v[0],drink:p.drink||v[1],top:p.top||v[2]};
}
function mapApiProduct(p){
 const colors=productColors(p);
 return Object.assign({},p,{id:String(p.id),price:Number(p.price_toman||p.price||0),bg:colors.bg,drink:colors.drink,top:colors.top,
   tags:p.tags||[],flavors:p.flavors||[],popular:false,available:p.available!==false,milk:p.attributes&&p.attributes.dairy_free===true?false:!!p.milk});
}
function renderCategories(){
 $("categories").innerHTML=categories.map(c=>'<button type="button" class="category-chip '+(activeCategory===c?"active":"")+'" data-category="'+esc(c)+'">'+esc(c)+"</button>").join("");
}
function visual(p){
 const colors=productColors(p);
 return '<div class="product-visual" style="--product-bg:'+esc(colors.bg)+";--drink:"+esc(colors.drink)+";--drink-top:"+esc(colors.top)+'">'+(p.popular?'<span class="product-badge">محبوب</span>':"")+'<div class="drink" aria-hidden="true"></div></div>';
}
function renderProducts(itemsOverride){
 let list=(itemsOverride||products).filter(p=>p.available!==false&&p.visible!==false);
 if(!itemsOverride&&activeCategory!=="همه")list=list.filter(p=>p.category===activeCategory);
 if(!itemsOverride&&query)list=list.filter(p=>normalize([p.name,p.category,p.description].concat(p.tags||[],p.flavors||[]).join(" ")).includes(normalize(query)));
 $("menu-note").textContent=list.length?num(list.length)+" انتخاب برای تو":"چیزی با این مشخصات پیدا نکردیم؛ عبارت دیگری را امتحان کن.";
 if(!backendMode)$("menu-note").textContent+=" · نمایش نمونه؛ برای سفارش واقعی API را وصل کنید.";
 $("product-grid").innerHTML=list.map(p=>'<article class="product-card">'+visual(p)+'<div class="product-content"><div class="product-top"><h3>'+esc(p.name)+'</h3><span class="product-price">'+money(p.price_toman||p.price)+'</span></div><p class="product-desc">'+esc(p.description)+'</p><div class="tag-row">'+(p.tags||[]).slice(0,3).map(t=>'<span class="tag">'+esc(t)+"</span>").join("")+'</div><div class="product-actions"><span class="availability">● موجود</span><button type="button" class="button button-outline" data-add="'+esc(p.id)+'">افزودن به سبد +</button></div></div></article>').join("");
 $("product-grid").hidden=list.length===0;
 if(!list.length){$("product-grid").hidden=false;$("product-grid").innerHTML='<div class="empty-state">چیزی با این مشخصات پیدا نکردیم؛ عبارت دیگری را امتحان کن.</div>';}
}
function findItem(key){
 const parts=key.split(":");const id=parts.slice(1).join(":");
 if(parts[0]==="c")return combos.find(c=>String(c.id)===id);
 return products.find(p=>String(p.id)===id);
}
function itemPrice(item){return Number(item&&(item.price_toman||item.price)||0);}
function addToCart(id){
 const p=products.find(x=>String(x.id)===String(id));
 if(!p||!p.available)return toast("این محصول اکنون موجود نیست.",true);
 const key="p:"+p.id;cart.set(key,Math.min(20,(cart.get(key)||0)+1));renderCart();toast(p.name+" به سبد اضافه شد.");
}
function addCombo(id){
 const c=combos.find(x=>String(x.id)===String(id));
 if(!c||!c.active)return toast("این ترکیب اکنون در دسترس نیست.",true);
 const key="c:"+c.id;cart.set(key,Math.min(20,(cart.get(key)||0)+1));renderCart();toast("«"+c.name+"» به سبد اضافه شد.");
}
function renderCart(){
 $("cart-count").textContent=num([...cart.values()].reduce((a,b)=>a+b,0));
 let total=0;
 const lines=[...cart.entries()].map(([key,qty])=>{
  const item=findItem(key);if(!item)return "";
  const price=itemPrice(item);total+=price*qty;
  return '<div class="cart-line"><div><strong>'+esc(item.name)+'</strong><small>'+money(price)+' · '+money(price*qty)+'</small></div><div class="quantity-controls"><button type="button" data-qty="'+esc(key)+'" data-delta="-1" aria-label="کم کردن تعداد">−</button><span>'+num(qty)+'</span><button type="button" data-qty="'+esc(key)+'" data-delta="1" aria-label="زیاد کردن تعداد">+</button></div></div>';
 }).join("");
 $("cart-total").textContent=money(total);$("cart-items").innerHTML=lines||'<div class="cart-empty">سبد سفارش هنوز خالی است.<br>از منو چیزی برای خودت انتخاب کن.</div>';
 $("submit-order").disabled=!cart.size;
}
function openCart(){$("cart-overlay").hidden=false;document.body.style.overflow="hidden";$("close-cart").focus();}
function closeCart(){$("cart-overlay").hidden=true;document.body.style.overflow="";}
function openClub(){
 $("club-error").hidden=true;
 const user=readClubUser();
 if(user&&user.role==="customer"){showClubAccount();}else{clubMode="login";setClubMode();}
 if(!$("club-dialog").open)$("club-dialog").showModal();
}
function readClubUser(){try{return JSON.parse(localStorage.getItem("aramesh-user")||"null");}catch(_){return null;}}
function setClubMode(){
 $("club-name-label").hidden=clubMode!=="register";$("club-name").hidden=clubMode!=="register";$("club-name").required=clubMode==="register";
 $("club-submit").textContent=clubMode==="register"?"ساخت حساب":"ورود";
 $("club-switch").textContent=clubMode==="register"?"قبلاً حساب ساخته‌ای؟ ورود":"ساخت حساب مشتری";
 $("club-dialog-description").textContent=clubMode==="register"?"برای نگهداری امتیازهای باشگاه حساب مشتری بساز.":"برای دیدن امتیازهای حساب مشتری وارد شو.";
 $("club-account").hidden=true;$("club-email").hidden=false;$("club-password").hidden=false;$("club-name").hidden=clubMode!=="register";$("club-name-label").hidden=clubMode!=="register";$("club-switch").hidden=false;$("club-submit").hidden=false;
}
async function showClubAccount(){
 $("club-error").hidden=true;
 try{
 const data=await api("/api/loyalty/me");
 $("club-points-value").textContent=num(data.points);
 $("club-rewards").innerHTML=(data.rewards||[]).map(r=>'<div class="reward-line"><div><strong>'+esc(r.name)+'</strong><small>'+num(r.points)+' امتیاز · '+money(r.discount_toman)+'</small></div><button class="button button-outline" data-redeem="'+esc(r.id)+'">درخواست پاداش</button></div>').join("")||'<p class="small muted">پاداش فعالی تعریف نشده است.</p>';
 $("club-history").innerHTML=(data.history||[]).map(h=>'<div class="history-line"><span>'+esc(h.reason==="order_earned"?"امتیاز سفارش تکمیل‌شده":h.reason.startsWith("reward_redeemed:")?"درخواست پاداش":"تغییر امتیاز")+'</span><strong>'+((h.points_delta>0?"+":"")+num(h.points_delta))+'</strong></div>').join("")||'<p class="small muted">هنوز تغییری در امتیاز ثبت نشده است.</p>';
 $("club-account").hidden=false;$("club-email").hidden=true;$("club-password").hidden=true;$("club-name").hidden=true;$("club-name-label").hidden=true;$("club-submit").hidden=true;$("club-switch").hidden=true;
 $("club-dialog-description").textContent="امتیاز و تاریخچه از اطلاعات حساب مشتری خوانده شده است.";
 $("club-card-status").textContent=num(data.points)+" امتیاز قابل استفاده";
 }catch(e){$("club-error").textContent=e.message;$("club-error").hidden=false;}
}
function discoverLocal(text){
 const q=normalize(text);if(!q){$("discovery-results").innerHTML="";return;}
 const rules=[
 {keys:["سرد","خنک","یخ","آیس"],test:p=>p.temperature==="سرد",label:"سرد"},
 {keys:["ترش","لیمویی","مرکبات"],test:p=>(p.flavors||[]).some(f=>["ترش","مرکباتی"].includes(f)),label:"ترش و مرکباتی"},
 {keys:["قوی","پرکافئین","انرژی","بیدار","درس خوندن","تمرکز"],test:p=>p.caffeine==="زیاد",label:"قهوه قوی"},
 {keys:["کم شیرین","کمشیرین","شیرین نباشه","بدون شکر","کم‌شیرین"],test:p=>!(p.flavors||[]).includes("شیرین"),label:"کم‌شیرین"},
 {keys:["بدون شیر","غیرلبنی","شیر نداشته"],test:p=>p.attributes?p.attributes.dairy_free===true:!p.milk,label:"بدون شیر"},
 {keys:["میوه","بری"],test:p=>(p.flavors||[]).includes("میوه‌ای"),label:"میوه‌ای"},
 {keys:["بدون کافئین","کافئین نداشته"],test:p=>p.caffeineFree===true||p.caffeine==="بدون کافئین",label:"بدون کافئین"},
 {keys:["گرم","داغ"],test:p=>p.temperature==="گرم",label:"گرم"}];
 const active=rules.filter(r=>r.keys.some(k=>q.includes(normalize(k))));
 const ranked=products.filter(p=>p.available).map(p=>({p:p,score:active.reduce((s,r)=>s+(r.test(p)?3:-3),0)})).filter(x=>active.length?x.score>0:normalize([x.p.name,x.p.description,...(x.p.tags||[])].join(" ")).split(" ").some(t=>t.length>3&&q.includes(t))).sort((a,b)=>b.score-a.score).slice(0,3);
 renderDiscoveryResults(ranked.map(x=>Object.assign({},x.p,{match_reasons:active.filter(r=>r.test(x.p)).map(r=>r.label)})),text);
}
function renderDiscoveryResults(rows,queryText){
 $("discovery-results").innerHTML=rows.length?rows.map(p=>'<div class="mini-result"><strong>'+esc(p.name)+'</strong><span>'+money(p.price_toman||p.price)+' · '+esc((p.match_reasons||[]).join("، ")||"پیشنهاد از منوی کافه")+'</span><p class="small muted">'+esc(p.description)+'</p><button class="button button-outline" type="button" data-add="'+esc(p.id)+'">افزودن به سبد</button></div>').join(""):'<div class="mini-result"><strong>هنوز انتخاب دقیقی پیدا نکردیم.</strong><span>طعم یا ویژگی مشخصی مثل «سرد»، «ترش»، «قهوه قوی» یا «بدون شیر» را امتحان کن.</span></div>';
}
async function discover(text){
 if(!String(text||"").trim())return;
 $("discovery-results").innerHTML='<div class="mini-result">در حال بررسی گزینه‌های منو…</div>';
 if(backendMode){
  try{const data=await api("/api/search/natural?query="+encodeURIComponent(text));renderDiscoveryResults(data.matches||[],text);if(data.message&&!data.matches.length)toast(data.message);return;}
  catch(e){toast(e.message,true);}
 }
 discoverLocal(text);
}
async function renderCombos(){
 const host=$("combo-grid");
 if(!backendMode){host.innerHTML='<div class="empty-state">پیشنهادهای ترکیبی پس از اتصال API نمایش داده می‌شوند؛ در این نسخه قیمت یا ترکیب ساختگی معرفی نمی‌شود.</div>';return;}
 try{
 combos=(await api("/api/combos")).filter(c=>c.active);
 host.innerHTML=combos.length?combos.map(c=>'<article class="combo-card"><div class="combo-art-mini"><span>✳</span></div><h3>'+esc(c.name)+'</h3><p>'+esc(c.description)+'</p><div class="combo-products-mini">'+(c.products||[]).map(p=>'<span>'+esc(p.name)+'</span>').join("")+'</div><div class="combo-price-line"><div><strong>'+money(c.price_toman)+'</strong><small>'+(c.discount_toman?"صرفه‌جویی "+money(c.discount_toman):"قیمت ترکیب")+'</small></div><button class="button button-outline" data-add-combo="'+c.id+'">افزودن</button></div></article>').join(""):'<div class="empty-state">ترکیب فعالی برای نمایش وجود ندارد.</div>';
 }catch(e){host.innerHTML='<div class="empty-state">'+esc(e.message)+'</div>';}
}
async function loadRemoteMenu(){
 renderCategories();renderProducts();renderCart();renderCombos();
 if(!canTryApi()){
 announce("نمایش نمونه فعال است؛ برای سفارش واقعی، نشانی API را در config.js تنظیم کنید.");
 loadWorkConfig();
 return;
 }
 try{
 const data=await api("/api/menu");
 products=(data.products||[]).map(mapApiProduct);
 categories=["همه"].concat((data.categories||[]).map(c=>c.name));
 backendMode=true;activeCategory="همه";
 renderCategories();renderProducts();renderCart();await renderCombos();
 announce("منوی زنده کافه آرامش · اطلاعات از API دریافت شد.");
 }catch(e){
 backendMode=false;renderCategories();renderProducts();renderCombos();
 announce("API در دسترس نیست؛ فعلاً منوی نمونه نمایش داده می‌شود. سفارش واقعی ثبت نمی‌شود.");
 }
 loadWorkConfig();
}
async function loadWorkConfig(){
 if(!canTryApi())return;
 try{
 workConfig=await api("/api/work-mode");
 const select=$("work-duration");
 if(Array.isArray(workConfig.durations)&&workConfig.durations.length){select.innerHTML=workConfig.durations.map(d=>'<option value="'+Number(d)+'">'+num(d/60)+' ساعت · '+num(d)+' دقیقه</option>').join("");}
 }catch(_){}
}
async function submitOrder(){
 if(!backendMode)return toast("سفارش ثبت نشد؛ API واقعی به این نسخه متصل نیست. نشانی API را در config.js تنظیم کن.",true);
 if(!cart.size)return toast("سبد سفارش خالی است.",true);
 const button=$("submit-order");button.disabled=true;button.textContent="در حال ثبت درخواست…";
 const items=[...cart.entries()].map(([key,quantity])=>{const bits=key.split(":");return {kind:bits[0]==="c"?"combo":"product",id:Number(bits[1]),quantity:quantity};});
 const key=window.crypto&&crypto.randomUUID?crypto.randomUUID():String(Date.now())+"-"+Math.random().toString(16).slice(2);
 try{
 const result=await api("/api/orders",{method:"POST",body:JSON.stringify({table_token:$("table-select").value,items:items,idempotency_key:key})});
 cart.clear();renderCart();$("order-feedback").textContent=result.message+"\\nکد پیگیری: "+result.id+"\\nکد تأیید مشتری: "+result.confirmation_code+"\\nمبلغ درخواست: "+money(result.total_toman)+"\\nاین کد را هنگام مراجعه به گارسون اعلام کنید. پرداخت آنلاین انجام نشده است.";
 $("order-feedback").hidden=false;toast("درخواست شما ثبت شد؛ کد تأیید را نزد خود نگه دار.",false);
 }catch(e){$("order-feedback").textContent=e.message;$("order-feedback").hidden=false;toast(e.message,true);}
 finally{button.disabled=!cart.size;button.textContent="ثبت درخواست سفارش";}
}
async function startWork(){
 if(!backendMode)return toast("برای فعال‌سازی واقعی، API را راه‌اندازی و در config.js تنظیم کنید.",true);
 const orderId=$("work-order-ref").value.trim();
 if(!orderId)return toast("کد پیگیری سفارش تأییدشده را وارد کن.",true);
 const button=$("start-work");button.disabled=true;
 try{
 const result=await api("/api/work-mode/sessions",{method:"POST",body:JSON.stringify({order_id:orderId,duration_minutes:Number($("work-duration").value)})});
 $("work-feedback").textContent="جلسه فعال شد. پایان زمان: "+faDate(result.expires_at)+". "+result.instructions+" "+result.notice;
 toast("جلسه مطالعه و کار ثبت شد.");
 }catch(e){$("work-feedback").textContent=e.message;toast(e.message,true);}
 finally{button.disabled=false;}
}
function setClubCard(user){$("club-card-title").textContent=user?"باشگاه مشتریان · "+user.full_name:"باشگاه مشتریان آرامش";}
$("categories").addEventListener("click",e=>{const b=e.target.closest("[data-category]");if(!b)return;activeCategory=b.dataset.category;renderCategories();renderProducts();});
$("product-grid").addEventListener("click",e=>{const b=e.target.closest("[data-add]");if(b)addToCart(b.dataset.add);});
$("combo-grid").addEventListener("click",e=>{const b=e.target.closest("[data-add-combo]");if(b)addCombo(b.dataset.addCombo);});
$("discovery-results").addEventListener("click",e=>{const b=e.target.closest("[data-add]");if(b)addToCart(b.dataset.add);});
$("menu-search").addEventListener("input",e=>{query=e.target.value;renderProducts();});
$("clear-search").addEventListener("click",()=>{$("menu-search").value="";query="";renderProducts();$("menu-search").focus();});
$("open-discovery").addEventListener("click",()=>{$("discover").scrollIntoView({behavior:"smooth"});$("preference-input").focus({preventScroll:true});});
$("discovery-form").addEventListener("submit",e=>{e.preventDefault();discover($("preference-input").value);});
$("open-cart").addEventListener("click",openCart);$("close-cart").addEventListener("click",closeCart);$("cart-overlay").addEventListener("click",e=>{if(e.target===$("cart-overlay"))closeCart();});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!$("cart-overlay").hidden)closeCart();});
$("cart-items").addEventListener("click",e=>{const b=e.target.closest("[data-qty]");if(!b)return;const key=b.dataset.qty,n=(cart.get(key)||0)+Number(b.dataset.delta);if(n<=0)cart.delete(key);else cart.set(key,Math.min(20,n));renderCart();});
$("submit-order").addEventListener("click",submitOrder);
$("start-work").addEventListener("click",startWork);
$("club-info").addEventListener("click",openClub);
$("club-close").addEventListener("click",()=>$("club-dialog").close());
$("club-switch").addEventListener("click",()=>{clubMode=clubMode==="register"?"login":"register";$("club-error").hidden=true;setClubMode();});
$("club-login-form").addEventListener("submit",async e=>{
 e.preventDefault();$("club-error").hidden=true;
 try{
  const body={email:$("club-email").value.trim(),password:$("club-password").value};
  const path=clubMode==="register"?"/api/auth/register":"/api/auth/login";
  if(clubMode==="register")body.full_name=$("club-name").value.trim();
  const result=await api(path,{method:"POST",body:JSON.stringify(body)});
  if(result.user.role!=="customer")throw new Error("این حساب، حساب مشتری باشگاه نیست.");
  localStorage.setItem("aramesh-token",result.access_token);localStorage.setItem("aramesh-user",JSON.stringify(result.user));
  setClubCard(result.user);await showClubAccount();toast("ورود به باشگاه انجام شد.");
 }catch(e){$("club-error").textContent=e.message;$("club-error").hidden=false;}
});
$("club-account").addEventListener("click",async e=>{
 const b=e.target.closest("[data-redeem]");if(!b)return;
 try{const result=await api("/api/loyalty/redeem",{method:"POST",body:JSON.stringify({reward_id:b.dataset.redeem})});toast(result.message);await showClubAccount();}
 catch(err){toast(err.message,true);}
});
$("club-logout").addEventListener("click",()=>{localStorage.removeItem("aramesh-token");localStorage.removeItem("aramesh-user");$("club-dialog").close();$("club-card-status").textContent="برای مشاهده امتیازها وارد حساب شو";setClubCard(null);});
async function restoreClub(){
 const user=readClubUser();if(!user||user.role!=="customer")return;
 setClubCard(user);if(canTryApi()){try{await showClubAccount();}catch(_){}}
}
renderCategories();renderProducts();renderCart();loadRemoteMenu();restoreClub();
