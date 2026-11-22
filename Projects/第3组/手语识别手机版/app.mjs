import {prepareVision,readLandmarks,squareFrame} from "./capture.mjs";

const by=(id)=>document.getElementById(id);
const sampleList=by("example-list"),preview=by("poster"),video=by("camera-view"),overlay=by("overlay"),action=by("primary-action");
const hint=by("hint"),state=by("model-status"),stageStatus=by("stage-status"),dialog=by("vocab-dialog"),stopCamera=by("stop-camera");
const modeButtons=[...document.querySelectorAll("[data-mode][aria-pressed]")];
const statusText={
  example:"样例使用预先提取的骨架，在本机运行识别。",
  camera:"相机画面在浏览器内处理。",
  video:"从相册选择约 2 秒的视频，画面中只做一个完整手语词。",
};
const wait=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
let mode="camera",examples=[],selected=0,stream=null,videoURL=null,busy=false,words=[],history=[],topWord="",operation=0;
let worker,requestId=0;
let modelReady;
const pending=new Map();

function askWorker(landmarks){
  if(!worker){
    worker=new Worker("./worker.mjs",{type:"module"});
    worker.onmessage=({data})=>{
      const callbacks=pending.get(data.id);
      if(!callbacks)return;
      pending.delete(data.id);
      data.error?callbacks.reject(Error(data.error)):callbacks.resolve(data.choices);
    };
    worker.onerror=()=>{
      for(const cb of pending.values())cb.reject(Error("浏览器启动识别模型失败"));
      pending.clear();
      worker.terminate();worker=null;modelReady=null;
    };
  }
  const id=++requestId;
  return new Promise((resolve,reject)=>{
    pending.set(id,{resolve,reject});
    try{worker.postMessage({id,landmarks});}
    catch(error){pending.delete(id);reject(error);}
  });
}

function prepareModel(){
  modelReady??=Promise.resolve().then(()=>askWorker()).catch(error=>{modelReady=null;throw error;});
  return modelReady;
}

async function json(path){
  const response=await fetch(path);
  if(!response.ok)throw Error("无法读取 "+path);
  return response.json();
}

