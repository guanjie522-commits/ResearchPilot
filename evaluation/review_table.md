# ResearchPilot Benchmark 人工审核表

- Dataset version: `0.3`
- Questions: `20` core questions; the q09 local-source variant was run
  separately and is covered by `evaluation/human_review_summary.md`
- 参考答案均为候选，等待人工审核。

| ID | Type | Answerable | Source / Page | Review |
|---|---|---|---|---|
| q01 | fact_extraction | True | s41467-025-56194-1.pdf p.1 | [ ] pending_review |
| q02 | mechanism_explanation | True | s41467-025-56194-1.pdf p.1 | [ ] pending_review |
| q03 | fact_extraction | True | s41467-025-56194-1.pdf p.1 | [ ] pending_review |
| q04 | fact_extraction | True | 1-s2.0-S2352847824001278-main.pdf p.1 | [ ] pending_review |
| q05 | fact_extraction | True | 1-s2.0-S2352847824001278-main.pdf p.1 | [ ] pending_review |
| q06 | fact_extraction | True | materials-4180042.pdf p.1 | [ ] pending_review |
| q07 | cross_language | True | s41467-025-56194-1.pdf p.1 | [ ] pending_review |
| q08 | cross_language | True | 1-s2.0-S2352847824001278-main.pdf p.1 | [ ] pending_review |
| q09 | cross_language | True | materials-4180042.pdf p.1 | [ ] pending_review |
| q10 | insufficient_evidence | False | N/A | [ ] pending_review |
| q11 | insufficient_evidence | False | N/A | [ ] pending_review |
| q12 | insufficient_evidence | False | N/A | [ ] pending_review |
| q13 | mechanism_explanation | True | 1-s2.0-S2352847824001278-main.pdf p.2 | [ ] pending_review |
| q14 | mechanism_explanation | True | materials-4180042.pdf p.1 | [ ] pending_review |
| q15 | mechanism_explanation | True | 1-s2.0-S2352847824001278-main.pdf p.1 | [ ] pending_review |
| q16 | cross_paragraph_or_paper | True | s41467-025-56194-1.pdf p.1; 1-s2.0-S2352847824001278-main.pdf p.1 | [ ] pending_review |
| q17 | cross_paragraph_or_paper | True | 1-s2.0-S2352847824001278-main.pdf p.1; materials-4180042.pdf p.1 | [ ] pending_review |
| q18 | cross_paragraph_or_paper | True | s41467-025-56194-1.pdf p.1; 1-s2.0-S2352847824001278-main.pdf p.1; materials-4180042.pdf p.1 | [ ] pending_review |
| q19 | cross_paragraph_or_paper | True | materials-4180042.pdf p.1; materials-4180042.pdf p.1 | [ ] pending_review |
| q20 | insufficient_evidence | False | N/A | [ ] pending_review |

## 逐题对照

### q01

**Question:** Using only the imported local PDFs, what design strategy is used to improve antiferroelectric polarization configuration for capacitive energy storage?

**Candidate answer:** The paper uses an entropy-increase strategy to design the antiferroelectric polarization configuration.

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

### q02

**Question:** According to the paper, what competing effects make the antiferroelectric-ferroelectric phase transition a double-edged sword?

**Candidate answer:** It provides high energy-storage density but also causes large polarization hysteresis and poor efficiency.

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> Electric ﬁeld induced antiferroelectric-ferroelectric phase transition is a double-edged sword for energy storage properties, which not only offers a congenital superiority with substantial energy storage density but also poses signiﬁcant challenges such as large polarization hysteresis and poor efﬁciency

### q03

**Question:** What recoverable energy-storage density and efficiency are reported for the medium-entropy antiferroelectrics?

**Candidate answer:** The reported recoverable energy-storage density is 14.8 J cm^-3 and the efficiency is 90.2%.

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> recoverable energy storge density (14.8 J cm−3)a n de fﬁciency (90.2%)

### q04

**Question:** Using only the imported local PDFs, which three variables are investigated in the phase-field study of PZO-based antiferroelectric films?

