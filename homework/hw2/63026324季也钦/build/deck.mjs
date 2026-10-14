import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import sharp from 'sharp';
import {finalizePresentation} from '/root/.codex/skills/builtins/presentations/container_tools/artifact_tool_utils.mjs';
const root='/workspace/scratch/bfdf484048d6',bd=path.join(root,'build');
const specs=JSON.parse(await fs.readFile(path.join(bd,'slides.json'),'utf8'));
const results=JSON.parse(await fs.readFile(path.join(bd,'results.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={navy:'#173453',ink:'#24374B',teal:'#008B8B',pale:'#E8F3F3',muted:'#687C90',orange:'#DE8634',gray:'#DCE4EB'};
const font='Noto Sans CJK SC';
function box(s,x,y,w,h,fill='none',line='none',sw=0,geom='rect') {return s.shapes.add({geometry:geom,position:{left:x,top:y,width:w,height:h},fill,line:{style:'solid',fill:line,width:sw}})}
function text(s,str,x,y,w,h,size=26,color=C.ink,bold=false){let sh=box(s,x,y,w,h);sh.text=str;sh.text.style={fontSize:size,typeface:font,color,bold,insets:0,autoFit:'none',wrap:'square'};return sh;}
function line(s,pts,color=C.teal,sw=3){const minx=Math.min(...pts.map(v=>v[0])),miny=Math.min(...pts.map(v=>v[1]));const w=Math.max(1,Math.max(...pts.map(v=>v[0]))-minx),h=Math.max(1,Math.max(...pts.map(v=>v[1]))-miny);return s.shapes.add({geometry:'custom',position:{left:minx,top:miny,width:w,height:h},fill:'none',line:{style:'solid',fill:color,width:sw},customPaths:[{width:w,height:h,commands:pts.map((v,i)=>({[i?'lineTo':'moveTo']:{x:v[0]-minx,y:v[1]-miny}}))}]});}
function arrow(s,x,y,xx,yy,color=C.navy,sw=3){line(s,[[x,y],[xx,yy]],color,sw);const dx=xx-x,dy=yy-y,l=Math.hypot(dx,dy),ux=dx/l,uy=dy/l;line(s,[[xx-ux*13+uy*6,yy-uy*13-ux*6],[xx,yy],[xx-ux*13-uy*6,yy-uy*13+ux*6]],color,sw);}
async function image(s,name,x,y,w,h,contain=true){const bytes=await fs.readFile(path.join(bd,'assets',name));const m=await sharp(bytes).metadata();let ww=w,hh=h;if(contain){const scale=Math.min(w/m.width,h/m.height);ww=m.width*scale;hh=m.height*scale;}s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',alt:name,fit:'contain',position:{left:x,top:y+(h-hh)/2,width:ww,height:hh}});}
async function formula(s,i,j,y,w=1136,x=72,h=65){await image(s,`eq_${i+1}_${j+1}.png`,x,y,w,h);}
function bullets(s,arr,x,y,w,size=25,gap=55){arr.forEach((v,j)=>{box(s,x,y+gap*j+11,5,18,C.teal);text(s,v,x+20,y+gap*j,w-20,gap-5,size);});}
function table(s,values,y=198,h=410){let t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top:y,width:1136,height:h,columnTracks:values[0].map((v,j)=>({mode:'fr',value:values[0].length===2?(j?2.6:1):1})) ,values});t.borders.assign({style:'solid',fill:C.gray,width:1});for(let i=0;i<values.length;i++)for(let j=0;j<values[0].length;j++){let cell=t.getCell(i,j);cell.fill=i===0?C.navy:(i%2?'#FFFFFF':'#F4F7FA');cell.text.style={fontSize:values.length>7?22:24,typeface:font,color:i===0?'#FFFFFF':C.ink,bold:i===0,insets:12};}return t;}
function schematic(s,cover=false){let x=cover?655:160,y=cover?280:250,wid=cover?530:780,ht=cover?250:280;const a=results.a_m,x0=results.x0_m,c=results.c_m;const map=(xx,yy)=>[x+wid*xx/10,y+ht*(2.5-yy)/5];let pts=[];for(let k=0;k<=100;k++){let xx=k/10,yy=a*Math.cosh((xx-x0)/a)+c;pts.push(map(xx,yy));}line(s,pts,C.teal,cover?5:5);const A=map(0,0),B=map(10,2),bot=map(x0,a+c);[A,B].forEach(v=>box(s,v[0]-8,v[1]-8,16,16,C.navy,'none',0,'ellipse'));if(!cover){line(s,[A,B],C.gray,2);text(s,'A(x₁,y₁)',A[0]-85,A[1]+20,185,40,25);text(s,'B(x₂,y₂)',B[0]-115,B[1]-52,200,40,25);arrow(s,A[0],A[1],A[0]-90,A[1]-90);text(s,'−Q(0)',A[0]-135,A[1]-137,120,40,24);arrow(s,B[0],B[1],B[0]+65,B[1]-75);text(s,'Q(L)',B[0]+78,B[1]-75,110,40,24);arrow(s,bot[0],bot[1],bot[0],bot[1]+72,C.orange);text(s,'重力向下',bot[0]+22,bot[1]+37,160,38,24,C.orange);arrow(s,1020,560,1150,560,C.muted,2);arrow(s,1020,560,1020,440,C.muted,2);text(s,'x',1154,543,50,40,24);text(s,'y',1008,406,50,40,24);text(s,'固定端点，固定长度 L，均匀线密度 ρ',220,626,780,40,26,C.muted);} }
for(let i=0;i<specs.length;i++){
 const a=specs[i],s=p.slides.add();s.background.fill='#FFFFFF';
 if(a.kind==='cover') {box(s,0,0,1280,720,'#F5F8FB');box(s,72,130,7,92,C.teal);text(s,'悬链线',100,140,500,100,64,C.navy,true);text(s,'从约束能量到静力学平衡',100,251,520,105,37,C.navy);text(s,'解析推导、全局最小性\n与数值验证',100,390,490,100,28,C.muted);schematic(s,true);text(s,'数学物理研究',100,615,450,50,24,C.teal,true);text(s,'2026.10',1030,622,170,40,22,C.muted); }
 else {text(s,a.title,72,46,1136,58,38,C.navy,true);text(s,a.lead,72,121,1136,55,23,C.muted);box(s,72,183,1136,2,C.gray);text(s,String(i+1).padStart(2,'0'),1172,674,45,25,16,C.muted);
 if(a.kind==='flow') {
 const labels=['物理模型','能量与长度','约束变分','解析曲线'];const shapes=labels.map((v,k)=>{let sh=box(s,72+k*287,247,235,87,k===0?C.navy:C.pale);text(s,v,85+k*287,270,208,45,28,k===0?'#FFFFFF':C.navy,true);return sh;});for(let k=0;k<3;k++)arrow(s,310+k*287,291,350+k*287,291,C.teal);
 const sub=['受力平衡独立验证','全局最小性证明','数值实验与误差'];sub.forEach((v,k)=>{box(s,72+k*383,458,337,95,'#F4F7FA');text(s,v,92+k*383,485,300,50,25,C.navy,true);});arrow(s,1050,338,1050,425,C.teal);line(s,[[1050,425],[240,425]],C.teal,2);[240,615,1000].forEach(x=>arrow(s,x,425,x,452,C.teal,2));text(s,'必要条件与充分条件分别检验，计算结果由实际程序生成',72,598,1136,45,26,C.muted);
 } else if(a.kind==='schematic'){schematic(s);}
 else if(a.kind==='force') {let pts=[[900,399],[983,370],[1062,325]];line(s,pts,C.teal,6);arrow(s,900,399,830,429,C.navy);arrow(s,1062,325,1136,280,C.navy);arrow(s,982,366,982,486,C.orange);text(s,'−Q(s)',790,440,145,40,23);text(s,'Q(s+ds)',1044,231,164,40,23);text(s,'w ds',1000,455,130,40,23,C.orange);for(let j=0;j<a.eqs.length;j++)await formula(s,i,j,225+j*111,700,72,80);text(s,'两端张力与微元重力平衡',800,562,408,70,24,C.muted);}
 else if(a.chart){await image(s,a.chart+'.png',62,209,855,423);bullets(s,a.texts,950,235,266,24,89);}
 else if(a.table){table(s,a.table,205,a.texts.length?295:414);if(a.texts.length)bullets(s,a.texts,72,547,1136,24,55);}
 else {const n=a.eqs.length;let y=211;for(let j=0;j<n;j++){await formula(s,i,j,y,1136,72,n>=3?65:78);y+=n>=3?82:100;}if(a.texts.length){const by=n?y+10:225;bullets(s,a.texts,72,by,1136,a.texts.length>3?25:26,n?54:(a.texts.length>3?92:58));} }
 }
 s.speakerNotes.text=a.notes+'\n\n公式 LaTeX 源：\n'+a.eqs.join('\n')+'\n\n所有数值来源：本项目 research.py 的实际运行结果，见 results.json。';
}
await fs.mkdir(path.join(bd,'previews'),{recursive:true});
const candidate=path.join(bd,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);console.log('candidate exported',specs.length);
const res=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(root,'output','悬链线数学物理研究_最终版.pptx'),pythonExecutable:process.env.CODEX_PRIMARY_RUNTIME_PYTHON,integrityValidatorPath:'/root/.codex/skills/builtins/presentations/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:'/root/.codex/skills/builtins/presentations/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],fontPolicy:{basis:'design',families:[font]},requiredNativeTableOwnerSlides:[],verifyArtifactToolImport:true,receiptPath:path.join(bd,'validation-final.json')});console.log('finalized',JSON.stringify(res));
for(let i=0;i<p.slides.items.length;i++){let png=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(bd,'previews',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));console.log('rendered',i+1);}
