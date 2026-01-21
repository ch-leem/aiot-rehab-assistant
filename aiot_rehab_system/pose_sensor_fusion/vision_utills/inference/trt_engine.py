from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
import tensorrt as trt

from pose_sensor_fusion.vision_utills.inference.cuda_runtime import (
    cudaMalloc, cudaFree,
    cudaStreamCreate, cudaStreamDestroy,
    cudaMemcpyAsync, cudaStreamSynchronize,
    cudaMemcpyHostToDevice, cudaMemcpyDeviceToHost,
)


# =========================
# TRT wrapperclear
# =========================

TRT_LOGGER = trt.Logger(trt.Logger.INFO)

@dataclass
class TrtIO:
    input_name: str
    output_name: str
    input_shape: Tuple[int, int, int, int]   # NCHW
    output_shape: Tuple[int, int, int]       # (1,56,8400)
    input_dtype: np.dtype
    output_dtype: np.dtype

class TrtEngine:
    def __init__(self, engine_path: str):
        with open(engine_path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        if self.engine is None:
            raise RuntimeError("Failed to deserialize engine")

        self.context = self.engine.create_execution_context()
        if self.context is None:
            raise RuntimeError("Failed to create execution context")

        # assume fixed: input 1x3x640x640, output 1x56x8400
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

        in_shape = tuple(self.engine.get_tensor_shape(self.input_name))
        out_shape = tuple(self.engine.get_tensor_shape(self.output_name))

        self.input_shape = (in_shape[0], in_shape[1], in_shape[2], in_shape[3])
        self.output_shape = (out_shape[0], out_shape[1], out_shape[2])

        in_dtype = trt.nptype(self.engine.get_tensor_dtype(self.input_name))
        out_dtype = trt.nptype(self.engine.get_tensor_dtype(self.output_name))

        self.io = TrtIO(
            input_name=self.input_name,
            output_name=self.output_name,
            input_shape=self.input_shape,
            output_shape=self.output_shape,
            input_dtype=in_dtype,
            output_dtype=out_dtype,
        )

        self.stream = cudaStreamCreate()

        self.in_bytes = int(np.prod(self.input_shape) * np.dtype(self.io.input_dtype).itemsize)
        self.out_bytes = int(np.prod(self.output_shape) * np.dtype(self.io.output_dtype).itemsize)

        self.d_input = cudaMalloc(self.in_bytes)
        self.d_output = cudaMalloc(self.out_bytes)

        self.h_input = np.empty(self.input_shape, dtype=self.io.input_dtype)
        self.h_output = np.empty(self.output_shape, dtype=self.io.output_dtype)

        self.context.set_tensor_address(self.input_name, self.d_input)
        self.context.set_tensor_address(self.output_name, self.d_output)

    def infer(self, input_nchw: np.ndarray) -> np.ndarray:
        assert input_nchw.shape == self.input_shape, (input_nchw.shape, self.input_shape)
        if input_nchw.dtype != self.io.input_dtype:
            input_nchw = input_nchw.astype(self.io.input_dtype, copy=False)

        np.copyto(self.h_input, input_nchw)

        cudaMemcpyAsync(self.d_input, self.h_input.ctypes.data, self.in_bytes, cudaMemcpyHostToDevice, self.stream)

        ok = self.context.execute_async_v3(int(self.stream))
        if not ok:
            raise RuntimeError("execute_async_v3 failed")

        cudaMemcpyAsync(self.h_output.ctypes.data, self.d_output, self.out_bytes, cudaMemcpyDeviceToHost, self.stream)
        cudaStreamSynchronize(self.stream)

        return self.h_output.copy()

    def close(self):
        try:
            cudaFree(self.d_input)
            cudaFree(self.d_output)
        finally:
            cudaStreamDestroy(self.stream)
