# ST26 XML 生成规则详细说明

## 1. 概述

本文档详细说明了从Excel输入文件生成ST26格式XML序列列表的规则和流程。系统使用Python的ElementTree库构建XML结构，并遵循WIPO ST26标准格式要求。

## 2. XML基本结构

### 2.1 根元素

生成的XML文档以`ST26SequenceListing`为根元素，包含以下属性：

| 属性名 | 取值 | 说明 |
|--------|------|------|
| originalFreeTextLanguageCode | en | 原始自由文本语言代码 |
| nonEnglishFreeTextLanguageCode | zh | 非英文自由文本语言代码 |
| dtdVersion | V1_3 | DTD版本号 |
| fileName | 动态生成 | 基于申请人文件参考生成 |
| softwareName | WIPO Sequence | 软件名称 |
| softwareVersion | 2.3.0 | 软件版本 |
| productionDate | 动态生成 | 当前日期，格式：YYYY-MM-DD |

### 2.2 头部信息

根元素下包含以下头部信息：

- `ApplicantFileReference`：申请人文件参考
- `EarliestPriorityApplicationIdentification`：最早优先权申请标识（可选，如提供）
  - `IPOfficeCode`：知识产权局代码
  - `ApplicationNumberText`：申请号文本
  - `FilingDate`：申请日期
- `ApplicantName`：申请人名称（自动判断语言代码）
- `ApplicantNameLatin`：申请人名称拉丁文（如需要）
- `InventorName`：发明人名称（自动判断语言代码）
- `InventorNameLatin`：发明人名称拉丁文（如需要）
- `InventionTitle`：发明名称（自动判断语言代码）
- `SequenceTotalQuantity`：序列总数

## 3. 序列数据处理

### 3.1 序列解析

系统使用`parser.py`中的`parse_sequence`函数解析输入序列，提取以下信息：

- `naked_sequence`：裸露序列（去除修饰符后的序列）
- `modifications`：修饰信息列表
- `special_positions`：特殊位置列表
- `has_degenerate_bases`：是否包含简并碱基
- `ligand_removed`：是否移除了配体

### 3.2 序列转换规则

1. **RNA到DNA的碱基转换**：所有RNA序列中的`U`（尿苷）将转换为`T`（胸苷）以符合ST26标准

2. **大小写处理**：
   - DNA/RNA序列：转换为小写
   - 氨基酸序列：保持原始大小写

3. **简并碱基处理**：识别并保留简并碱基（M/R/W/S/Y/K/V/H/D/B），并生成相应提醒

4. **配体处理**：自动检测并移除序列末尾的L96配体，生成相应提醒

## 4. 修饰碱基处理规则

### 4.1 修饰类型

系统支持以下修饰类型：

| 修饰符 | 名称 | 说明 |
|--------|------|------|
| m | 2'-O-甲基化 | 2'-O-methyl |
| f | 2'-氟代 | 2'-fluoro |
| e | 2'-甲氧基乙基 | 2'-methoxyethyl |
| s | 硫代磷酸酯键 | phosphorothioate linkage |
| pv | 5'乙烯基膦酸酯 | 5prime-vinylphosphonate |

### 4.2 修饰碱基的XML表示

修饰碱基在XML中表示为`modified_base`或`misc_feature`特征：

#### 4.2.1 2'-O-甲基化 (m)

- **A碱基**：
  ```xml
  <INSDFeature>
    <INSDFeature_key>modified_base</INSDFeature_key>
    <INSDFeature_location>位置</INSDFeature_location>
    <INSDFeature_quals>
      <INSDQualifier>
        <INSDQualifier_name>mod_base</INSDQualifier_name>
        <INSDQualifier_value>OTHER</INSDQualifier_value>
      </INSDQualifier>
      <INSDQualifier id="qX">
        <INSDQualifier_name>note</INSDQualifier_name>
        <INSDQualifier_value>2prime-O-methyl adenosine</INSDQualifier_value>
      </INSDQualifier>
    </INSDFeature_quals>
  </INSDFeature>
  ```

- **其他碱基**：
  ```xml
  <INSDFeature>
    <INSDFeature_key>modified_base</INSDFeature_key>
    <INSDFeature_location>位置</INSDFeature_location>
    <INSDFeature_quals>
      <INSDQualifier>
        <INSDQualifier_name>mod_base</INSDQualifier_name>
        <INSDQualifier_value>Am/Gm/Cm/Tm</INSDQualifier_value>
      </INSDQualifier>
    </INSDFeature_quals>
  </INSDFeature>
  ```

#### 4.2.2 2'-氟代 (f)

