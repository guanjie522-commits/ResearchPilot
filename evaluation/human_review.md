# ResearchPilot 第一轮 Benchmark 人工审核

- 数据集版本：`0.3`
- 首轮实际评测题：`q01`, `q04`, `q09`, `q16`, `q10`
- 原始结果：`evaluation/results/formal_benchmark_pilot_20261110.json`
- 当前状态：`pending_human_review`

> 候选参考答案尚未人工确认。自动术语检查或引用结构通过，都不能把状态改成 `verified`。

审核选项：`correct` / `partially_correct` / `incorrect` / `insufficient_evidence` / `needs_source_check`。

## q01

1. **Question ID：** `q01`

2. **原始问题：** Using only the imported local PDFs, what design strategy is used to improve antiferroelectric polarization configuration for capacitive energy storage?

3. **候选参考答案：** The paper uses an entropy-increase strategy to design the antiferroelectric polarization configuration.

   - 状态：`pending_human_review`

4. **支持原文：**

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

5. **PDF 文件名：** `s41467-025-56194-1.pdf` p.1

6. **页码：** 1

7. **Baseline 回答：**

```text
证据不足
```

8. **Direct RAG 回答：**

```text
Based strictly on the provided retrieval evidence, the design strategy used to improve antiferroelectric polarization configuration for capacitive energy storage is described as follows:

The strategy involves **utilizing entropy increase effect to simultaneously break the long-range antiferroelectric order and locally adjust the fourfold commensurate modulated structure**. This is explicitly stated in the first page of the source PDF.

**Source attribution**:  
- Source file: `s41467-025-56194-1.pdf`  
- Page number: 1  
- Chunk ID: `c01c9f511e2a100e:p0001:c0000`  

**Rationale for evidence use**:  
- Evidence 1 (source file: `s41467-025-56194-1.pdf`, page 1) directly describes the design strategy in the context of the paper's title and opening paragraph. It specifies that the entropy increase effect is employed to achieve the dual objectives of breaking long-range antiferroelectric order and locally adjusting the fourfold commensurate modulated structure, which improves capacitive energy storage performance.  
- No other evidence provides a more specific or direct description of the design strategy for this query. Evidence 2, 3, and 4 contain references or related concepts (e.g., domain modulation, phase-field simulations) but do not explicitly define the strategy for improving antiferroelectric polarization configuration as the query requires. The evidence strictly adheres to the provided PDF fragments without supplementation.  

**Note**: The response is derived solely from the given evidence and does not include any external knowledge, assumptions, or inferences. The strategy is quoted verbatim from the evidence where applicable.

检索来源：
- s41467-025-56194-1.pdf 第 1 页 (chunk c01c9f511e2a100e:p0001:c0000)
- s41467-025-56194-1.pdf 第 8 页 (chunk c01c9f511e2a100e:p0008:c0000)
- materials-4180042.pdf 第 10 页 (chunk f831e3b0bc234f0b:p0010:c0002)
- 1-s2.0-S2352847824001278-main.pdf 第 1 页 (chunk d99a382568c429f7:p0001:c0000)
```

9. **Fast Mode 回答：**

```text
The design strategy used to improve antiferroelectric polarization configuration for capacitive energy storage is increasing entropy, as evidenced by [S1]. This strategy utilizes the entropy increase effect to simultaneously break the long-range antiferroelectric order and locally adjust the fourfold commensurate modulated polarization configuration, thereby enhancing ultrahigh capacitive energy storage performance.

引用索引：
- [S1] s41467-025-56194-1.pdf 第 1 页
```

10. **Deep Mode 回答：**

```text
根据导入的本地PDF证据，用于改善抗铁电极化配置以实现电容器能量存储的设计策略为：**通过增加熵（entropy increase）打破长程反铁电序并局部调整四重调制极化结构**（证据 [S1]）。  

该结论直接来源于证据 [S1] 的原文描述（相关度 0.629），其核心机制为：熵增效应被用于同时抑制长程反铁电序并优化四重调制极化结构，从而实现超高效电容器能量存储。其他证据（[S2]、[S3]、[S4]）仅提供相关参考文献列表，未直接描述该设计策略的具体实现细节，因此不作为策略结论的依据。  

（注：所有结论严格基于证据文本，未添加任何外部信息或假设；程序将自动追加唯一可信的来源索引。）

引用索引：
- [S1] s41467-025-56194-1.pdf 第 1 页
- [S2] s41467-025-56194-1.pdf 第 8 页
- [S3] materials-4180042.pdf 第 10 页
- [S4] materials-4180042.pdf 第 10 页
```

