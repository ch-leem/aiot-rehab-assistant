import ctypes

# =========================
# CUDA Runtime via ctypes (no pycuda)
# =========================
_libcudart = ctypes.CDLL("libcudart.so")

cudaSuccess = 0
cudaMemcpyHostToDevice = 1
cudaMemcpyDeviceToHost = 2

def _check_cuda(err: int, msg: str):
    if err != cudaSuccess:
        raise RuntimeError(f"CUDA error {err} at {msg}")

def cudaMalloc(nbytes: int) -> int:
    ptr = ctypes.c_void_p()
    err = _libcudart.cudaMalloc(ctypes.byref(ptr), ctypes.c_size_t(nbytes))
    _check_cuda(err, "cudaMalloc")
    return ptr.value

def cudaFree(ptr: int):
    err = _libcudart.cudaFree(ctypes.c_void_p(ptr))
    _check_cuda(err, "cudaFree")

def cudaStreamCreate() -> int:
    stream = ctypes.c_void_p()
    err = _libcudart.cudaStreamCreate(ctypes.byref(stream))
    _check_cuda(err, "cudaStreamCreate")
    return stream.value

def cudaStreamDestroy(stream: int):
    err = _libcudart.cudaStreamDestroy(ctypes.c_void_p(stream))
    _check_cuda(err, "cudaStreamDestroy")

def cudaMemcpyAsync(dst: int, src: int, nbytes: int, kind: int, stream: int):
    err = _libcudart.cudaMemcpyAsync(
        ctypes.c_void_p(dst),
        ctypes.c_void_p(src),
        ctypes.c_size_t(nbytes),
        kind,
        ctypes.c_void_p(stream)
    )
    _check_cuda(err, "cudaMemcpyAsync")

def cudaStreamSynchronize(stream: int):
    err = _libcudart.cudaStreamSynchronize(ctypes.c_void_p(stream))
    _check_cuda(err, "cudaStreamSynchronize")