```xml
<INSDFeature>
  <INSDFeature_key>modified_base</INSDFeature_key>
  <INSDFeature_location>位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier>
      <INSDQualifier_name>mod_base</INSDQualifier_name>
      <INSDQualifier_value>OTHER</INSDQualifier_value>
    </INSDQualifier>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>2prime-fluoro 碱基名称</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

#### 4.2.3 2'-甲氧基乙基 (e)

```xml
<INSDFeature>
  <INSDFeature_key>modified_base</INSDFeature_key>
  <INSDFeature_location>位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier>
      <INSDQualifier_name>mod_base</INSDQualifier_name>
      <INSDQualifier_value>OTHER</INSDQualifier_value>
    </INSDQualifier>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>2prime-methoxyethyl 碱基名称</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

#### 4.2.4 硫代磷酸酯键 (s)

```xml
<INSDFeature>
  <INSDFeature_key>misc_feature</INSDFeature_key>
  <INSDFeature_location>位置^位置+1</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>phosphorothioate linkage</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

#### 4.2.5 5'乙烯基膦酸酯 (pv)

```xml
<INSDFeature>
  <INSDFeature_key>modified_base</INSDFeature_key>
  <INSDFeature_location>1</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier>
      <INSDQualifier_name>mod_base</INSDQualifier_name>
      <INSDQualifier_value>OTHER</INSDQualifier_value>
    </INSDQualifier>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>5prime-vinylphosphonate</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

## 5. 特殊位置处理规则

### 5.1 DNA/RNA序列中的N位置

DNA/RNA序列中的`N`（未知碱基）被视为特殊位置，处理规则如下：

1. **替换规则**：
   - 如果freetext包含"or"：保持`N`不变
   - 否则：根据freetext内容替换为相应碱基（A/T/C/G）

2. **XML表示**：
   - 如果freetext包含"or"：生成`misc_difference`特征
   - 无论是否包含"or"：生成`modified_base`特征

```xml
<!-- 示例：包含or的情况 -->
<INSDFeature>
  <INSDFeature_key>misc_difference</INSDFeature_key>
  <INSDFeature_location>位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>freetext内容</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>

<INSDFeature>
  <INSDFeature_key>modified_base</INSDFeature_key>
  <INSDFeature_location>位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier>
      <INSDQualifier_name>mod_base</INSDQualifier_name>
      <INSDQualifier_value>OTHER</INSDQualifier_value>
    </INSDQualifier>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>freetext内容</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

### 5.2 氨基酸序列中的X位置

氨基酸序列中的`X`（未知氨基酸）被视为特殊位置，XML表示为`SITE`特征：

```xml
<INSDFeature>
  <INSDFeature_key>SITE</INSDFeature_key>
  <INSDFeature_location>位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>freetext内容</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

## 6. 环信息处理规则

### 6.1 二硫键验证

对于氨基酸序列中的二硫键环，系统会验证位置上的氨基酸是否为半胱氨酸（C）或未知氨基酸（X），如不符合则抛出错误。

### 6.2 XML表示

环信息在XML中表示为`REGION`特征：

```xml
<INSDFeature>
  <INSDFeature_key>REGION</INSDFeature_key>
  <INSDFeature_location>起始位置..结束位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>环描述</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

## 7. 杂合DNA序列处理规则

### 7.1 区段验证

系统会验证杂合DNA序列的区段是否连续，如不连续则抛出错误。

### 7.2 XML表示

杂合DNA序列的每个区段在XML中表示为`misc_feature`特征：

```xml
<INSDFeature>
  <INSDFeature_key>misc_feature</INSDFeature_key>
  <INSDFeature_location>起始位置..结束位置</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier id="qX">
      <INSDQualifier_name>note</INSDQualifier_name>
      <INSDQualifier_value>区段类型（DNA/RNA）</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

## 8. 源特征处理

每个序列必须包含一个`source`特征，包含以下限定符：

- `mol_type`：分子类型（如other RNA、other DNA、protein等）
- `organism`：生物体名称

```xml
<INSDFeature>
  <INSDFeature_key>source</INSDFeature_key>
  <INSDFeature_location>1..序列长度</INSDFeature_location>
  <INSDFeature_quals>
    <INSDQualifier>
      <INSDQualifier_name>mol_type</INSDQualifier_name>
      <INSDQualifier_value>分子类型</INSDQualifier_value>
    </INSDQualifier>
    <INSDQualifier id="qX">
      <INSDQualifier_name>organism</INSDQualifier_name>
      <INSDQualifier_value>生物体名称</INSDQualifier_value>
    </INSDQualifier>
  </INSDFeature_quals>
</INSDFeature>
```

## 9. 输出格式和文件结构

### 9.1 XML声明

