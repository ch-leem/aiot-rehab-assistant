
```bash
create_onnx.py
```

```bash
/usr/src/tensorrt/bin/trtexec \
  --onnx=yolo11n-pose.onnx \
  --saveEngine=yolo11n-pose_fp16.engine \
  --fp16 \
  --memPoolSize=workspace:2048M \
  --skipInference
```
