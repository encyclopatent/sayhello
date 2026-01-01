# 序列比对工具算法参数文档

## 1. 概述

序列比对工具支持多种比对算法，包括全局比对、局部比对、ClustalW、Needle、MUSCLE和Water。本文档详细说明各算法使用的默认参数和配置。

## 2. 算法列表

### 2.1 全局比对 (Global Alignment)

**算法描述**：使用BioPython的PairwiseAligner进行全局序列比对，适用于完整序列的比对分析。

**默认参数**：
- 评分方法：blastp
- 比对模式：global
- 替换矩阵：BLOSUM62
- 开放缺口分数：-10
- 扩展缺口分数：-0.5

**实现函数**：`create_aligner('global')`

### 2.2 局部比对 (Local Alignment)

**算法描述**：使用BioPython的PairwiseAligner进行局部序列比对，适用于寻找序列中的相似区域。

**默认参数**：
- 评分方法：blastp
- 比对模式：local
- 替换矩阵：BLOSUM62
- 开放缺口分数：使用默认值（BioPython PairwiseAligner默认值）
- 扩展缺口分数：使用默认值（BioPython PairwiseAligner默认值）

**实现函数**：`create_aligner('local')`

### 2.3 ClustalW

**算法描述**：使用外部ClustalW工具进行多序列比对，适用于蛋白质序列比对。

**默认参数**：
- 序列类型：PROTEIN
- 替换矩阵：BLOSUM
- 开放缺口罚分：10.0
- 扩展缺口罚分：0.2
- 输出格式：FASTA
- 工具路径：`/opt/anaconda3/envs/rdkit-env/bin/clustalw2`

**命令行参数**：
```bash
clustalw2 -infile=<input_file> -outfile=<output_file> -OUTPUT=FASTA -quiet -PROFILE=clustalw.cfg
```

### 2.4 Needle

**算法描述**：使用EMBOSS Needle工具进行全局序列比对，基于Needleman-Wunsch算法。

**默认参数**：
- 开放缺口罚分：10.0
- 扩展缺口罚分：0.5
- 工具路径：`/opt/anaconda3/envs/rdkit-env/bin/_needle`

**命令行参数**：
```bash
_needle -nobrief -asequence=<target_file> -bsequence=<query_file> -gapopen=10.0 -gapextend=0.5 -outfile=needle.txt
```

### 2.5 MUSCLE

**算法描述**：使用外部MUSCLE工具进行多序列比对，适用于快速准确的序列比对。

**默认参数**：
- 工具路径：`/opt/anaconda3/envs/rdkit-env/bin/muscle`
- 命令行参数：`muscle -align <input_file> -output <output_file>`

### 2.6 Water

**算法描述**：使用EMBOSS Water工具进行局部序列比对，基于Smith-Waterman算法。

**默认参数**：
- 开放缺口罚分：10.0
- 扩展缺口罚分：0.5
- 工具路径：`/opt/anaconda3/envs/rdkit-env/bin/_water`

**命令行参数**：
```bash
_water -nobrief -asequence=<target_file> -bsequence=<query_file> -gapopen=10.0 -gapextend=0.5 -outfile=water.txt
```

## 3. 输入参数

### 3.1 序列输入

- **靶序列**：权利要求中限定的参比序列
- **查询序列**：需要进行比对分析的序列
- **输入格式**：直接输入序列字符串，程序会自动处理（去除空格，转换为大写）

### 3.2 位点输入

- **特定位点**：权利要求限定的位点，以逗号分隔的数字（如：266,389,422）
- **关键位点**：查询序列中的关键位点，以逗号分隔的数字（如：266,389,422）
- **注意**：如果不输入任何位点，则只进行序列同一性计算

### 3.3 算法选择

- **默认算法**：global（全局比对）
- **算法选择**：程序会自动使用所有算法进行比对，并在结果中显示各算法的比对结果

## 4. 环境变量

程序使用以下环境变量来配置外部工具：

```
EMBOSS_ACDROOT=/opt/anaconda3/envs/rdkit-env/share/EMBOSS/acd/
EMBOSS_DATA=/opt/anaconda3/envs/rdkit-env/share/EMBOSS/data/
PLPLOT_LIB=/opt/anaconda3/envs/rdkit-env/share/EMBOSS/
```

## 5. 结果输出

### 5.1 表格结果

比对结果以表格形式展示，包含以下列：
- 参考位点：输入的特定位点
- 全局匹配：全局比对算法的匹配结果
- 局部匹配：局部比对算法的匹配结果
- ClustalW匹配：ClustalW算法的匹配结果
- needle匹配：Needle算法的匹配结果
- MUSCLE匹配：MUSCLE算法的匹配结果
- water匹配：Water算法的匹配结果
- 关键位点：标记查询序列中的关键位点

### 5.2 同一性信息

表格最后两行显示：
- 同一性：各算法的序列同一性百分比
- needle最长一致性：Needle算法的最长一致性百分比

### 5.3 文件下载

程序支持下载以下文件：
- Excel结果：包含所有比对结果的Excel文件
- Needle原始结果：Needle算法的原始输出文件

## 6. 错误处理

- 如果输入序列为空，程序会提示"请输入靶序列和查询序列"
- 如果输入位点格式错误，程序会自动解析有效数字
- 如果特定位点超出序列长度，对应结果显示"-"
- 如果外部工具调用失败，程序会忽略该算法的结果，继续使用其他算法

## 7. 性能优化

- 程序使用内存中的文件处理，避免了大量的磁盘I/O操作
- 异步处理比对请求，提高了系统的并发处理能力
- 自动清理临时文件，避免了磁盘空间的浪费

## 8. 版本信息

- 序列比对工具版本：1.0
- BioPython版本：依赖系统安装的BioPython库
- 外部工具版本：
  - ClustalW：2.x
  - EMBOSS：6.x
  - MUSCLE：3.8.x

## 9. 联系方式

如有任何问题或建议，请联系开发团队。
