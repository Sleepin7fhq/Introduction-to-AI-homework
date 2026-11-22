import {filled} from "./recognizer.mjs";

const POSE_IDS=[0,11,12,13,14,15,16,23,24];
const POSE_FRAMES=[0,3,6,8,11];
const blank=(n,w)=>Array.from({length:n},()=>Array(w).fill(0));

let vision;
export function prepareVision(){
  if(!vision)vision=(async()=>{
    const {FilesetResolver,HandLandmarker,PoseLandmarker}=await import("./assets/vision/vision_bundle.mjs");
    const files=await FilesetResolver.forVisionTasks(new URL("./assets/vision/wasm",import.meta.url).href);
    const hand=await HandLandmarker.createFromOptions(files,{
      baseOptions:{modelAssetPath:new URL("./assets/vision/hand_landmarker.task",import.meta.url).href},
      runningMode:"IMAGE",numHands:2,minHandDetectionConfidence:.35,minHandPresenceConfidence:.40,
    });
    try{
      const pose=await PoseLandmarker.createFromOptions(files,{
        baseOptions:{modelAssetPath:new URL("./assets/vision/pose_landmarker_lite.task",import.meta.url).href},
        runningMode:"IMAGE",minPoseDetectionConfidence:.45,minPosePresenceConfidence:.45,
      });
      return {hand,pose};
    }catch(error){hand.close();throw error;}
  })().catch(error=>{vision=null;throw error;});
  return vision;
}

export function squareFrame(source,canvas){
  const w=source.videoWidth||source.naturalWidth,h=source.videoHeight||source.naturalHeight;
  const size=Math.min(w,h);
  if(!size)throw Error("无法读取画面");
  if(canvas.width!==256)canvas.width=256;
  if(canvas.height!==256)canvas.height=256;
  canvas.getContext("2d").drawImage(source,(w-size)/2,(h-size)/2,size,size,0,0,256,256);
}

function chooseHands(candidates,labels,body,last){
  if(!candidates.length)return [-1,-1];
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  const cost=candidates.map((v,k)=>[0,1].map(side=>{
    const tag=labels[k]?.[0],given=body[5+side],matches=side===0?"Left":"Right";
    return (tag?.categoryName!==matches? .10*(tag?.score||0):0)
      +(given[3]>.32?dist(v[0],given):0)+(last[side]? .65*dist(v[0],last[side]):0);
  }));
  if(candidates.length===1)return cost[0][0]<=cost[0][1]?[0,-1]:[-1,0];
  return cost[0][0]+cost[1][1]<=cost[1][0]+cost[0][1]?[0,1]:[1,0];
}

export async function readLandmarks(frames,onFrame){
  if(frames.length!==12)throw Error("需要 12 帧动作");
  const {hand,pose}=await prepareVision();
  const poseRows=frames.map(()=>Array(36).fill(0)),valid=frames.map(()=>false);
  for(const i of POSE_FRAMES){
    const value=pose.detect(frames[i]).landmarks[0];
    if(value){
      valid[i]=true;
      poseRows[i]=POSE_IDS.flatMap(j=>[value[j].x,value[j].y,value[j].z,value[j].visibility||0]);
    }
    await new Promise(r=>setTimeout(r,0));
  }
  const output=filled(poseRows,valid,Array(36).fill(0));
  const points=output.map(row=>Array.from({length:9},(_,i)=>row.slice(i*4,i*4+4)));
  const poseMask=points.map(row=>row[1][3]>.30&&row[2][3]>.30);
  let last=[null,null], hands=[],mask=[];
  for(let i=0;i<frames.length;i++){
    const value=hand.detect(frames[i]);
    const candidates=value.landmarks.map(view=>view.map(p=>[p.x,p.y,p.z]));
    const choices=chooseHands(candidates,value.handedness||value.handednesses||[],points[i],last);
    const selected=choices.map((j,side)=>{
      if(j<0)return blank(21,3);
      last[side]=candidates[j][0];
      return candidates[j];
    });
    hands.push(selected);mask.push(choices.map(j=>j>=0));
    onFrame?.(i,selected,points[i],mask[i]);
    await new Promise(r=>setTimeout(r,0));
  }
  if(mask.filter(v=>v[0]||v[1]).length<3)throw Error("检测到的手部画面太少，请让双手和肩部都进入画面。");
  return {hands,pose:points,hand_mask:mask,pose_mask:poseMask};
}
