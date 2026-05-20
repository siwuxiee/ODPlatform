#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集划分器 (Splitter)
"""
from __future__ import annotations
import random
from typing import List, Tuple
from .manifest import DatasetManifest, Pair

RATE_EPSILON = 1e-9

def split_pairs(
    manifest: DatasetManifest,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42,
    strict: bool = True,
) -> Tuple[List[Pair], List[Pair], List[Pair]]:
    """
    将 manifest.pairs 按比例划分为 train/val/test 三个子集。

    边界检查：
    1. 各比例必须在 [0,1] 内
    2. 比例之和若 strict=True 则必须 ≈1.0（允许 RATE_EPSILON 误差）
    3. manifest 不能为空
    4. 样本数必须 ≥ 正比例对应的集合数（保证每个集合至少一个样本）
    5. 划分后某个集合为空但比例 >0 则报错
    """
    pairs = list(manifest.pairs)
    n = len(pairs)

    # 检查 1：比例范围
    for ratio, name in zip((train_ratio, val_ratio, test_ratio), ("train", "val", "test")):
        if not (0.0 <= ratio <= 1.0):
            raise ValueError(f"{name}_ratio must be in [0,1], got {ratio}")

    # 检查 2：比例之和
    total = train_ratio + val_ratio + test_ratio
    if strict and abs(total - 1.0) > RATE_EPSILON:
        raise ValueError(f"Ratios sum to {total}, expected 1.0 (±{RATE_EPSILON})")

    # 检查 3：非空
    if n == 0:
        raise ValueError("Cannot split empty manifest")

    # 检查 4：样本数是否足够覆盖至少各一个的正比例集合
    required = 0
    if train_ratio > 0: required += 1
    if val_ratio > 0: required += 1
    if test_ratio > 0: required += 1
    if n < required:
        raise ValueError(
            f"Need at least {required} pairs to split with given non-zero ratios, "
            f"but only {n} available"
        )

    # 计算各集合数量（四舍五入，最后调整使总和 = n）
    n_train = max(0, round(n * train_ratio))
    n_val = max(0, round(n * val_ratio))
    n_test = n - n_train - n_val

    # 由于四舍五入可能导致总和不为 n，进行微调
    diff = n - (n_train + n_val + n_test)
    if diff != 0:
        if diff > 0:
            n_test += diff
        else:  # diff < 0，过多，从 val 中减去
            n_val += diff  # diff 为负

    # 确保非负
    n_train = max(0, n_train)
    n_val = max(0, n_val)
    n_test = max(0, n_test)

    # 检查 5：比例 >0 时集合不能为空
    if train_ratio > 0 and n_train == 0:
        raise ValueError(f"train set would be empty with ratio {train_ratio} and {n} samples")
    if val_ratio > 0 and n_val == 0:
        raise ValueError(f"val set would be empty with ratio {val_ratio} and {n} samples")
    if test_ratio > 0 and n_test == 0:
        raise ValueError(f"test set would be empty with ratio {test_ratio} and {n} samples")

    # 随机打乱并切片
    rng = random.Random(random_state)
    shuffled = list(pairs)
    rng.shuffle(shuffled)

    train = shuffled[:n_train]
    val = shuffled[n_train:n_train + n_val]
    test = shuffled[n_train + n_val:]

    return train, val, test