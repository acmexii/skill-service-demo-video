const http=require('http'),fs=require('fs'),path=require('path');
const {record}=require('./record.cjs');
const out=path.resolve(process.argv[process.argv.indexOf('--out')+1]||'demo-validation');
const html=`<!doctype html><meta charset="utf-8"><style>body{font:30px sans-serif;margin:80px;background:#f5f6fa;color:#252535}h1{color:#67519e}input,button{font:30px sans-serif;padding:18px}#result{margin-top:35px;width:650px;height:140px;padding:24px;background:white;border:2px solid #67519e}#lower{margin-top:600px;height:220px;width:650px;padding:30px;background:#e6def5}iframe{width:450px;height:120px}</style><h1>서비스 영상 코드 검증용 데모</h1><input id="q"><button id="go" onclick="document.querySelector('#result').textContent='검색 결과: '+document.querySelector('#q').value">검색</button><div id="result">검색할 문서를 입력하세요</div><section id="lower">공유 권한을 확인하는 데모 영역<br><a id="open" href="/popup" target="_blank">새 탭 열기</a></section><script>document.querySelector('#q').addEventListener('input',()=>{window.inputSamples=window.inputSamples||[];window.inputSamples.push({text:document.querySelector('#q').value,time:performance.now()})})</script>`;
const popup=`<!doctype html><meta charset="utf-8"><style>body{margin:100px;font:32px sans-serif}#panel{width:620px;padding:30px;background:#f0e9fa}iframe{margin-top:40px;width:620px;height:180px}</style><h1>새 탭의 실제 결과</h1><div id="panel">공유 결과를 확인했습니다</div><iframe src="/frame"></iframe>`;
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(req.url==='/popup'?popup:req.url==='/frame'?'<body style="font:30px sans-serif">iframe 안의 커서 검증</body>':html)});
server.listen(0,'127.0.0.1',async()=>{try{
 fs.mkdirSync(out,{recursive:true});
 const plan={url:`http://127.0.0.1:${server.address().port}/`,readySelector:'#q',scenes:[
 {id:'search',duration:8,narration:'문서를 한 글자씩 검색합니다.',actions:[{kind:'type',selector:'#q',text:'데모 문서',min:100,max:200},{kind:'click',selector:'#go',waitForSelector:'#result'},{kind:'move',x:1000,y:700,ms:500}],holdMs:650,focusSelector:'#result',zoom:1.25,callout:'검색 결과 확인'},
 {id:'scroll',duration:5,narration:'아래로 이동해 공유 권한을 확인합니다.',actions:[{kind:'scroll',delta:650,ms:800},{kind:'move',x:1000,y:700,ms:500}],holdMs:650,focusSelector:'#lower',zoom:1.2,callout:'공유 설정 영역'},
 {id:'popup',duration:7,narration:'새 탭에서도 커서가 자연스럽게 이어집니다.',actions:[{kind:'click',selector:'#open',waitForSelector:'#panel'},{kind:'move',x:400,y:410,ms:650}],holdMs:700,focusSelector:'#panel',zoom:1.2,callout:'새 탭 결과'}]};
 fs.writeFileSync(path.join(out,'plan.json'),JSON.stringify(plan,null,2));await record(path.join(out,'plan.json'),out);
 const meta=JSON.parse(fs.readFileSync(path.join(out,'recording.json')));
 if(!meta.events.some(e=>e.action==='type')||!meta.events.some(e=>e.action==='scroll'))throw Error('Missing interaction evidence');
 if(new Set(meta.scenes.flatMap(s=>s.parts.map(p=>p.file))).size!==2)throw Error('Popup recording missing');
 for(const scene of meta.scenes){const recorded=scene.parts.reduce((n,p)=>n+p.end-p.start,0);scene.duration=Math.max(scene.duration,Math.ceil(recorded)+2);scene.silentPreview=true}
 fs.writeFileSync(path.join(out,'recording.json'),JSON.stringify(meta,null,2));
 console.log('Local interaction smoke test passed. Render separately to inspect zoom and masks.');
 }catch(e){console.error(e.message);process.exitCode=1}finally{server.close()}});