11. **真实引用来源：**

- A_baseline: 无
- B_direct_rag: s41467-025-56194-1.pdf p.1; s41467-025-56194-1.pdf p.8; materials-4180042.pdf p.10; 1-s2.0-S2352847824001278-main.pdf p.1
- C_fast: s41467-025-56194-1.pdf p.1
- D_deep: s41467-025-56194-1.pdf p.1; s41467-025-56194-1.pdf p.8; materials-4180042.pdf p.10; materials-4180042.pdf p.10

12. **待审核问题：**

- [ ] 回答是否直接回答了题目？
- [ ] 每个事实性结论是否由真实支持原文支持？
- [ ] 是否存在答案没有覆盖、但原文明确支持的限定条件？
- [ ] “increasing entropy”与回答中的机制描述是否一致？

**审核决定：**

- [ ] correct
- [ ] partially_correct
- [ ] incorrect
- [ ] insufficient_evidence
- [ ] needs_source_check

**审核备注：**

```text

```

## q04

1. **Question ID：** `q04`

2. **原始问题：** Using only the imported local PDFs, which three variables are investigated in the phase-field study of PZO-based antiferroelectric films?

3. **候选参考答案：** The variables are misfit strain between film and substrate, defect-dipole doping, and film thickness.

   - 状态：`pending_human_review`

4. **支持原文：**

> the effects of three variables, mis ﬁt strain between the thin ﬁlm and substrate, defect dipoles doping, and ﬁlm thickness, on the domain structure and energy storage performance of PZO-based antiferroelectric materials are comprehensively investigated via phase-ﬁeld simulations.

5. **PDF 文件名：** `1-s2.0-S2352847824001278-main.pdf` p.1

6. **页码：** 1

7. **Baseline 回答：**

```text
证据不足
```

8. **Direct RAG 回答：**

```text
Based solely on the provided retrieval evidence, the three variables investigated in the phase-field study of PZO-based antiferroelectric films are:  
(1) mis fit strain between the thin film and substrate,  
(2) defect dipoles doping, and  
(3) film thickness.  

Source: 1-s2.0-S2352847824001278-main.pdf, page 1.  

*Note: The conclusion is derived exclusively from Evidence 4 (page 1 of the source PDF), which explicitly states: "the effects of three variables, mis fit strain between the thin film and substrate, defect dipoles doping, and film thickness, on the domain structure and energy storage performance of PZO-based antiferroelectric materials are comprehensively investigated via phase-ﬁeld simulations." No additional variables or details are inferred from other evidence, as they do not specify the three variables in question.*

检索来源：
- 1-s2.0-S2352847824001278-main.pdf 第 5 页 (chunk d99a382568c429f7:p0005:c0000)
- 1-s2.0-S2352847824001278-main.pdf 第 2 页 (chunk d99a382568c429f7:p0002:c0005)
- 1-s2.0-S2352847824001278-main.pdf 第 8 页 (chunk d99a382568c429f7:p0008:c0012)
- 1-s2.0-S2352847824001278-main.pdf 第 1 页 (chunk d99a382568c429f7:p0001:c0001)
```

9. **Fast Mode 回答：**

```text
The three variables investigated in the phase-field study of PZO-based antiferroelectric films are:  
(1) misfit strain between the thin film and substrate [S4],  
(2) defect dipoles doping [S4],  
(3) film thickness [S4].

引用索引：
- [S4] 1-s2.0-S2352847824001278-main.pdf 第 1 页
```

10. **Deep Mode 回答：**

```text
Based on the provided evidence, the three variables investigated in the phase-field study of PZO-based antiferroelectric films are:  
1. Misfit strain between the thin film and substrate  
2. Defect dipoles doping  
3. Film thickness  

These are explicitly stated in evidence [S4].

引用索引：
- [S4] 1-s2.0-S2352847824001278-main.pdf 第 1 页
```

11. **真实引用来源：**

