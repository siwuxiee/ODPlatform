#!/bin/bash

# scripts/make_disaster_data.sh
# 为 D2.5 课程造灾难现场数据

echo "🎬 准备灾难现场..."

# 1. data/raw/
mkdir -p "data/raw/precious_dataset/images"
mkdir -p "data/raw/precious_dataset/labels"

for i in {1..200}; do
    echo "fake image $i" > "data/raw/precious_dataset/images/img_$i.jpg"
    echo "0 0.5 0.5 0.3 0.4" > "data/raw/precious_dataset/labels/img_$i.txt"
done
echo "  ✅ data/raw/precious_dataset/ — 400 个文件"

# 2. 2GB 稀疏文件
mkdir -p "runs/exp_2026_05_10"
# 使用 truncate 创建稀疏文件，这比直接分配空间快得多
truncate -s 2G "runs/exp_2026_05_10/best.pt"
echo "  ✅ runs/exp_2026_05_10/best.pt — 2 GB"

# 3. 5000 小文件
mkdir -p "runs/exp_2026_05_10/tb_logs"
for i in {1..5000}; do
    echo "step $i loss" > "runs/exp_2026_05_10/tb_logs/event.$i"
done
echo "  ✅ runs/exp_2026_05_10/tb_logs/ — 5000 个文件"

# 4. logging
mkdir -p "apps/platform/logging/training/2026-05-10"
for i in {1..50}; do
    echo "training run $i" > "apps/platform/logging/training/2026-05-10/run-$i.log"
done
echo "  ✅ apps/platform/logging/ — 50 份日志"

echo ""
echo "🎬 灾难现场准备就绪。"