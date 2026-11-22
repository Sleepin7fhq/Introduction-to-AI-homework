const TIPS=[4,8,12,16,20];
const PARENTS=[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19];
const norm=(a,b)=>Math.hypot(a,b);

export function mixAt(t,length,callback){
  const low=Math.max(0,Math.min(length-1,Math.floor(t)));
  const high=Math.min(length-1,low+1);
  const left=callback(low);
  return high===low?left:left+(t-low)*(callback(high)-left);
}

export function filled(data, mask, fallback){
  const observed=[];
  for(let i=0;i<mask.length;i++)if(mask[i])observed.push(i);
  if(!observed.length)return data.map((row,i)=>Array.isArray(fallback[0])?fallback[i].slice():fallback.slice());
  let after=0;
  return data.map((_,i)=>{
    while(after<observed.length-1&&observed[after]<i)after++;
    const lo=observed[Math.max(0,after-1)];
    const hi=observed[after];
    const ratio=hi===lo?0:Math.max(0,Math.min(1,(i-lo)/(hi-lo)));
    return data[lo].map((v,j)=>Math.fround(v+(data[hi][j]-v)*ratio));
  });
}

function temporal(a){
  const n=a.length,w=a[0].length,out=[];
  for(let frame=0;frame<8;frame++)
    for(let j=0;j<w;j++)out.push(Math.fround(.75*mixAt(frame*(n-1)/7,n,i=>a[i][j])));
  for(let seg=0;seg<3;seg++){
    const start=seg*Math.floor(n/3)+Math.min(seg,n%3);
    const end=(seg+1)*Math.floor(n/3)+Math.min(seg+1,n%3);
    for(let j=0;j<w;j++){
      let total=0;
      for(let i=start;i<end;i++)total+=a[i][j];
      out.push(total/(end-start));
    }
  }
  const means=[],sd=[],ranges=[];
  for(let j=0;j<w;j++){
    let sum=0,low=Infinity,high=-Infinity;
    for(let i=0;i<n;i++){const v=a[i][j];sum+=v;low=Math.min(low,v);high=Math.max(high,v);}
    const mean=sum/n;
    let variance=0;
    for(let i=0;i<n;i++)variance+=(a[i][j]-mean)**2;
    means.push(mean);sd.push(Math.sqrt(variance/n));ranges.push(high-low);
  }
  return Float32Array.from([...out,...means,...sd,...ranges]);
}

function quantile(input,p){
  return mixAt((input.length-1)*p,input.length,i=>input[i]);
}

export function makeFeatures(data){
  const {hands,pose,hand_mask:seen,pose_mask:poseHint}=data;
  const length=hands.length;
  const poseRows=filled(pose.map(v=>v.flat()),poseHint,Array(36).fill(0));
  const center=filled(poseRows.map(v=>[(v[4]+v[8])/2,(v[5]+v[9])/2]),poseHint,[.5,.37]);
  const width=filled(poseRows.map(v=>[norm(v[4]-v[8],v[5]-v[9])]),poseHint,[.35]).map(v=>Math.max(v[0],.12));
  const hasPose=poseHint.some(Boolean);
  const poseXY=poseRows.map((row,i)=>Array.from({length:9},(_,k)=>hasPose?
    [(row[4*k]-center[i][0])/width[i],(row[4*k+1]-center[i][1])/width[i]]:[0,0]));
  const local=[],present=[],wrists=[],palms=[];
  for(let side=0;side<2;side++){
    const found=seen.map(v=>Boolean(v[side]));
    const flat=filled(hands.map(v=>v[side].flat()),found,Array(63).fill(0));
    const relative=flat.map(p=>Array.from({length:21},(_,j)=>[p[3*j]-p[0],p[3*j+1]-p[1],p[3*j+2]-p[2]]));
    const scale=Math.max(.025,quantile(relative.map(p=>norm(p[9][0],p[9][1])).sort((a,b)=>a-b),.65));
    const facing=[];
    local.push(relative.map(points=>{
      const p=points.map(row=>row.map(x=>x/scale));
      const [px,py]=p[9],q=Math.max(.08,norm(px,py)),ux=px/q,uy=py/q;
      facing.push([ux,uy]);
      const front=p.slice(1).flatMap(v=>[v[0],v[1]]);
      const canonical=p.flatMap(([x,y])=>[(x*uy-y*ux)*.45,(x*ux+y*uy)*.45]);
      const bones=PARENTS.flatMap((parent,j)=>{
        const v=p[j+1].map((x,axis)=>x-p[parent][axis]),q=Math.max(.07,Math.hypot(...v));
        return [.60*v[0]/q,.60*v[1]/q];
      });
      const radii=[];
      for(let j=0;j<21;j++)for(let k=j+1;k<21;k++)radii.push(.45*norm(p[j][0]-p[k][0],p[j][1]-p[k][1]));
      return [...front,...canonical,...bones,...radii,...TIPS.map(i=>.32*p[i][2])];
    }));
    palms.push(facing);
    const nr=5+side;
    const known=pose.map((v,i)=>Boolean(poseHint[i]&&v[nr][3]>.28));
    const fallback=filled(pose.map(v=>v[nr].slice(0,2)),known,center);
    const choice=hands.map((v,i)=>found[i]?v[side][0].slice(0,2):fallback[i]);
    const valid=found.map((x,i)=>x||known[i]);
    const wrist=filled(choice,valid,center).map((v,i)=>v.map((x,j)=>(x-center[i][j])/width[i]));
    wrists.push(wrist);
    present.push(found.reduce((s,x)=>s+Number(x),0)/length);
  }
  const activity=(rows)=>rows[0].reduce((total,_,axis)=>{
    const mu=rows.reduce((s,v)=>s+v[axis],0)/length;
    return total+Math.sqrt(rows.reduce((s,v)=>s+(v[axis]-mu)**2,0)/length);
  },0);
  const dominant=present[0]+.10*activity(wrists[0])>=present[1]+.10*activity(wrists[1])?0:1;
  const position=wrists[0].map(([x,y],i)=>[x,y,...wrists[1][i],x-wrists[1][i][0],y-wrists[1][i][1],...poseXY[i][0]]);
  const movement=position.slice(1).map((v,i)=>v.map((u,k)=>u-position[i][k])).map(v=>[...v,...v.map(Math.abs)]);
  const arms=poseXY.map((v,i)=>[...v.slice(3,7).flat(),...palms[0][i],...palms[1][i]]);
  return [temporal(local[dominant]),temporal(local[0].map((v,i)=>[...v,...local[1][i]])),
    temporal(position),Float32Array.from([...temporal(movement),...temporal(arms)]),
    Float32Array.of(...present,seen.filter(v=>v[0]&&v[1]).length/length,poseHint.filter(Boolean).length/length)];
}