- A_baseline: 无
- B_direct_rag: 1-s2.0-S2352847824001278-main.pdf p.5; 1-s2.0-S2352847824001278-main.pdf p.2; 1-s2.0-S2352847824001278-main.pdf p.8; 1-s2.0-S2352847824001278-main.pdf p.1
- C_fast: 1-s2.0-S2352847824001278-main.pdf p.1
- D_deep: 1-s2.0-S2352847824001278-main.pdf p.1

12. **待审核问题：**

- [ ] 回答是否直接回答了题目？
- [ ] 每个事实性结论是否由真实支持原文支持？
- [ ] 是否存在答案没有覆盖、但原文明确支持的限定条件？
- [ ] misfit strain、defect-dipole doping、film thickness 是否完整？
- [ ] 术语检查通过是否可能掩盖额外的不当结论？

**审核决定：**

- [ ] correct
- [ ] partially_correct
- [ ] incorrect
- [ ] insufficient_evidence
- [ ] needs_source_check

**审核备注：**

```text

```

## q09

1. **Question ID：** `q09`

2. **原始问题：** 请用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。

3. **候选参考答案：** 它通过傅里叶空间扰动方案处理具有空间变化的完整各向异性梯度能量张量。

   - 状态：`pending_human_review`

4. **支持原文：**

> Through a Fou- rier-space perturbation scheme, we achieve the ability to treat the full anisotropic gradient energy tensor with spatial variations, overcoming limitations of previous constant-coeﬃ- cient or isotropic approximations.

5. **PDF 文件名：** `materials-4180042.pdf` p.1

6. **页码：** 1

7. **Baseline 回答：**

```text
证据不足
```

8. **Direct RAG 回答：**

```text
根据用户提供的检索证据，我将严格基于证据内容用中文说明该扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。每条事实性结论均标注来源文件名和页码（所有证据均来自 `materials-4180042.pdf`）。证据内容仅限于提供的片段，未添加任何自身知识或常识性补充。

### 说明：
该扰动模型（即文中所述的“rate perturbation framework”）能处理以前常系数或各向同性近似难以处理的问题，原因如下：

1. **以前方法的局限性**：  
   以前的傅里叶谱扰动方法（previous Fourier-spectral perturbation methods）要么假设梯度系数为常数（constant gradient coefficients），要么将各向异性和空间异质性（spatial heterogeneity）分别处理，导致无法同时有效处理具有各向异性梯度能量和空间变化的复杂系统。  
   *来源：materials-4180042.pdf, 页码9*（Evidence 3）

2. **本模型的处理机制**：  
   本模型通过分解梯度能量张量（gradient energy tensor）为均匀部分（homogeneous part，隐式处理）和波动部分（fluctuating part，显式处理），提供了一个统一的框架（unified framework），能够同时处理全各向异性梯度能量张量及其任意空间变化。这种分解机制允许在倒空间（reciprocal space）中高效迭代求解，从而克服了传统方法的局限性。  
   *来源：materials-4180042.pdf, 页码9*（Evidence 3）

3. **具体应用场景**：  
   该模型能处理的问题包括铁电/反铁电复合材料（ferroelectric/antiferroelectric composites）中的组分梯度（composition gradients）或结构调制（structural modulations），这些问题在以前的常系数或各向同性近似下难以被有效建模。  
   *来源：materials-4180042.pdf, 页码9*（Evidence 3）

### 为什么能处理？核心结论
该扰动模型能处理以前常系数或各向同性近似难以处理的问题，**直接原因**是它避免了以前方法的两个关键缺陷：  
- 以前方法假设梯度系数为常数（导致无法处理空间变化）；  
- 以前方法将各向异性和空间异质性分开处理（导致无法同时建模复杂系统）。  
本模型通过统一框架实现对全各向异性梯度能量张量的显式-隐式分解，从而在倒空间中高效求解，解决了这些难以处理的问题。

**证据总结**：所有结论均严格基于提供的检索证据（Evidence 3 为核心证据），未引入任何外部知识或推测。该模型的处理能力已通过数值实验验证（Evidence 3 提及），但具体实验细节未在证据中展开，故不额外说明。

检索来源：
- materials-4180042.pdf 第 8 页 (chunk f831e3b0bc234f0b:p0008:c0002)
- materials-4180042.pdf 第 5 页 (chunk f831e3b0bc234f0b:p0005:c0002)
- materials-4180042.pdf 第 9 页 (chunk f831e3b0bc234f0b:p0009:c0001)
- materials-4180042.pdf 第 4 页 (chunk f831e3b0bc234f0b:p0004:c0002)
```

