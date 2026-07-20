---
name: compare-sequences
description: 三序列比对与突变分析 — 基于编号序列坐标系统比较参比与目标序列的同一性和突变位点
trigger: /compare-sequences
---

# /compare-sequences

基于 EMBOSS needle 全局比对算法，以**编号序列**为坐标系统，比较参比序列与目标序列的同一性（Longest_Identity）和突变位点。

运行此命令需在 `sayhello` 项目目录下，确保 venv 激活且 EMBOSS needle 可用。

## Usage

```
/compare-sequences <ref_seq> <num_seq> <tgt_seq>                       单序列比对
/compare-sequences batch <excel_path>                                  Excel批量比对
/compare-sequences batch <excel_path> --open                           Excel批量比对 + 浏览器打开结果
```

## 参数

| 参数 | 说明 |
|------|------|
| `<ref_seq>` | 参比序列（氨基酸或核酸字符串） |
| `<num_seq>` | 编号序列（提供坐标系统） |
| `<tgt_seq>` | 目标序列 |
| `<excel_path>` | 批量模式 Excel 文件路径 |

可选参数（通过 `--gapopen N --gapextend N` 指定，默认值：gapopen=10.0, gapextend=0.5）

## 单序列模式

### 流程

1. needle 比对 参比序列 vs 编号序列
2. needle 比对 目标序列 vs 编号序列
3. needle 比对 参比序列 vs 目标序列（获取 ref-tgt 最长同一性）
4. 以编号序列为锚点，逐位比较参比与目标，发现突变位点
5. 返回：同一性、最长一致性、突变位点列表、三序列分块比对可视化

### 调用示例

```python
from compare_utils import compare_sequences

result = compare_sequences(
    ref_seq="MVLSPADKTNVKAAWGKVGAHAGEYGAEALERM",
    num_seq="MVLSPADKTNVKAAWGKVGAHAGEYGAEALERM",
    tgt_seq="MGLSPADKTNVKAAWGKVGAHAGEYGAEALERM",
    gapopen=10.0,
    gapextend=0.5,
)

print(f"同一性: {result['identity']:.2%}")
print(f"最长一致性: {result['longest_identity']:.2%}")
for m in result['mutations']:
    print(f"  {m['reference_residue']}{m['numbering_position']}{m['target_residue']}")
```

### 返回值

```python
{
    'identity': float,           # 参比vs目标同一性 (0~1)
    'longest_identity': float,   # needle最长一致性 (0~1)
    'matches': int,              # 匹配数
    'mismatches': int,           # 错配数
    'total_positions': int,      # 总比对位置
    'mutations': [               # 突变列表
        {'numbering_position': int, 'reference_residue': str, 'target_residue': str}
    ],
    'alignment_chunks': [...],   # 每30残基分块的比对可视化
    'ref_tgt_longest_identity': float,  # ref-vs-tgt needle Longest_Identity
}
```

## 批量模式（Excel）

### Excel 格式要求

| 列名（关键字匹配） | 说明 |
|---|---|
| 序列名称 / name / 序列名 | 可选 |
| 参比序列 / reference / ref | 必需 |
| 编号序列 / numbering / num | 必需 |
| 目标序列 / target / tgt | 必需 |

### 调用示例

```python
from compare_utils import batch_compare_from_excel

results = batch_compare_from_excel("/path/to/file.xlsx", gapopen=10.0, gapextend=0.5)
for r in results:
    print(f"{r['name']}: identity={r['identity']:.2%}")
```

### 输出

批量下载时在原 Excel 右侧追加两列：
- `序列同一性` — needle longest_identity（百分比）
- `突变位点列表` — 斜杠间隔的突变表示，如 `V2G/E31S`

## 命令行快速测试

```bash
cd /Users/zhaoyongjiang/Downloads/bioapp/sayhello
source venv/bin/activate
python3 -c "
from compare_utils import compare_sequences
r = compare_sequences('MVLSPADKTNVKAAWGKVGAHAGEYGAEALERM', 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERM', 'MGLSPADKTNVKAAWGKVGAHAGEYGAEALERM')
print(f'同一性: {r[\"identity\"]*100:.2f}%')
for m in r['mutations']:
    print(f'  突变: {m[\"reference_residue\"]}{m[\"numbering_position\"]}{m[\"target_residue\"]}')
"
```

## API 端点

如果 Flask 服务运行中，也可直接 HTTP 调用：

```bash
# 单序列分析
curl -s -X POST http://localhost:8081/compare/analyze \
  -d "ref_sequence=...&num_sequence=...&tgt_sequence=..."

# 批量上传
curl -s -F "excel_file=@/path/to/file.xlsx" http://localhost:8081/compare/batch
```