**Candidate answer:** The variables are misfit strain between film and substrate, defect-dipole doping, and film thickness.

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.1

> the effects of three variables, mis ﬁt strain between the thin ﬁlm and substrate, defect dipoles doping, and ﬁlm thickness, on the domain structure and energy storage performance of PZO-based antiferroelectric materials are comprehensively investigated via phase-ﬁeld simulations.

### q05

**Question:** What recoverable energy density and efficiency are achieved at 1.5% tensile strain and 2% defect-dipole concentration?

**Candidate answer:** A recoverable energy density of 38.3 J/cm^3 and an efficiency of about 89.4%.

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.1

> a recoverable energy density of 38.3 J/cm 3 and an energy storage ef ﬁciency of about 89.4% can be realized at 1.5% tensile strain and 2% defect dipole concentration.

### q06

**Question:** What numerical method is the proposed model for anisotropic gradient energy based on?

**Candidate answer:** It is based on Fourier spectral methods.

**Verification status:** `pending_human_review`

- `materials-4180042.pdf` p.1

> we have developed a perturbation model for solv- ing anisotropic gradient energy based on Fourier spectral methods.

### q07

**Question:** 请用中文说明这篇论文主要通过什么设计策略提升反铁电储能性能。

**Candidate answer:** 主要通过增加熵来设计反铁电极化构型。

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

### q08

**Question:** 请用中文概括相场模拟研究了哪三类变量对 PZO 基反铁电薄膜畴结构和储能性能的影响。

**Candidate answer:** 研究者考察了薄膜与基底之间的失配应变、缺陷偶极子掺杂以及薄膜厚度三类变量。

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.1

> the effects of three variables, mis ﬁt strain between the thin ﬁlm and substrate, defect dipoles doping, and ﬁlm thickness, on the domain structure and energy storage performance of PZO-based antiferroelectric materials are comprehensively investigated via phase-ﬁeld simulations.

### q09

**Question:** 请用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。

**Candidate answer:** 它通过傅里叶空间扰动方案处理具有空间变化的完整各向异性梯度能量张量。

**Verification status:** `pending_human_review`

- `materials-4180042.pdf` p.1

> Through a Fou- rier-space perturbation scheme, we achieve the ability to treat the full anisotropic gradient energy tensor with spatial variations, overcoming limitations of previous constant-coeﬃ- cient or isotropic approximations.

### q10

**Question:** 根据当前已导入的本地 PDF，这些论文在 500 K 下测得的超导临界温度是多少？

**Candidate answer:** The imported papers do not provide a superconducting critical temperature at 500 K.

**Verification status:** `pending_human_review`

- No supporting excerpt expected; verify absence across imported PDFs.

### q11

**Question:** 根据当前已导入的本地 PDF，这些论文中优化的金纳米颗粒直径是多少纳米？

**Candidate answer:** The imported papers do not report an optimized gold-nanoparticle diameter.

**Verification status:** `pending_human_review`

- No supporting excerpt expected; verify absence across imported PDFs.

### q12

**Question:** 根据当前已导入的本地 PDF，这些论文中的随机对照临床试验共纳入多少名患者？

**Candidate answer:** The imported papers do not report a randomized clinical trial patient count.

**Verification status:** `pending_human_review`

- No supporting excerpt expected; verify absence across imported PDFs.

### q13

**Question:** According to the PZO paper, how does film thickness produce competing effects on energy-storage performance?

**Candidate answer:** Increasing thickness can raise dielectric constant and Ps, but excessively thick films can reduce efficiency and increase breakdown susceptibility.

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.2

> Ultrathin ﬁlms possess low energy loss (Wloss), the dielectric constant and Ps increase as the ﬁlm thickness increases. However, excessively thick ﬁlms suffer from low energy storage efﬁciency and susceptibility to breakdown, which impair the energy storage performance

### q14

**Question:** How does the perturbation model overcome previous constant-coefficient or isotropic approximations?

**Candidate answer:** The Fourier-space perturbation formulation treats a full anisotropic gradient-energy tensor whose coefficients vary spatially.

