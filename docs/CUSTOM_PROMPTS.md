# 自定义Prompt指南

本指南介绍如何自定义AI生成内容的Prompt，以获得更符合您需求的论文分析结果。

## 目录

- [Prompt文件结构](#prompt文件结构)
- [内置Prompt说明](#内置prompt说明)
- [自定义Prompt](#自定义prompt)
- [使用示例](#使用示例)
- [最佳实践](#最佳实践)

## Prompt文件结构

Prompt配置文件位于 `prompts/prompts.yaml`，使用YAML格式：

```yaml
prompt_type:
  system: "系统提示词"
  user_template: |
    用户提示词模板
    可以使用 {变量名} 进行变量替换
```

## 内置Prompt说明

### 1. summarize（论文总结）

**作用**：生成论文的结构化总结

**可用变量**：
- `{title}` - 论文标题
- `{authors}` - 作者列表
- `{summary}` - 论文摘要

**默认格式**：
```yaml
summarize:
  system: "你是一位专业的学术论文分析专家，擅长提炼论文核心要点。"
  user_template: |
    请对以下学术论文进行总结分析，要求：

    1. **核心观点**：用 2-3 句话概括论文的主要贡献和创新点
    2. **研究方法**：简要说明使用的技术方法或理论框架
    3. **关键结果**：总结主要实验结果或理论发现
    4. **应用价值**：说明研究的实际应用场景或学术意义

    论文信息：
    标题：{title}
    作者：{authors}
    摘要：{summary}

    请用中文输出，使用清晰的结构化格式。
```

### 2. translate（摘要翻译）

**作用**：将英文摘要翻译成中文

**可用变量**：
- `{lang_name}` - 目标语言名称
- `{text}` - 待翻译文本

**默认格式**：
```yaml
translate:
  system: "你是一位专业的学术翻译专家。"
  user_template: |
    请将以下英文学术摘要翻译成{lang_name}，要求翻译准确、专业、流畅：

    {text}
```

### 3. insights（关键洞察）

**作用**：提取论文的关键洞察点

**可用变量**：
- `{title}` - 论文标题
- `{summary}` - 论文摘要

**默认格式**：
```yaml
insights:
  system: "你是一位专业的学术研究洞察专家，擅长从论文中提炼关键见解。"
  user_template: |
    请从以下学术论文中提取关键洞察，每个洞察应简洁明了、富有启发性。

    论文信息：
    标题：{title}
    摘要：{summary}

    请以 JSON 格式输出，格式如下：
    {{
      "insights": [
        "洞察1：简短描述（不超过30字）",
        "洞察2：简短描述（不超过30字）",
        "洞察3：简短描述（不超过30字）"
      ]
    }}
```

## 自定义Prompt

### 示例1：更技术化的总结

如果您希望总结更侧重技术细节：

```yaml
summarize:
  system: "你是一位精通机器学习的技术专家，擅长分析算法细节。"
  user_template: |
    请对以下机器学习论文进行技术分析：

    标题：{title}
    作者：{authors}
    摘要：{summary}

    请重点分析：
    1. **算法创新**：具体的技术改进点
    2. **数学原理**：核心公式或理论基础
    3. **实验设置**：数据集、评估指标、对比方法
    4. **性能提升**：具体的量化指标（准确率、速度等）
    5. **代码实现**：是否开源、关键技术点

    输出应包含技术术语，面向研究人员和工程师。
```

### 示例2：面向产品经理的总结

如果您希望从产品角度理解论文：

```yaml
custom:
  product_summary:
    system: "你是一位技术产品经理，擅长将学术成果转化为产品价值。"
    user_template: |
      请从产品角度分析以下论文：

      标题：{title}
      摘要：{summary}

      请回答：
      1. **解决什么问题**：这项技术能解决什么实际问题？
      2. **用户价值**：对最终用户有什么好处？
      3. **落地难度**：技术实现的复杂度（1-5星）
      4. **商业潜力**：可能的商业应用场景
      5. **竞争优势**：相比现有方案的优势

      用非技术语言解释，面向产品和业务团队。
```

### 示例3：深度技术评估

添加更深入的技术评估：

```yaml
custom:
  technical_review:
    system: "你是一位资深技术审稿人。"
    user_template: |
      请对以下论文进行学术审稿式评估：

      标题：{title}
      摘要：{summary}

      评估标准：
      1. **创新性**：是否有实质性创新？（0-10分）
      2. **技术难度**：实现难度如何？（0-10分）
      3. **实验充分性**：实验设计是否充分？
      4. **可复现性**：结果是否容易复现？
      5. **实用价值**：是否有实际应用价值？
      6. **局限性**：可能的不足和改进方向

      给出客观、批判性的评价。
```

## 使用自定义Prompt

自定义prompt定义后，可以在代码中调用：

```python
from src.prompt_loader import get_prompt_loader

# 获取prompt loader
loader = get_prompt_loader()

# 使用自定义prompt
system, user = loader.get_custom_prompt(
    'product_summary',
    title="论文标题",
    summary="论文摘要"
)
```

## 提示词编写技巧

### 1. 明确角色定位

在system提示词中明确AI的角色和专业领域：

```yaml
system: "你是一位拥有10年经验的机器学习研究员，专注于计算机视觉领域。"
```

### 2. 结构化输出

使用清晰的输出结构：

```yaml
user_template: |
  请按以下格式输出：

  ## 技术创新
  [内容]

  ## 实验结果
  [内容]

  ## 应用场景
  [内容]
```

### 3. 具体的指标和要求

给出明确的量化要求：

```yaml
user_template: |
  要求：
  - 每个部分不超过100字
  - 至少列出3个关键技术点
  - 使用专业术语
  - 包含具体的性能数据
```

### 4. 示例驱动

提供输出示例：

```yaml
user_template: |
  输出格式示例：

  创新点：提出了XXX方法，相比YYY提升了ZZ%
  技术难点：主要挑战在于AAA，论文通过BBB解决
  应用价值：可用于CCC场景，预期提升DDD
```

### 5. 上下文信息

提供必要的上下文：

```yaml
user_template: |
  背景：当前领域的主流方法是 {current_method}
  论文信息：{title}

  请对比分析论文方法与主流方法的异同。
```

## 多语言支持

### 英文输出

```yaml
summarize_en:
  system: "You are an expert in academic paper analysis."
  user_template: |
    Analyze the following paper:

    Title: {title}
    Authors: {authors}
    Abstract: {summary}

    Please provide:
    1. Key contributions
    2. Methodology
    3. Results
    4. Practical applications
```

### 双语输出

```yaml
bilingual_summary:
  system: "你是一位双语学术专家。"
  user_template: |
    请对以下论文提供中英双语总结：

    标题：{title}
    摘要：{summary}

    格式：

    【中文】
    核心观点：...

    【English】
    Key Points: ...
```

## 针对特定领域优化

### NLP领域

```yaml
custom:
  nlp_analysis:
    system: "你是一位自然语言处理专家。"
    user_template: |
      分析NLP论文：{title}

      重点关注：
      1. 使用的预训练模型（BERT/GPT等）
      2. 数据集和评估指标（BLEU/ROUGE等）
      3. 与baseline的对比
      4. 在哪些NLP任务上有效
```

### CV领域

```yaml
custom:
  cv_analysis:
    system: "你是一位计算机视觉专家。"
    user_template: |
      分析CV论文：{title}

      重点分析：
      1. 网络架构设计
      2. 训练技巧和trick
      3. 在ImageNet/COCO等基准上的表现
      4. 计算复杂度（FLOPs/参数量）
```

## 调试和优化

### 1. 测试Prompt效果

修改prompt后，先在小规模数据上测试：

```bash
# 设置只抓取1篇论文测试
ARXIV_MAX_RESULTS=1 python main.py
```

### 2. 迭代优化

根据输出结果调整prompt：

- 输出太长 → 添加字数限制
- 缺少关键信息 → 添加具体要求
- 格式不统一 → 提供输出模板

### 3. A/B测试

保存多个版本的prompt进行对比：

```yaml
summarize_v1:
  ...

summarize_v2:
  ...
```

## 常见问题

### Q: 修改prompt后何时生效？

A: 立即生效。系统每次运行时都会重新加载 `prompts.yaml`。

### Q: 如何恢复默认prompt？

A: 删除或重命名 `prompts/prompts.yaml`，系统会使用内置默认prompt。

### Q: 可以添加多少个自定义prompt？

A: 无限制。建议合理组织，避免文件过大。

### Q: 不同AI模型需要不同prompt吗？

A: 是的。GPT-4和GPT-3.5的理解能力不同，可能需要调整prompt复杂度。

## 参考资源

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Library](https://docs.anthropic.com/claude/prompt-library)
- [Best Practices for Prompt Engineering](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api)
