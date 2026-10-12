/* PromptForge hero v2: halftone film reel (external) */
(function(){
/* halftone reel: draw 4 scene illustrations as dot grids, once, onto two canvases (cool + warm) */
  const art=document.getElementById('fxArt'),cool=document.getElementById('fxCool'),warm=document.getElementById('fxWarm');
  if(!art||!cool||!warm)return;
  const CELL=5,COLS=34,ROWS=60,GAP=22,HOLE=22,REPEAT=4;
  const FW=COLS*CELL,FH=ROWS*CELL,STEP=FW+GAP,PERIOD=4*STEP,W=PERIOD*REPEAT,H=FH+HOLE*2;
  const dpr=Math.min(window.devicePixelRatio||1,2);
  [cool,warm].forEach(c=>{c.width=W*dpr;c.height=H*dpr;c.style.width=W+'px';c.style.height=H+'px';c.style.setProperty('--p',-PERIOD+'px')});
  const load=url=>new Promise(res=>{
    const img=new Image();img.onload=()=>res(img);img.onerror=()=>res(null);
    img.src=url;
  });
  Promise.all(['assets/hero-s1.svg','assets/hero-s2.svg','assets/hero-s3.svg','assets/hero-s4.svg'].map(load)).then(imgs=>{
    try{
      /* sample each illustration into COLS x ROWS luminance cells */
      const cells=imgs.map(img=>{
        if(!img)return null;
        const s=document.createElement('canvas');s.width=COLS;s.height=ROWS;
        const g=s.getContext('2d',{willReadFrequently:true});g.drawImage(img,0,0,COLS,ROWS);
        const d=g.getImageData(0,0,COLS,ROWS).data,out=[];
        for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){
          const i=(r*COLS+c)*4,L=(0.2126*d[i]+0.7152*d[i+1]+0.0722*d[i+2])/255;
          /* soft vignette so frame edges melt into the dark */
          const nx=(c/COLS-.5)*2,ny=(r/ROWS-.5)*2,v=Math.max(0,1-.28*(nx*nx+ny*ny));
          out.push(Math.min(1,Math.pow(L,.55)*1.25*v));
        }
        return out;
      });
      const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t].map(Math.round);
      const palettes={
        cool:t=>mix([34,150,200],[207,250,254],t),
        warm:t=>mix([225,90,140],[253,205,90],t)
      };
      [['cool',cool],['warm',warm]].forEach(([name,cv])=>{
        const x=cv.getContext('2d');x.scale(dpr,dpr);
        /* sprocket holes along both edges of the strip */
        x.fillStyle='rgba(255,255,255,.2)';
        for(let px=6;px<W;px+=15){
          [[(HOLE-9)/2],[H-HOLE+(HOLE-9)/2]].forEach(([py])=>{x.beginPath();x.roundRect?x.roundRect(px,py,8,9,2):x.rect(px,py,8,9);x.fill()});
        }
        const pal=palettes[name];
        for(let rep=0;rep<REPEAT;rep++)for(let f=0;f<4;f++){
          const cl=cells[f];if(!cl)continue;
          const x0=(rep*4+f)*STEP+GAP/2,y0=HOLE;
          for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){
            const L=cl[r*COLS+c],rad=CELL*.52*Math.sqrt(L);
            if(rad<.5)continue;
            const [R,G,B]=pal(L);
            x.fillStyle='rgba('+R+','+G+','+B+','+(.3+.7*L).toFixed(2)+')';
            x.beginPath();x.arc(x0+c*CELL+CELL/2,y0+r*CELL+CELL/2,rad,0,6.2832);x.fill();
          }
          x.strokeStyle=name==='cool'?'rgba(103,232,249,.35)':'rgba(251,191,36,.38)';x.lineWidth=1;x.strokeRect(x0-.5,y0-.5,FW+1,FH+1);
        }
      });
      art.classList.add('ready');
    }catch(e){/* halftone is decoration only — hero still works without it */}
  });
})();
