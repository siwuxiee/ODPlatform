import tempfile, shutil, yaml
from pathlib import Path
from PIL import Image
import pytest
from odp_platform.data_pipeline import Orchestrator

@pytest.fixture
def voc_dataset():
    """构造一个最小的 VOC 数据集（3张图，3个xml）"""
    base = Path(tempfile.mkdtemp())
    ann = base / "Annotations"
    img = base / "JPEGImages"
    ann.mkdir()
    img.mkdir()

    # 创建三张图片
    for i in range(1, 4):
        Image.new("RGB", (50, 50), color="red").save(img / f"{i:03d}.jpg")

    # 创建三个标注文件（类别 cat）
    xml_content = """<annotation>
        <filename>{}.jpg</filename>
        <size><width>50</width><height>50</height><depth>3</depth></size>
        <object><name>cat</name>
            <bndbox><xmin>10</xmin><ymin>10</ymin><xmax>40</xmax><ymax>40</ymax></bndbox>
        </object>
    </annotation>"""
    for i in range(1, 4):
        (ann / f"{i:03d}.xml").write_text(xml_content.format(f"{i:03d}"))

    yield base
    shutil.rmtree(base)

@pytest.fixture
def orchestrator_kwargs(voc_dataset, tmp_path):
    """构造 Orchestrator 所需参数，比例调整为0.4/0.3/0.3，总和1.0，确保每个集合至少一个"""
    output_images = tmp_path / "converted" / "images"
    output_labels = tmp_path / "converted" / "labels"
    config_yaml = tmp_path / "output.yaml"
    return dict(
        dataset_name="test_voc",
        format_name="pascal_voc",
        raw_data_dir=voc_dataset,
        output_images_dir=output_images,
        output_labels_dir=output_labels,
        config_yaml_path=config_yaml,
        train_ratio=0.4,
        val_ratio=0.3,
        test_ratio=0.3,
        random_state=42,
    )

def test_smoke_voc_conversion(orchestrator_kwargs):
    """烟雾测试：VOC 数据集能成功运行完毕"""
    orch = Orchestrator(**orchestrator_kwargs)
    orch.run()
    yaml_path = orchestrator_kwargs["config_yaml_path"]
    assert yaml_path.exists()
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert "odp_meta" in data
    assert data["nc"] == 1
    assert data["names"] == {0: "cat"}

def test_smoke_coverage_failfast(tmp_path):
    """测试覆盖率不足时 fail-fast"""
    raw = tmp_path / "broken_voc"
    raw.mkdir()
    ann = raw / "Annotations"
    img = raw / "JPEGImages"
    ann.mkdir()
    img.mkdir()
    Image.new("RGB", (10,10)).save(img / "only.jpg")
    orch = Orchestrator(
        dataset_name="broken",
        format_name="pascal_voc",
        raw_data_dir=raw,
        output_images_dir=tmp_path / "out/images",
        output_labels_dir=tmp_path / "out/labels",
        config_yaml_path=tmp_path / "config.yaml",
    )
    with pytest.raises(ValueError, match="覆盖率"):
        orch.run()