function stageMessage(text,recording=false){
  stageStatus.hidden=!text;stageStatus.textContent=text;
  by("stage").toggleAttribute("data-recording",recording);
}
function hintMessage(text,error=false){hint.textContent=text;hint.toggleAttribute("data-error",error);}
function resultStatus(text,ready=false){state.textContent=text;state.dataset.ready=String(ready);}
function clearOverlay(){overlay.getContext("2d").clearRect(0,0,overlay.width,overlay.height);}
function showEmpty(message){
  preview.hidden=true;video.hidden=true;by("empty-stage").hidden=false;
  by("empty-text").textContent=message;clearOverlay();
}
function showSample(index){
  const sample=examples[index];
  if(!sample)return;
  by("empty-stage").hidden=true;video.hidden=true;preview.hidden=false;
  preview.src=sample.photos[0];preview.alt="国家通用手语公开样例「"+sample.label+"」的动作帧";clearOverlay();
}
function setButton(){
  action.disabled=busy||(mode==="example"&&!examples.length);
  action.textContent=mode==="example"?"播放并识别":mode==="camera"?(stream?"录一段并识别":"打开摄像头"):"选择视频";
  stopCamera.hidden=mode!=="camera"||!stream;
}
function closeStream(){
  const previous=stream;
  stream=null;previous?.getTracks().forEach(track=>track.stop());
  video.pause();video.srcObject=null;
  if(videoURL){URL.revokeObjectURL(videoURL);videoURL=null;video.removeAttribute("src");video.load();}
}
function closeCamera(message,error=false){
  operation++;busy=false;closeStream();stageMessage("");
  showEmpty("打开摄像头后取景");
  hintMessage(message,error);
  resultStatus(topWord?"识别完成":"等待输入",Boolean(topWord));
  setButton();
}
function resetResult(){
  topWord="";by("result-word").textContent="—";by("result-detail").textContent="完成一个动作后，结果会显示在这里。";
  by("candidate-list").replaceChildren(Object.assign(document.createElement("li"),{className:"blank",textContent:"等待第一次识别"}));
  by("append-word").disabled=true;resultStatus("等待输入");
}
function changeMode(next){
  if(mode===next)return;
  operation++;busy=false;closeStream();mode=next;stageMessage("");resetResult();
  by("stage").dataset.mode=mode;
  for(const button of modeButtons)button.setAttribute("aria-pressed",button.dataset.mode===mode?"true":"false");
  sampleList.hidden=mode!=="example";hintMessage(statusText[mode]);
  if(mode==="example")showSample(selected);
  else showEmpty(mode==="camera"?"打开摄像头后取景":"选择一段本地视频");
  setButton();
}
function addWord(word){
  if(!word)return;
  history.push(word);by("transcript").textContent=history.join(" ");by("clear-record").disabled=false;
  by("transcript").closest("details").open=true;
}
function displayResult(choices,description){
  topWord=choices[0];
  by("result-word").textContent=topWord;by("result-detail").textContent=description;
  by("append-word").disabled=false;resultStatus("识别完成",true);
  by("candidate-list").replaceChildren(...choices.slice(1).map((choice,i)=>{
    const li=document.createElement("li"),button=document.createElement("button"),rank=document.createElement("small");
    button.type="button";button.textContent=choice;button.title="添加到文字记录";
    button.onclick=()=>addWord(choice);rank.textContent=String(i+2);li.append(button,rank);return li;
  }));
}
function drawPose(hands,body,mask){
  const ctx=overlay.getContext("2d"),n=overlay.width;
  clearOverlay();
  function track(points,edges,color){
    ctx.lineWidth=2.3;ctx.strokeStyle=color;ctx.fillStyle=color;
    for(const [i,j] of edges){
      const a=points[i],b=points[j];ctx.beginPath();ctx.moveTo(a[0]*n,a[1]*n);ctx.lineTo(b[0]*n,b[1]*n);ctx.stroke();
    }
    for(const v of points){ctx.beginPath();ctx.arc(v[0]*n,v[1]*n,2.5,0,2*Math.PI);ctx.fill();}
  }
  if(body.slice(1,3).every(v=>v[3]>.30))track(body.slice(1,7),[[0,1],[0,2],[1,3],[2,4],[3,5]],"#b4fbb4");
  const edges=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[0,9],[9,10],[10,11],[11,12],[0,13],[13,14],[14,15],[15,16],[0,17],[17,18],[18,19],[19,20]];
  hands.forEach((hand,i)=>{if(mask[i])track(hand,edges,i===0?"#72dfff":"#ffd672");});
}
async function perform(fn){
  if(busy)return;
  busy=true;
  const token=++operation;
  setButton();
  const active=()=>token===operation;
  try{await fn(active);}
  catch(error){
    if(active()){
      const message=error.message||"本次识别失败，请重新输入。";
      if(mode==="video"){closeStream();showEmpty("选择一段本地视频");}
      if(/activeTexture|WebGL|GL context/i.test(message)){
        hintMessage("浏览器无法运行手部关键点提取（WebGL）。请用 Safari 或 Chrome 重试，或用内置样例检查词模型。",true);
      }else if(error instanceof TypeError){
        hintMessage("模型资源或画面读取失败，请确认资源上传完整后刷新。",true);
      }else hintMessage(message,true);
      resultStatus("请重试");stageMessage("");
    }
  }finally{if(active()){busy=false;setButton();}}
}
async function runSample(active){
  const picked=examples[selected];
  if(!picked)return;
  resultStatus("模型运行中");
  hintMessage("正在播放样例并识别。首次加载模型可能需要等待。");
  const data=await json(picked.landmarks);
  if(!active())return;
  const request=askWorker(data).then(choices=>({choices}),error=>({error}));
  for(let i=0;i<picked.photos.length&&active();i++){
    preview.src=picked.photos[i];drawPose(data.hands[i],data.pose[i],data.hand_mask[i]);
    stageMessage("播放中");await wait(85);
  }
  if(!active())return;
  stageMessage("识别中");
  const {choices,error}=await request;
  if(error)throw error;
  if(active()){stageMessage("");hintMessage(statusText.example);displayResult(choices,"样例原词为「"+picked.label+"」");}
}
async function startCamera(active){
  if(!navigator.mediaDevices?.getUserMedia)throw Error("摄像头需要 HTTPS 或本机地址。请在系统浏览器打开部署地址，也可以试内置样例。");
  hintMessage("请在浏览器弹窗点「允许」。");
  try{
    const next=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:"user"},width:{ideal:640},height:{ideal:480}}});
    if(!active()){next.getTracks().forEach(track=>track.stop());return;}
    stream=next;
    next.getVideoTracks().forEach(track=>track.addEventListener("ended",()=>{
      if(stream===next)closeCamera("摄像头已断开，请重新打开。",true);
    },{once:true}));
    video.srcObject=stream;video.hidden=false;preview.hidden=true;by("empty-stage").hidden=true;
    setButton();
    await video.play();
    if(!active())return;
    prepareVision().catch(()=>{});
    prepareModel().catch(()=>{});
    hintMessage("确认双肩和双手入镜，点「录一段并识别」。");stageMessage("摄像头已开启");
    resultStatus("准备录制");
  }catch(error){
    if(!active())return;
    closeStream();showEmpty("摄像头未开启");
    if(error.name==="NotAllowedError"||error.name==="SecurityError")throw Error("请在浏览器的网站设置中允许摄像头并刷新，也可以从相册选视频。");
    if(error.name==="NotFoundError")throw Error("浏览器没有找到摄像头，可以试试相册视频。");
    throw Error("摄像头未打开。请退出正在用相机的应用，再重试。");
  }
}
async function runVision(frames,active,description){
  if(!active())return;
  resultStatus("提取骨架");stageMessage("提取骨架");
  const data=await readLandmarks(frames,(i,h,p,m)=>{
    if(!active())throw Error("识别已取消");
    drawPose(h,p,m);
  });
  if(!active())return;
  resultStatus("模型运行中");stageMessage("识别中");
  const choices=await askWorker(data);
  if(active()){
    stageMessage("");
    hintMessage(mode==="camera"?"可以再录一段，或关闭摄像头。":statusText.video);
    displayResult(choices,description);
  }
}
async function runCamera(active){
  resetResult();stageMessage("载入模型");resultStatus("载入模型");
  hintMessage("首次加载需要等待。看到「录制中」再开始动作。");
  await Promise.all([prepareVision(),prepareModel()]);
  if(!active())return;
  video.hidden=false;preview.hidden=true;clearOverlay();
  for(const seconds of [3,2,1]){
    if(!active())return;
    stageMessage("准备 "+seconds);await wait(1000);
  }
  if(!active())return;
  stageMessage("录制中",true);hintMessage("现在做一个完整手语词。");
  const frames=[];
  for(let i=0;i<12&&active();i++){
    const frame=document.createElement("canvas");squareFrame(video,frame);frames.push(frame);
    if(i<11)await wait(150);
  }
  if(active()){
    preview.src=frames.at(-1).toDataURL("image/jpeg",.9);
    preview.alt="刚录制的摄像头动作画面";
    preview.hidden=false;video.hidden=true;
    await runVision(frames,active,"摄像头动作 · 每次识别一个词");
  }
}
function waitFor(target,event,timeout=7000){
  return new Promise((resolve,reject)=>{
    let id;
    const finish=(error)=>{
      clearTimeout(id);target.removeEventListener(event,good);target.removeEventListener("error",bad);
      error?reject(error):resolve();
    };
    const good=()=>finish(),bad=()=>finish(Error("浏览器无法读取这个视频，请尝试 MP4 或 WebM。"));
    target.addEventListener(event,good,{once:true});target.addEventListener("error",bad,{once:true});
    id=setTimeout(()=>finish(Error("读取视频超时，请重试。")),timeout);
  });
}
async function runVideo(file,active){
  closeStream();resetResult();showEmpty("正在读取视频");resultStatus("读取视频");stageMessage("载入视频");
  hintMessage("正在读取相册视频。");
  videoURL=URL.createObjectURL(file);
  const ready=waitFor(video,"loadeddata");
  video.src=videoURL;video.load();
  await ready;
  if(!active())return;
  by("empty-stage").hidden=true;preview.hidden=true;video.hidden=false;video.pause();
  const duration=video.duration;
  if(!Number.isFinite(duration)||duration<.2)throw Error("视频太短或时长读取失败，请另录一段约 2 秒的视频。");
  const frames=[];
  for(let i=0;i<12&&active();i++){
    const t=(Math.max(.01,duration-.05))*i/11;
    if(Math.abs(video.currentTime-t)>.008){const seeked=waitFor(video,"seeked");video.currentTime=t;await seeked;}
    const frame=document.createElement("canvas");squareFrame(video,frame);frames.push(frame);
  }
  if(active())await runVision(frames,active,"相册视频 · 每次识别一个词");
}

