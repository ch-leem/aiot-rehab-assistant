## Training Summary

- Model: YOLO11m-pose
- Keypoints: 21 (COCO 17 + Foot 4)
- Epochs: 100
- Pose mAP50: 0.988
- Pose mAP50-95: 0.872
- Inference: ~2.5ms/image (V100)

## Pipeline
1. Dataset split (labels 기준)
2. Pose training (YOLO11m)
3. Validation
4. Image / Video inference


```
# 폴더구조
workspace/
├── datasets/
│   ├── images/
│   │   ├── train/
│   │   │   └── ...
│   │   └── val/
│   │       └── ...
│   ├── input_images/
│   │   ├── 000001.jpg
│   │   └── ...
|   |
│   └── labels/
│       ├── 000001.txt
│       └── ...
│
├── yolom/
│   ├── dataset/
│   │   └── data.yaml
|   |
│   ├── models/
│   │   ├── yolo11m_pose.yaml
│   │   └── ...
|   |
│   ├── runs/
│   │   └── pose/
│   │        └── yolo11m_pose_21points/
│   │             ├── weights/
│   │             |    ├── best.pt
│   │             |    └── last.pt
│   │             ├── args.yaml
│   │             └── results ... (images & results.csv)
|   |
│   ├── scripts/
│   │   ├── ...
│   │   └── ...
|   |
│   ├── weights/
│   │   └── yolo11m-pose.pt # original model
|   |
│   ├── env/yolom_train_env.yaml
|   |
│   └── README.md
|
│
├── mmpose/
│
└── yolon/
```