import argparse
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export YOLOv11 Pose model to ONNX format"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to YOLO model (.pt)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Input image size"
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version"
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        help="Simplify ONNX graph"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    model = YOLO(args.model)
    model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=args.simplify
    )


if __name__ == "__main__":
    main()