9. **Fast Mode 回答：**

```text
根据提供的证据，这个扰动模型能处理以前常系数（即梯度系数为常数）或各向同性近似难以处理的问题，原因如下（每条事实性结论均严格引用真实证据ID）：

1. **以前的方法存在局限性**：以前的傅里叶-谱扰动方法要么假设梯度系数为常数（即各向同性），要么将各向异性和空间异质性分开处理，导致无法有效处理同时具有各向异性和局部异质性的系统（[S3]）。  
2. **本模型的核心机制**：本扰动模型通过将梯度能量张量分解为均匀部分（隐式处理）和波动部分（显式处理），在傅里叶空间中提供统一的求解框架，从而能同时处理全各向异性梯度能量张量及其任意空间变化（[S3]）。  
3. **实际应用优势**：该方法在相场建模中特别适用于铁电/反铁电复合材料等系统（其中梯度能量既各向异性又局部异质），解决了以往方法无法处理的复杂场景（[S3]）。

综上，本扰动模型通过上述机制，直接克服了以前常系数或各向同性近似难以处理的问题，其核心依据均来自证据[S3]（该证据的文本明确描述了该框架如何同时应对各向异性和空间异质性）。其他证据（如[S1]）虽提及扰动方法的数值稳定性优势，但未直接解释“为何能处理问题”的根本原因，因此本回答仅聚焦[S3]以确保结论的精确性和证据可追溯性。

引用索引：
- [S1] materials-4180042.pdf 第 8 页
- [S3] materials-4180042.pdf 第 9 页
```

10. **Deep Mode 回答：**

```text
扰动模型能够有效处理以往常系数或各向同性近似难以应对的问题，其核心原因基于以下三点事实性结论（证据来源均严格对应提供的证据ID）：

1. **物理模型适应性**：传统常系数模型假设介质为均匀且各向同性（如各向同性弹性介质），但实际地质结构常存在横各向异性（如垂直对称轴的弹性介质）。扰动模型通过引入小扰动项，直接建模介质从各向同性到各向异性的渐变过程（[S5]）。  
   *（注：此结论源自[S5]中对横各向异性介质扰动建模的描述，明确区分了传统模型的局限性与扰动模型的适应性。）*

2. **误差敏感性优化**：在计算P波和S波旅行时差时，扰动模型能更精确地捕捉深度、垂直速度比及各向异性参数（如anellipticity参数）的微小变化。传统方法（如通用移动出近似GMA）在参数变化时误差显著增大，而扰动模型通过局部线性化近似，将误差敏感性控制在可接受范围内（[S5]）。  
   *（注：此结论源自[S5]中对扰动系数从隐式参数偏移-旅行时方程导出的机制分析，避免了对传统方法误差的过度推断。）*

3. **实际应用价值**：在地震数据处理中，扰动模型可直接应用于高精度成像（如时间迁移），从而避免传统方法因假设不成立导致的结构模糊问题（[S5]）。  
   *（注：此结论源自[S5]的实证场景，聚焦于扰动模型在实际地质应用中的优势，未引入额外数据或假设。）*

以上结论均严格基于证据[S5]（2022年Geophysics期刊论文），未添加任何未验证的DOI、页码、公式或实验数据。程序将自动追加唯一可信的来源索引，确保响应的精确性与可追溯性。

引用索引：
- [S5] Crossref DOI: 10.1190/geo2021-0695.1
```

11. **真实引用来源：**

- A_baseline: 无
- B_direct_rag: materials-4180042.pdf p.8; materials-4180042.pdf p.5; materials-4180042.pdf p.9; materials-4180042.pdf p.4
- C_fast: materials-4180042.pdf p.8; materials-4180042.pdf p.9
- D_deep: DOI 10.1190/geo2021-0695.1

12. **待审核问题：**

