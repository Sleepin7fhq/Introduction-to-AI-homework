import json

import streamlit as st
import torch

from inspection import ROOT, COLORS, LABELS, Detector, inspect_batch, summary, export_csv, export_html

st.set_page_config(page_title="微瑕必究 · PCB 图块质检", layout="wide")
st.markdown("""<style>.stApp{background:#f6f8f7;color:#152d32} [data-testid="stMetric"]{background:white;padding:1rem;border:1px solid #dce6e2;border-radius:.55rem}
h1,h2,h3{color:#153c40} .stButton>button[kind="primary"]{background:#00685b;border-color:#00685b}
[data-testid="stSidebar"]{background:#e9efed}</style>""",unsafe_allow_html=True)
st.title("微瑕必究")
st.write("PCB 图块质检工作台")
release = json.loads((ROOT/"model"/"release.json").read_text(encoding="utf8"))
with st.sidebar:
    st.header("检测设置")
    source = st.radio("图像来源", ["上传图片","演示批次"])
    device = st.selectbox("推理设备", (["GPU","CPU"] if torch.cuda.is_available() else ["CPU"]))
    threshold = st.slider("置信度阈值",min_value=0.01,max_value=0.99,value=release["threshold"],step=0.01)
    st.caption(f'部署模型　{release["variant"]}　·　输入 640 × 640')
    st.caption("图例编号")
    for i,name in enumerate(LABELS):
        st.markdown(f'<span style="color:{COLORS[i]};font-size:1.4em">●</span>　{i+1}　{name}',unsafe_allow_html=True)

@st.cache_resource
def detector(path, backend):
    return Detector(path,backend)

if source == "上传图片":
    uploaded = st.file_uploader("选择待检图块", type=["jpg","jpeg","png"], accept_multiple_files=True)
    files = [(item.name,item.getvalue()) for item in uploaded]
else:
    files = [(p.name,p.read_bytes()) for p in sorted((ROOT/"demo").glob("*.jpg"))]
    st.caption(f"已载入 {len(files)} 张 DeepPCB 演示图块，包含待检图与清洁模板。")
if st.button("开始检测", type="primary", disabled=not files):
    bar = st.progress(0.0, text="正在检测图块")
    model = detector(str(ROOT/"model"/"pcb.pt"), 0 if device=="GPU" else "cpu")
    st.session_state["batch"] = inspect_batch(files, model, threshold, bar.progress)
    bar.empty()
if "batch" not in st.session_state:
    st.info("选择图片或演示批次后，点击“开始检测”。")
    st.stop()
batch = st.session_state["batch"]
s = summary(batch)
st.header("检测结果")
st.caption(f'批次 {batch["id"]}　·　{batch["date"]}　·　{batch["version"]}　·　阈值 {batch["conf"]:.2f}')
for col,(label,value) in zip(st.columns(4),[("成功检测",f'{s["valid"]} / {s["total"]}'),("待复检图块",s["review"]),
        ("缺陷实例",sum(s["counts"])),("图块模拟合格率",f'{s["rate"]:.1%}' if s["rate"] is not None else "无有效结果")]):
    col.metric(label,value)
st.caption(f'未检出缺陷 {s["clear"]} 张，处理失败 {s["failed"]} 张。模拟合格率以成功检测的图块为分母。')
detail,overview = st.tabs(["逐图复核","批次明细"])
with detail:
    idx = st.selectbox("选择图块",range(len(batch["rows"])),format_func=lambda i: f'{i+1} · {batch["rows"][i]["name"]} · {batch["rows"][i]["status"]}',key="pick_"+batch["id"])
    row = batch["rows"][idx]
    left,right = st.columns([1.2,1])
    if row["preview"]:
        display = left.radio("显示图像", ["定位结果", "原图"], horizontal=True)
        left.image(row["preview"] if display == "定位结果" else row["original"],caption=row["name"])
        right.write(row["status"])
        if row["boxes"]:
            right.dataframe([{"类别":LABELS[b["class"]],"置信度":round(b["score"],3),"原图坐标":str(b["xyxy"])} for b in row["boxes"]],hide_index=True)
    else:
        st.error(row["error"])
with overview:
    st.bar_chart(dict(类别=LABELS, 实例数=s["counts"]), x="类别", y="实例数", color="#137365")
    st.dataframe([dict(zip(LABELS,s["counts"]))],hide_index=True)
    st.dataframe([{"序号":r["id"],"文件":r["name"],"状态":r["status"],"缺陷数":len(r["boxes"])} for r in batch["rows"]],hide_index=True)
a,b = st.columns(2)
a.download_button("下载检测报告 · HTML",export_html(batch),f'PCB-{batch["id"]}.html',"text/html")
b.download_button("下载明细 · CSV",export_csv(batch),f'PCB-{batch["id"]}.csv',"text/csv")

