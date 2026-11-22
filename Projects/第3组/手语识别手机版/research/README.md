# 训练与复核

原始数据为 [NationalCSL-DP](https://doi.org/10.6084/m9.figshare.27261843.v3)。在此目录运行，指定从 Figshare 下载的 ZIP。依次筛选 203 词的正面抽帧，提取骨架，复算训练口径。

    python -m pip install numpy pillow mediapipe==0.10.35
    python extract_target_frames.py 27261843.zip label_map.json selected-frames
    python extract_dual_landmarks.py --images selected-frames --hand-model ../assets/vision/hand_landmarker.task --pose-model ../assets/vision/pose_landmarker_lite.task --out landmarks
    python train_real_frames.py --landmarks landmarks --manifest selected-frames/manifest.csv --out base-run
    python tune_dual_alignment.py --landmarks landmarks --manifest selected-frames/manifest.csv --out tuned-experiment

发布模型分片见上一层 assets。metrics.json 记录基础双手实验。release_metrics.json 记录最终正则化与时间对齐实验。网页用同一模型系数，并以无损字节排列压缩半精度参考特征。
