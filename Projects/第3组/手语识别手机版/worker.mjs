import {unpack,calculate,makeFeatures,ranking} from "./recognizer.mjs";

async function load(){
  const metadata=await fetch("./assets/model.json");
  if(!metadata.ok)throw Error("无法下载识别模型");
  const meta=await metadata.json();
  const responses=await Promise.all(meta.modelFiles.map(file=>fetch("./assets/"+file)));
  if(responses.some(response=>!response.ok))throw Error("模型文件缺失，请重新载入页面。");
  const payload=new Uint8Array(await new Blob(await Promise.all(responses.map(r=>r.arrayBuffer()))).arrayBuffer());
  const buffer=payload[0]===31&&payload[1]===139?
    await new Response(new Blob([payload]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer():
    payload.buffer;
  return unpack(meta,buffer);
}
let loading;
self.onmessage=async({data})=>{
  try{
    loading??=load().catch(error=>{loading=null;throw error;});
    const model=await loading;
    const choices=data.landmarks?ranking(calculate(makeFeatures(data.landmarks),model)).map(i=>model.labels[i]):null;
    self.postMessage({id:data.id,choices});
  }catch(error){self.postMessage({id:data.id,error:error.message});}
};
