/* Admin Mode - Standalone */
(function(){
  var ch={};
  try{ch=JSON.parse(sessionStorage.getItem('ac')||'{}');}catch(e){}
  var btn=document.createElement('button');
  btn.textContent='\u2699';
  btn.style.cssText='position:fixed;bottom:10px;right:10px;background:rgba(255,255,255,0.15);color:#888;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:16px;z-index:9999;';
  btn.onclick=function(){
    var p=prompt('Admin password:');
    if(p==='admin123') startAdmin();
  };
  document.body.appendChild(btn);

  function startAdmin(){
    btn.style.display='none';
    var bar=document.createElement('div');
    bar.style.cssText='position:fixed;top:0;left:0;right:0;background:#ff6b00;color:#fff;padding:8px 15px;z-index:10000;text-align:center;font-size:14px;display:flex;justify-content:space-between;align-items:center;direction:rtl;';
    bar.innerHTML='<span>\uD83D\uDD27 \u05DE\u05E6\u05D1 \u05DE\u05E0\u05D4\u05DC - \u05DC\u05D7\u05E5 \u05E2\u05DC \u05DE\u05D5\u05E6\u05E8 \u05DC\u05E9\u05E0\u05D5\u05EA \u05EA\u05DE\u05D5\u05E0\u05D4 | <b id="acnt">0</b> \u05E9\u05D9\u05E0\u05D5\u05D9\u05D9\u05DD</span><div><button onclick="window._aExport()" style="margin:0 3px;padding:4px 12px;border:none;border-radius:4px;cursor:pointer;">\uD83D\uDCBE \u05D9\u05D9\u05E6\u05D0</button><button onclick="location.reload()" style="margin:0 3px;padding:4px 12px;border:none;border-radius:4px;cursor:pointer;">\u2716 \u05E1\u05D2\u05D5\u05E8</button></div>';
    document.body.prepend(bar);
    document.body.style.paddingTop='45px';
    updCnt();

    var cards=document.querySelectorAll('.product-card');
    cards.forEach(function(card,i){
      card.style.cursor='pointer';
      card.style.outline=ch[i]!==undefined?'3px solid #00c853':'';
      card.addEventListener('click',function(e){
        e.preventDefault();e.stopPropagation();
        openPick(i);
      },true);
    });
  }

  function openPick(idx){
    var old=document.getElementById('_apick');
    if(old) old.remove();
    var pr=PRODUCTS[idx];
    if(!pr) return;
    var imgs=pr.images||[];
    var sel=ch[idx]||0;
    var ov=document.createElement('div');
    ov.id='_apick';
    ov.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);z-index:10001;overflow-y:auto;padding:20px;direction:rtl;';
    var h='<div style="max-width:900px;margin:0 auto;"><h3 style="color:#fff;margin-bottom:15px;">'+(pr.title||'')+'</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;">';
    imgs.forEach(function(src,j){
      var border=j===sel?'3px solid #00c853':'3px solid transparent';
      h+='<div class="_aopt" data-j="'+j+'" style="cursor:pointer;border:'+border+';border-radius:8px;overflow:hidden;position:relative;"><img src="'+src+'" style="width:100%;height:150px;object-fit:cover;" onerror="this.style.background=\'#333\'"><div style="position:absolute;bottom:5px;right:5px;background:rgba(0,0,0,0.7);color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">#'+(j+1)+'</div></div>';
    });
    h+='</div><div style="margin-top:15px;text-align:center;"><button id="_asave" style="padding:8px 20px;margin:0 5px;border:none;border-radius:4px;cursor:pointer;background:#00c853;color:#fff;font-size:14px;">\u2713 \u05E9\u05DE\u05D5\u05E8</button><button onclick="document.getElementById(\'_apick\').remove()" style="padding:8px 20px;margin:0 5px;border:none;border-radius:4px;cursor:pointer;background:#666;color:#fff;font-size:14px;">\u2716 \u05D1\u05D8\u05DC</button></div></div>';
    ov.innerHTML=h;
    document.body.appendChild(ov);

    ov.querySelectorAll('._aopt').forEach(function(opt){
      opt.onclick=function(){
        ov.querySelectorAll('._aopt').forEach(function(o){o.style.border='3px solid transparent';});
        opt.style.border='3px solid #00c853';
        sel=parseInt(opt.getAttribute('data-j'));
      };
    });

    document.getElementById('_asave').onclick=function(){
      ch[idx]=sel;
      sessionStorage.setItem('ac',JSON.stringify(ch));
      var card=document.querySelectorAll('.product-card')[idx];
      if(card){
        card.style.outline='3px solid #00c853';
        var ci=card.querySelector('.gallery-img');
        if(ci&&imgs[sel]) ci.src=imgs[sel];
      }
      updCnt();
      ov.remove();
    };
  }

  function updCnt(){
    var el=document.getElementById('acnt');
    if(el) el.textContent=Object.keys(ch).length;
  }

  window._aExport=function(){
    var blob=new Blob([JSON.stringify(ch,null,2)],{type:'application/json'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='admin_changes.json';
    a.click();
  };
})();
