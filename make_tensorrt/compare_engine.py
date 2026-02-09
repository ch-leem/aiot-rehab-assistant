# compare_engines.py
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, Tuple, Any, List

import numpy as np
import tensorrt as trt

TRT_LOGGER = trt.Logger(trt.Logger.INFO)

@dataclass
class IOInfo:
    name: str
    mode: str           # INPUT / OUTPUT
    shape: Tuple[int, ...]
    dtype: str

@dataclass
class EngineSummary:
    path: str
    num_io_tensors: int
    io: Dict[str, IOInfo]          # key = tensor name
    input_names: List[str]
    output_names: List[str]
    # wrapper가 현재 가정하는 "0번 input, 1번 output" 매핑 결과
    idx0_name: str
    idx1_name: str
    idx0_mode: str
    idx1_mode: str

def load_engine(path: str) -> trt.ICudaEngine:
    with open(path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
        engine = runtime.deserialize_cuda_engine(f.read())
    if engine is None:
        raise RuntimeError(f"Failed to deserialize engine: {path}")
    return engine

def mode_to_str(m: trt.TensorIOMode) -> str:
    if m == trt.TensorIOMode.INPUT:
        return "INPUT"
    if m == trt.TensorIOMode.OUTPUT:
        return "OUTPUT"
    return str(m)

def inspect_engine(path: str) -> EngineSummary:
    e = load_engine(path)

    io: Dict[str, IOInfo] = {}
    input_names: List[str] = []
    output_names: List[str] = []

    for i in range(e.num_io_tensors):
        name = e.get_tensor_name(i)
        mode = mode_to_str(e.get_tensor_mode(name))
        shape = tuple(e.get_tensor_shape(name))
        dtype = str(np.dtype(trt.nptype(e.get_tensor_dtype(name))))

        io[name] = IOInfo(name=name, mode=mode, shape=shape, dtype=dtype)
        if mode == "INPUT":
            input_names.append(name)
        elif mode == "OUTPUT":
            output_names.append(name)

    # 네 wrapper의 가정(0번, 1번)
    idx0_name = e.get_tensor_name(0) if e.num_io_tensors > 0 else ""
    idx1_name = e.get_tensor_name(1) if e.num_io_tensors > 1 else ""
    idx0_mode = mode_to_str(e.get_tensor_mode(idx0_name)) if idx0_name else ""
    idx1_mode = mode_to_str(e.get_tensor_mode(idx1_name)) if idx1_name else ""

    return EngineSummary(
        path=path,
        num_io_tensors=e.num_io_tensors,
        io=io,
        input_names=input_names,
        output_names=output_names,
        idx0_name=idx0_name,
        idx1_name=idx1_name,
        idx0_mode=idx0_mode,
        idx1_mode=idx1_mode,
    )

def print_summary(s: EngineSummary) -> None:
    print(f"\n=== {s.path} ===")
    print("num_io_tensors:", s.num_io_tensors)
    print("inputs:", s.input_names)
    print("outputs:", s.output_names)
    print("wrapper_assumption idx0 ->", s.idx0_name, s.idx0_mode)
    print("wrapper_assumption idx1 ->", s.idx1_name, s.idx1_mode)
    print("\nIO details:")
    for name, info in s.io.items():
        print(f"- {name:30s} {info.mode:6s} shape={info.shape} dtype={info.dtype}")

def decide_wrapper_changes(a: EngineSummary, b: EngineSummary) -> None:
    # 1) IO 개수 동일?
    if a.num_io_tensors != 2 or b.num_io_tensors != 2:
        print("\n[판정] IO 텐서 개수가 2가 아님. wrapper 수정 필요 가능성 큼.")
        return

    # 2) 엔진당 input/output 1개씩?
    if len(a.input_names) != 1 or len(a.output_names) != 1 or len(b.input_names) != 1 or len(b.output_names) != 1:
        print("\n[판정] input/output 텐서가 1개씩이 아님. wrapper 수정 필요.")
        return

    a_in = a.io[a.input_names[0]]
    a_out = a.io[a.output_names[0]]
    b_in = b.io[b.input_names[0]]
    b_out = b.io[b.output_names[0]]

    # 3) shape 비교
    same_in_shape = a_in.shape == b_in.shape
    same_out_shape = a_out.shape == b_out.shape

    # 4) dtype 비교
    same_in_dtype = a_in.dtype == b_in.dtype
    same_out_dtype = a_out.dtype == b_out.dtype

    # 5) wrapper의 "0=input,1=output" 가정이 둘 다 맞는지
    a_order_ok = (a.idx0_mode == "INPUT" and a.idx1_mode == "OUTPUT")
    b_order_ok = (b.idx0_mode == "INPUT" and b.idx1_mode == "OUTPUT")

    print("\n=== 호환 판정 ===")
    print("입력 shape 동일:", same_in_shape, "(", a_in.shape, "vs", b_in.shape, ")")
    print("출력 shape 동일:", same_out_shape, "(", a_out.shape, "vs", b_out.shape, ")")
    print("입력 dtype 동일:", same_in_dtype, "(", a_in.dtype, "vs", b_in.dtype, ")")
    print("출력 dtype 동일:", same_out_dtype, "(", a_out.dtype, "vs", b_out.dtype, ")")
    print("wrapper index 가정 OK (A):", a_order_ok)
    print("wrapper index 가정 OK (B):", b_order_ok)

    if same_in_shape and same_out_shape and a_order_ok and b_order_ok:
        print("\n[결론] 엔진만 교체해도 wrapper 그대로 사용 가능.")
        if not (same_in_dtype and same_out_dtype):
            print("[주의] dtype이 달라서 입력 배열 dtype 캐스팅이 자주 발생할 수 있음. 그래도 동작은 함.")
    else:
        print("\n[결론] wrapper 수정 필요 가능성 있음.")
        if not (a_order_ok and b_order_ok):
            print("- 수정 1순위: get_tensor_name(0/1) 가정 제거하고 TensorIOMode로 input/output 찾기.")
        if not same_out_shape:
            print("- 출력 shape가 다르면 후처리도 같이 맞춰야 함.")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine_a", default="yolo11m-pose_fp16.engine")
    ap.add_argument("--engine_b", default="yolo11n-pose_fp16.engine")
    args = ap.parse_args()

    A = inspect_engine(args.engine_a)
    B = inspect_engine(args.engine_b)

    print_summary(A)
    print_summary(B)
    decide_wrapper_changes(A, B)

if __name__ == "__main__":
    main()
