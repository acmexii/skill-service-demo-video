const sleep = ms => new Promise(r => setTimeout(r, ms));
async function installCursor(context) {
  await context.addInitScript(() => {
    if (window !== window.top) {
      for (const type of ['mousemove','mousedown','mouseup']) document.addEventListener(type,e=>window.top.postMessage({demoCursor:true,type,x:e.clientX,y:e.clientY},'*'),true);
      return;
    }
    const init=()=>{
      const cursor=document.createElement('div');
      cursor.style.cssText='position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;display:none;filter:drop-shadow(1px 2px 2px #0008)';
      cursor.innerHTML='<svg width="32" height="40" viewBox="0 0 32 40"><path d="M3 2L4 29L11 23L18 36L24 33L17 21L29 20Z" fill="white" stroke="#111" stroke-width="2"/></svg>';
      document.documentElement.append(cursor);
      function update(type,x,y){
        cursor.style.display='block';cursor.style.transform=`translate(${x}px,${y}px)`;
        if(type==='mousedown'){
          const ring=document.createElement('div');ring.style.cssText=`position:fixed;left:${x-16}px;top:${y-16}px;width:32px;height:32px;border:3px solid #8c65e8;border-radius:50%;pointer-events:none;z-index:2147483646`;
          document.documentElement.append(ring);ring.animate([{transform:'scale(.4)',opacity:1},{transform:'scale(1.6)',opacity:0}],{duration:320}).finished.then(()=>ring.remove());
        }
      }
      for(const type of ['mousemove','mousedown','mouseup'])document.addEventListener(type,e=>update(type,e.clientX,e.clientY),true);
      window.addEventListener('message',e=>{
        if(!e.data?.demoCursor)return;
        const frame=[...document.querySelectorAll('iframe')].find(f=>f.contentWindow===e.source);
        if(frame){const b=frame.getBoundingClientRect();update(e.data.type,e.data.x+b.x,e.data.y+b.y)}
      });
    };
    document.documentElement?init():document.addEventListener('DOMContentLoaded',init,{once:true});
  });
}
class HumanMotion {
  constructor(page,log=()=>{},start=[160,820]){this.page=page;this.log=log;this.xy=start}
  async move(x,y,ms=700){
    const [sx,sy]=this.xy, distance=Math.hypot(x-sx,y-sy), bend=Math.min(65,distance*.12);
    const dx=x-sx,dy=y-sy,norm=distance||1,cx=(sx+x)/2-dy/norm*bend,cy=(sy+y)/2+dx/norm*bend;
    const n=Math.max(12,Math.ceil(ms/20));
    for(let i=1;i<=n;i++){let t=i/n;t=t*t*(3-2*t);await this.page.mouse.move((1-t)**2*sx+2*(1-t)*t*cx+t*t*x,(1-t)**2*sy+2*(1-t)*t*cy+t*t*y,{steps:3});await sleep(ms/n)}
    this.xy=[x,y];this.log('move',{from:[sx,sy],to:this.xy,duration:ms/1000,steps:3});
  }
  async target(locator,ms=700){await locator.waitFor({state:'visible'});const b=await locator.boundingBox();if(!b)throw Error('Target has no visible box');if(b.y<0||b.y+b.height>1080)throw Error('Scroll target into viewport before moving');await this.move(b.x+b.width*.5,b.y+b.height*.5,ms);return b}
  async click(locator){await this.target(locator);await sleep(220);await this.page.mouse.click(...this.xy);this.log('click',{at:this.xy})}
  async hover(locator){await this.target(locator);await sleep(250);this.log('hover',{at:this.xy})}
  async type(locator,text,{min=100,max=200,clear=false}={}){
    if(min<0||max<min)throw Error('Invalid typing delay');await this.click(locator);await locator.focus();
    if(clear){await locator.press(process.platform==='darwin'?'Meta+A':'Control+A');await locator.press('Backspace')}
    const chars=typeof Intl.Segmenter==='function'?[...new Intl.Segmenter('ko',{granularity:'grapheme'}).segment(text)].map(x=>x.segment):Array.from(text);
    for(const char of chars){await this.page.keyboard.insertText(char);await sleep(min+Math.random()*(max-min))}
    this.log('type',{characters:chars.length,method:'grapheme insertText',delayMs:[min,max]});await sleep(500);
    const actual=await locator.inputValue();if(actual!==text)throw Error('Typed value differs from planned text');
  }
  async scroll(delta,ms=800){const n=Math.ceil(ms/25);for(let i=1;i<=n;i++){const a=(i-1)/n,b=i/n;const ease=t=>t*t*(3-2*t);await this.page.mouse.wheel(0,delta*(ease(b)-ease(a)));await sleep(ms/n)}await sleep(450);this.log('scroll',{delta,duration:ms/1000})}
}
module.exports={HumanMotion,installCursor,sleep};