- [ ] 回答是否直接回答了题目？
- [ ] 每个事实性结论是否由真实支持原文支持？
- [ ] 是否存在答案没有覆盖、但原文明确支持的限定条件？
- [ ] 原始题干的“这个扰动模型”是否明确指向本地 PDF？
- [ ] Deep Mode 使用 Crossref 地球物理论文是否属于来源错误？

**审核决定：**

- [ ] correct
- [ ] partially_correct
- [ ] incorrect
- [ ] insufficient_evidence
- [ ] needs_source_check

**审核备注：**

```text

```

> 数据清洗说明：原始 q09 保留不变；明确限定本地 PDF 的变体为 `q09_local_pdf`，当前尚未运行。

## q16

1. **Question ID：** `q16`

2. **原始问题：** Using only the imported local PDFs, compare the main design approaches of the entropy paper and the PZO domain-modulation paper.

3. **候选参考答案：** The first paper uses increasing entropy to design the polarization configuration; the second studies domain modulation with phase-field simulations.

   - 状态：`pending_human_review`

4. **支持原文：**

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

> Antiferroelectric domain modulation enhancing energy storage performance by phase- ﬁeld simulations

5. **PDF 文件名：** `s41467-025-56194-1.pdf` p.1, `1-s2.0-S2352847824001278-main.pdf` p.1

6. **页码：** 1, 1

7. **Baseline 回答：**

```text
证据不足
```

8. **Direct RAG 回答：**

```text
证据不足：当前索引中没有与问题足够相关的 PDF 片段，因此不能基于论文回答。
```

9. **Fast Mode 回答：**

```text
证据不足。
```

10. **Deep Mode 回答：**

```text
证据不足。根据当前证据，本地PDF库中未检索到与关键词"entropy"相关的有效证据（相关性阈值0.25未达标），因此无法确定熵论文的设计方法，进而无法比较熵论文和PZO域调制论文的主要设计方法。
```

11. **真实引用来源：**

- A_baseline: 无
- B_direct_rag: 无
- C_fast: 无
- D_deep: 无

12. **待审核问题：**

- [ ] 回答是否直接回答了题目？
- [ ] 每个事实性结论是否由真实支持原文支持？
- [ ] 是否存在答案没有覆盖、但原文明确支持的限定条件？
- [ ] 回答是否同时覆盖两篇本地论文？
- [ ] 拒答是由真实证据不足导致，还是检索漏召回导致？

**审核决定：**

- [ ] correct
- [ ] partially_correct
- [ ] incorrect
- [ ] insufficient_evidence
- [ ] needs_source_check

**审核备注：**

```text

```

> q16 诊断：`entropy`, `top_k=4` 返回 0 条通过阈值的证据；两篇目标论文的支持 Chunk 均存在于 Chroma。

## q10

1. **Question ID：** `q10`

2. **原始问题：** 根据当前已导入的本地 PDF，这些论文在 500 K 下测得的超导临界温度是多少？

3. **候选参考答案：** The imported papers do not provide a superconducting critical temperature at 500 K.

   - 状态：`pending_human_review`

4. **支持原文：**

无预期支持摘录；审核者需确认三篇 PDF 均不支持该问题。

5. **PDF 文件名：** N/A（预期证据不足）

6. **页码：** N/A

7. **Baseline 回答：**

```text
证据不足
```

8. **Direct RAG 回答：**

```text
证据不足：当前索引中没有与问题足够相关的 PDF 片段，因此不能基于论文回答。
```

9. **Fast Mode 回答：**

```text
证据不足。
```

10. **Deep Mode 回答：**

```text
证据不足
```

11. **真实引用来源：**

- A_baseline: 无
- B_direct_rag: 无
- C_fast: 无
- D_deep: 无

12. **待审核问题：**

- [ ] 回答是否直接回答了题目？
- [ ] 每个事实性结论是否由真实支持原文支持？
- [ ] 是否存在答案没有覆盖、但原文明确支持的限定条件？
- [ ] 是否确认三篇本地 PDF 均没有 500 K 超导临界温度证据？
- [ ] 拒答是否明确且没有引入无关科学结论？

**审核决定：**

- [ ] correct
- [ ] partially_correct
- [ ] incorrect
- [ ] insufficient_evidence
- [ ] needs_source_check

**审核备注：**

```text

```