for(const button of modeButtons)button.onclick=()=>changeMode(button.dataset.mode);
action.onclick=()=>{
  if(mode==="video")by("video-file").click();
  else if(mode==="example")perform(runSample);
  else perform(stream?runCamera:startCamera);
};
by("video-file").onchange=(event)=>{const file=event.target.files[0];event.target.value="";if(file&&mode==="video")perform(active=>runVideo(file,active));};
stopCamera.onclick=()=>closeCamera("摄像头已关闭。");
by("append-word").onclick=()=>addWord(topWord);
by("clear-record").onclick=()=>{history=[];by("transcript").textContent="选中的词会添加到这里。";by("clear-record").disabled=true;};
function filterWords(){
  const q=by("word-filter").value.trim().toLowerCase(),matches=words.filter(w=>w.toLowerCase().includes(q));
  by("word-list").replaceChildren(...matches.map(word=>Object.assign(document.createElement("li"),{textContent:word})));
  by("word-count").textContent="共 "+matches.length+" 词";
}
by("show-vocab").onclick=()=>{filterWords();dialog.showModal();by("word-filter").focus();};
by("close-vocab").onclick=()=>dialog.close();
by("word-filter").oninput=filterWords;
window.addEventListener("pagehide",()=>{
  if(mode==="camera"&&(stream||busy))closeCamera("摄像头已关闭。");
  if(mode==="video"&&(videoURL||busy)){
    operation++;busy=false;closeStream();showEmpty("选择一段本地视频");
    stageMessage("");hintMessage(statusText.video);resetResult();setButton();
  }
});
Promise.all([json("assets/examples.json"),json("assets/model.json")]).then(([items,meta])=>{
  examples=items;words=meta.labels;
  sampleList.replaceChildren(...examples.map((sample,index)=>{
    const button=document.createElement("button");button.type="button";button.textContent=sample.label;
    button.setAttribute("aria-pressed",index===0?"true":"false");
    button.onclick=()=>{
      if(mode!=="example")return;
      operation++;busy=false;selected=index;stageMessage("");hintMessage(statusText.example);resetResult();showSample(index);setButton();
      for(const item of sampleList.children)item.setAttribute("aria-pressed",item===button?"true":"false");
    };
    return button;
  }));
  if(mode==="example")showSample(0);setButton();
}).catch(()=>{hintMessage("网页资源加载失败。请用部署地址或本地服务打开完整目录。",true);});
setButton();
