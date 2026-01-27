#!/bin/bash
conda activate yolon_distil

CUDA_VISIBLE_DEVICES=8 python -m train.train