生成的XML文件包含以下声明：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ST26SequenceListing PUBLIC "-//WIPO//DTD Sequence Listing 1.3//EN" "ST26SequenceListing_V1_3.dtd">
```

### 9.2 文件命名

XML文件以申请人文件参考命名，扩展名为.xml。

### 9.3 字符编码

文件使用UTF-8编码，确保支持国际字符。

## 10. 提醒生成规则

系统会生成以下提醒：

1. **未指定分子类型**：使用默认RNA，生成提醒
2. **未指定生物体名称**：使用默认'synthetic construct'，生成提醒
3. **未指定限定符分子类型**：使用默认值，生成提醒
4. **移除L96配体**：检测到并移除配体，生成提醒
5. **包含简并碱基**：检测到简并碱基，生成提醒

## 11. 输入输出示例

### 11.1 输入示例（简化Excel行）

| 序列 | 分子类型 | 生物体 | 限定符分子类型 | freetext1 |
|------|----------|--------|----------------|-----------|
| mGmGmUmUfGmGfAmUfUfUfUmUfCmUmUmGmCmUmAmUmG | RNA | synthetic construct | other RNA | 2'-O-methylguanosine |

### 11.2 输出示例（简化XML）

```xml
<ST26SequenceListing ...>
  <ApplicantFileReference>Example</ApplicantFileReference>
  <SequenceTotalQuantity>1</SequenceTotalQuantity>
  <SequenceData sequenceIDNumber="1">
    <INSDSeq>
      <INSDSeq_length>22</INSDSeq_length>
      <INSDSeq_moltype>RNA</INSDSeq_moltype>
      <INSDSeq_division>PAT</INSDSeq_division>
      <INSDSeq_feature-table>
        <INSDFeature>
          <INSDFeature_key>source</INSDFeature_key>
          <INSDFeature_location>1..22</INSDFeature_location>
          <INSDFeature_quals>
            <INSDQualifier>
              <INSDQualifier_name>mol_type</INSDQualifier_name>
              <INSDQualifier_value>other RNA</INSDQualifier_value>
            </INSDQualifier>
            <INSDQualifier id="q2">
              <INSDQualifier_name>organism</INSDQualifier_name>
              <INSDQualifier_value>synthetic construct</INSDQualifier_value>
            </INSDQualifier>
          </INSDFeature_quals>
        </INSDFeature>
        <!-- 修饰碱基特征 -->
        <INSDFeature>
          <INSDFeature_key>modified_base</INSDFeature_key>
          <INSDFeature_location>1</INSDFeature_location>
          <INSDFeature_quals>
            <INSDQualifier>
              <INSDQualifier_name>mod_base</INSDQualifier_name>
              <INSDQualifier_value>gm</INSDQualifier_value>
            </INSDQualifier>
          </INSDFeature_quals>
        </INSDFeature>
        <!-- 其他修饰碱基特征... -->
      </INSDSeq_feature-table>
      <INSDSeq_sequence>ggtufgmgfamufufufumufcmumumgcmumamumg</INSDSeq_sequence>
    </INSDSeq>
  </SequenceData>
</ST26SequenceListing>
```

## 12. 代码实现细节

### 12.1 关键函数

#### `generate_xml(sequences, basic_data, output_folder)`

主函数，负责生成XML根元素并处理每个序列：

1. 创建XML根元素和基本结构
2. 遍历每个序列，解析并生成序列数据
3. 处理修饰、特殊位置和环信息
4. 生成提醒列表

#### `parse_sequence(sequence, raw_moltype, line_number)`

序列解析函数：

1. 转换新格式的修饰标注到旧格式
2. 移除配体
3. 解析修饰符和碱基
4. 提取裸露序列、修饰信息和特殊位置

#### `write_xml_to_file(root, filename)`

XML文件写入函数：

1. 添加XML声明和DOCTYPE
2. 使用ElementTree写入XML内容

### 12.2 数据结构

#### 修饰信息结构
```python
modifications = [(位置, 修饰类型, 碱基), ...]
# 示例：[(1, 'm', 'g'), (2, 'm', 'g'), ...]
```

#### 特殊位置结构
```python
special_positions = [位置1, 位置2, ...]
# 示例：[5, 8, 10]
```

#### 环信息结构
```python
ring_infos = [
  {'start': 起始位置, 'end': 结束位置, 'note': 环描述}, ...
]
# 示例：[{'start': 1, 'end': 10, 'note': 'disulfide bond'}]
```

#### 杂合区段结构
```python
hybrid_segments = [
  {'start': 起始位置, 'end': 结束位置, 'type': 区段类型}, ...
]
# 示例：[{'start': 1, 'end': 10, 'type': 'DNA'}, {'start': 11, 'end': 20, 'type': 'RNA'}]
```

## 13. 版本历史

- V1.0：初始版本，支持基本的DNA/RNA/氨基酸序列生成
- V1.1：增加修饰碱基支持
- V1.2：增加特殊位置和环信息处理
- V1.3：增加杂合DNA序列支持
- V2.0：优化序列解析逻辑
- V2.3：当前版本，支持新格式序列标注