**Verification status:** `pending_human_review`

- `materials-4180042.pdf` p.1

> Through a Fou- rier-space perturbation scheme, we achieve the ability to treat the full anisotropic gradient energy tensor with spatial variations, overcoming limitations of previous constant-coeﬃ- cient or isotropic approximations.

### q15

**Question:** According to the abstract, how do tensile strain and defect dipoles jointly affect PZO-based antiferroelectric films?

**Candidate answer:** Tensile strain increases the AFE-to-FE transition field, while defect dipoles combined with tensile strain reduce hysteresis and improve efficiency.

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.1

> applying tensile strain to the ﬁlms can effectively increase the transition electric ﬁeld from antiferroelectric to ferroelectric. In addition, the introduction of defect dipoles while applying tensile strain can signi ﬁcantly reduce the hysteresis and improve energy storage ef ﬁciency.

### q16

**Question:** Using only the imported local PDFs, compare the main design approaches of the entropy paper and the PZO domain-modulation paper.

**Candidate answer:** The first paper uses increasing entropy to design the polarization configuration; the second studies domain modulation with phase-field simulations.

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

- `1-s2.0-S2352847824001278-main.pdf` p.1

> Antiferroelectric domain modulation enhancing energy storage performance by phase- ﬁeld simulations

### q17

**Question:** Using only the imported local PDFs, compare the phase-field simulation approach in the PZO film paper with the gradient-energy method in the ferroelectrics modeling paper.

**Candidate answer:** The PZO study applies phase-field simulations to strain, defect-dipole, and thickness effects; the modeling paper contributes a Fourier-spectral perturbation method for anisotropic gradient energy.

**Verification status:** `pending_human_review`

- `1-s2.0-S2352847824001278-main.pdf` p.1

> the effects of three variables, mis ﬁt strain between the thin ﬁlm and substrate, defect dipoles doping, and ﬁlm thickness, on the domain structure and energy storage performance of PZO-based antiferroelectric materials are comprehensively investigated via phase-ﬁeld simulations.

- `materials-4180042.pdf` p.1

> we have developed a perturbation model for solv- ing anisotropic gradient energy based on Fourier spectral methods.

### q18

**Question:** Using only the three imported local PDFs, how do the stated energy-storage goals and modeling approaches complement one another?

**Candidate answer:** The entropy and domain-modulation papers target improved antiferroelectric energy storage, while the modeling paper provides a robust numerical approach for FE/AFE composite phase-field simulations.

**Verification status:** `pending_human_review`

- `s41467-025-56194-1.pdf` p.1

> Design of antiferroelectric polarization conﬁguration for ultrahigh capacitive energy storage via increasing entropy

- `1-s2.0-S2352847824001278-main.pdf` p.1

> Antiferroelectric domain modulation enhancing energy storage performance by phase- ﬁeld simulations

- `materials-4180042.pdf` p.1

> The application of this model to FE/AFE composites demonstrates exceptional robustness and convergence eﬃciency.

### q19

**Question:** Using only the imported local PDFs, within the gradient-energy paper, what outcomes follow from applying the perturbation model to FE/AFE composites?

**Candidate answer:** The model shows robustness and convergence efficiency and can reproduce antiferroelectric phase diagrams and AFE-FE transition pathways under varying gradient-energy parameters.

**Verification status:** `pending_human_review`

- `materials-4180042.pdf` p.1

> The application of this model to FE/AFE composites demonstrates exceptional robustness and convergence eﬃciency.

- `materials-4180042.pdf` p.1

> the proposed perturbation scheme can accurately reproduce antiferroelectric phase diagrams and AFE-FE phase transition pathways under varying gradient energy parameters.

### q20

**Question:** 根据当前已导入的本地 PDF，这些样品经过 20 年现场服役后的年故障率是多少？

**Candidate answer:** The imported papers do not report a 20-year field-service annual failure rate.

**Verification status:** `pending_human_review`

- No supporting excerpt expected; verify absence across imported PDFs.