function decodeFloat16(){
  const lookup=new Float32Array(65536);
  for(let u=0;u<lookup.length;u++){
    const sign=u&0x8000?-1:1,exponent=(u>>10)&31,mantissa=u&1023;
    lookup[u]=sign*(exponent===0?mantissa*2**-24:exponent===31?Infinity:(1+mantissa/1024)*2**(exponent-15));
  }
  return lookup;
}

export function unpack(meta,buffer){
  let pointer=0;
  const lookup=meta.encoding.startsWith("f16")?decodeFloat16():null;
  const parts=meta.parts.map(part=>{
    const count=part.width*meta.n;
    const ref=new Float32Array(count),square=new Float32Array(meta.n);
    if(lookup){
      pointer+=(-pointer)&1;
      if(meta.encoding==="f16-shuffled"){
        const packed=new Uint8Array(buffer,pointer,2*count);
        for(let i=0;i<count;i++)ref[i]=lookup[packed[i]|packed[i+count]<<8];
      }else{
        const packed=new Uint16Array(buffer,pointer,count);
        for(let i=0;i<count;i++)ref[i]=lookup[packed[i]];
      }
      pointer+=count*2;
    }else{
      const levels=new DataView(buffer,pointer,4*part.width);
      const scales=Float32Array.from({length:part.width},(_,i)=>levels.getFloat32(4*i,true));
      pointer+=4*part.width;
      const packed=new Int8Array(buffer,pointer,count);
      for(let i=0;i<count;i++)ref[i]=packed[i]*scales[i%part.width];
      pointer+=count;
    }
    for(let i=0;i<meta.n;i++){
      let sum=0,offset=i*part.width;
      for(let j=0;j<part.width;j++)sum+=ref[offset+j]**2;
      square[i]=sum;
    }
    return {...part,ref,square};
  });
  pointer+=(-pointer)&3;
  const coefficient=new Float32Array(buffer,pointer,meta.n*meta.classes);
  if(pointer+coefficient.byteLength!==buffer.byteLength)throw Error("模型数据长度不匹配");
  return {...meta,parts,coefficient};
}

export function calculate(vectors,model){
  const distances=new Float32Array(model.n);
  model.parts.forEach((part,i)=>{
    const data=vectors[i];
    if(data.length!==part.width)throw Error("骨架特征长度不匹配");
    const v=Float32Array.from(data,x=>x/part.scale);
    let querySquared=0;
    for(let j=0;j<v.length;j++)querySquared+=v[j]**2;
    for(let n=0;n<model.n;n++){
      let dot=0,start=n*part.width;
      for(let j=0;j<part.width;j++)dot+=v[j]*part.ref[start+j];
      distances[n]+=part.weight*Math.max(0,querySquared+part.square[n]-2*dot)/part.median;
    }
  });
  const values=new Float64Array(model.classes);
  for(let i=0;i<model.n;i++){
    const d=distances[i],kernel=.55*Math.exp(-.55*d)+.45*Math.exp(-1.65*d),offset=i*model.classes;
    for(let k=0;k<model.classes;k++)values[k]+=model.coefficient[offset+k]*kernel;
  }
  return values;
}

export function ranking(values,n=5){
  return Array.from(values,(_,label)=>label).sort((a,b)=>values[b]-values[a]||a-b).slice(0,n);
}
