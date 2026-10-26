const fs=require('fs'),path=require('path');
const {HumanMotion,installCursor,sleep}=require('./motion.cjs');
function arg(name){const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1]}
function playwright(){try{return require('playwright')}catch{if(process.env.PLAYWRIGHT_MODULE)return require(process.env.PLAYWRIGHT_MODULE);throw Error('Install playwright or set PLAYWRIGHT_MODULE to its absolute module path')}}
async function record(planPath,out){
 const plan=JSON.parse(fs.readFileSync(planPath,'utf8'));fs.mkdirSync(out,{recursive:true});
 const {chromium}=playwright();let browser;
 try{
  browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
  const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,locale:plan.locale||'ko-KR',recordVideo:{dir:path.join(out,'raw'),size:{width:1920,height:1080}}});await installCursor(context);
  let page=await context.newPage();await page.goto(plan.url,{waitUntil:'domcontentloaded'});if(plan.readySelector)await page.locator(plan.readySelector).waitFor({state:'visible'});await sleep(1000);
  const clock=Date.now(),events=[],scenes=[],videoPages=new Map([[page,{start:clock,video:page.video()}]]);
  const log=(action,data)=>events.push({time:(Date.now()-clock)/1000,action,...data});
  let human=new HumanMotion(page,log);await page.mouse.move(...human.xy);
  for(const item of plan.scenes){
   const opened=[];const popupHandler=p=>{opened.push(p);videoPages.set(p,{start:Date.now(),video:p.video()})};context.on('page',popupHandler);
   let segmentStart=(Date.now()-clock)/1000,segmentPage=page;const parts=[];
   for(const a of item.actions||[]){
    const loc=a.selector?page.locator(a.selector).first():null;
    if(a.kind==='click')await human.click(loc);
    else if(a.kind==='hover')await human.hover(loc);
    else if(a.kind==='type')await human.type(loc,a.text,a);
    else if(a.kind==='scroll')await human.scroll(a.delta,a.ms);
    else if(a.kind==='move')await human.move(a.x,a.y,a.ms);
    else if(a.kind==='wait')await sleep(a.ms??500);
    else if(a.kind==='ready')await loc.waitFor({state:'visible',timeout:a.timeout??15000});
    else throw Error('Unknown action '+a.kind);
    await sleep(100);
    if(opened.length){
      const next=opened.shift();await next.waitForLoadState('domcontentloaded');
      const cut=(videoPages.get(next).start-clock)/1000;
      parts.push({page:segmentPage,start:segmentStart,end:cut});page=next;await page.bringToFront();human=new HumanMotion(page,log,human.xy);segmentPage=page;segmentStart=cut;await human.move(...human.xy,120);
    }
    if(a.waitForSelector)await page.locator(a.waitForSelector).waitFor({state:'visible'});
   }
   if(item.readySelector)await page.locator(item.readySelector).waitFor({state:'visible'});
   let focus=null;
   if(item.focusSelector){const b=await page.locator(item.focusSelector).first().boundingBox();if(!b||b.y<0||b.x<0||b.y+b.height>1080||b.x+b.width>1920)throw Error('Focus target outside viewport');focus={x:b.x/1920,y:b.y/1080,w:b.width/1920,h:b.height/1080}}
   await sleep(item.holdMs??1800);const end=(Date.now()-clock)/1000;parts.push({page:segmentPage,start:segmentStart,end});
   const screenshot=path.join(out,`${item.id}.png`);await page.screenshot({path:screenshot});context.off('page',popupHandler);
   scenes.push({...item,focus,parts,screenshot});
  }
  const end=Date.now();await context.close();
  for(const [p,v] of videoPages){v.file=await v.video.path();v.offset=(v.start-clock)/1000;v.elapsed=(end-v.start)/1000;}
  for(const s of scenes)s.parts=s.parts.map(v=>({file:videoPages.get(v.page).file,start:v.start-videoPages.get(v.page).offset,end:v.end-videoPages.get(v.page).offset,pageElapsed:videoPages.get(v.page).elapsed}));
  fs.writeFileSync(path.join(out,'recording.json'),JSON.stringify({resolution:[1920,1080],recordedSeconds:(end-clock)/1000,scenes,events,sourceType:'actual browser recording',cursor:'event-based overlay'},null,2));
  console.log('Saved recording and scene evidence: '+out);
 }finally{if(browser)await browser.close()}
}
if(require.main===module){const plan=arg('--plan'),out=arg('--out');if(!plan||!out){console.error('node record.cjs --plan plan.json --out build');process.exitCode=1}else record(path.resolve(plan),path.resolve(out)).catch(e=>{console.error(e.message);process.exitCode=1})}
module.exports={record};
