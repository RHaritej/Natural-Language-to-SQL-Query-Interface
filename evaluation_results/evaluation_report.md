# Natural Language to SQL — Evaluation Report
**Generated:** 2026-11-16 19:59:54

---

## 1. Strategy Comparison Summary

| Strategy | Total Qs | Exact-Match (EM) | Execution Acc (EX) | Avg Corrections | Avg Latency (ms) |
|----------|----------|------------------|--------------------|-----------------|-----------------|
| zero_shot            |      100 | 97/100 (97.0%) | 100/100 (100.0%) | 1.00 | 2.5 |
| few_shot             |      100 | 100/100 (100.0%) | 100/100 (100.0%) | 1.00 | 2.1 |
| cot_planner          |      100 | 100/100 (100.0%) | 100/100 (100.0%) | 1.00 | 2.3 |
| self_correction      |      100 | 97/100 (97.0%) | 100/100 (100.0%) | 1.00 | 7.3 |
| react_agent          |      100 | 100/100 (100.0%) | 100/100 (100.0%) | 1.00 | 3.7 |

---

## 2. Difficulty Breakdown

### Strategy: zero_shot
| Difficulty | Count | Exact-Match | Execution Acc |
|------------|-------|-------------|---------------|
| easy         |    34 | 100.0% | 100.0% |
| medium       |    36 | 100.0% | 100.0% |
| hard         |    20 | 85.0% | 100.0% |
| extra-hard   |    10 | 100.0% | 100.0% |

### Strategy: few_shot
| Difficulty | Count | Exact-Match | Execution Acc |
|------------|-------|-------------|---------------|
| easy         |    34 | 100.0% | 100.0% |
| medium       |    36 | 100.0% | 100.0% |
| hard         |    20 | 100.0% | 100.0% |
| extra-hard   |    10 | 100.0% | 100.0% |

### Strategy: cot_planner
| Difficulty | Count | Exact-Match | Execution Acc |
|------------|-------|-------------|---------------|
| easy         |    34 | 100.0% | 100.0% |
| medium       |    36 | 100.0% | 100.0% |
| hard         |    20 | 100.0% | 100.0% |
| extra-hard   |    10 | 100.0% | 100.0% |

### Strategy: self_correction
| Difficulty | Count | Exact-Match | Execution Acc |
|------------|-------|-------------|---------------|
| easy         |    34 | 100.0% | 100.0% |
| medium       |    36 | 100.0% | 100.0% |
| hard         |    20 | 85.0% | 100.0% |
| extra-hard   |    10 | 100.0% | 100.0% |

### Strategy: react_agent
| Difficulty | Count | Exact-Match | Execution Acc |
|------------|-------|-------------|---------------|
| easy         |    34 | 100.0% | 100.0% |
| medium       |    36 | 100.0% | 100.0% |
| hard         |    20 | 100.0% | 100.0% |
| extra-hard   |    10 | 100.0% | 100.0% |

---

## 3. Database Breakdown

### Strategy: zero_shot
| Database | Count | Exact-Match | Execution Acc |
|----------|-------|-------------|---------------|
| car_1                          |    20 | 100.0% | 100.0% |
| concert_singer                 |    20 | 100.0% | 100.0% |
| employee_hire_evaluation       |    20 | 85.0% | 100.0% |
| student_transcripts_tracking   |    20 | 100.0% | 100.0% |
| world_1                        |    20 | 100.0% | 100.0% |

### Strategy: few_shot
| Database | Count | Exact-Match | Execution Acc |
|----------|-------|-------------|---------------|
| car_1                          |    20 | 100.0% | 100.0% |
| concert_singer                 |    20 | 100.0% | 100.0% |
| employee_hire_evaluation       |    20 | 100.0% | 100.0% |
| student_transcripts_tracking   |    20 | 100.0% | 100.0% |
| world_1                        |    20 | 100.0% | 100.0% |

### Strategy: cot_planner
| Database | Count | Exact-Match | Execution Acc |
|----------|-------|-------------|---------------|
| car_1                          |    20 | 100.0% | 100.0% |
| concert_singer                 |    20 | 100.0% | 100.0% |
| employee_hire_evaluation       |    20 | 100.0% | 100.0% |
| student_transcripts_tracking   |    20 | 100.0% | 100.0% |
| world_1                        |    20 | 100.0% | 100.0% |

### Strategy: self_correction
| Database | Count | Exact-Match | Execution Acc |
|----------|-------|-------------|---------------|
| car_1                          |    20 | 100.0% | 100.0% |
| concert_singer                 |    20 | 100.0% | 100.0% |
| employee_hire_evaluation       |    20 | 85.0% | 100.0% |
| student_transcripts_tracking   |    20 | 100.0% | 100.0% |
| world_1                        |    20 | 100.0% | 100.0% |

### Strategy: react_agent
| Database | Count | Exact-Match | Execution Acc |
|----------|-------|-------------|---------------|
| car_1                          |    20 | 100.0% | 100.0% |
| concert_singer                 |    20 | 100.0% | 100.0% |
| employee_hire_evaluation       |    20 | 100.0% | 100.0% |
| student_transcripts_tracking   |    20 | 100.0% | 100.0% |
| world_1                        |    20 | 100.0% | 100.0% |

---

## 4. Per-Question Details (Failures & Corrections)

### zero_shot — No Failures! All queries executed with 100% accuracy ✅

### few_shot — No Failures! All queries executed with 100% accuracy ✅

### cot_planner — No Failures! All queries executed with 100% accuracy ✅

### self_correction — No Failures! All queries executed with 100% accuracy ✅

### react_agent — No Failures! All queries executed with 100% accuracy ✅

---

## 5. Metric Definitions

- **Exact-Match (EM):** Predicted SQL matches gold SQL after AST normalization (case-insensitive, whitespace-invariant, alias-normalized via `sqlglot`).
- **Execution Accuracy (EX):** Both queries execute without error and return the same set of rows.
- **Avg Correction Iterations:** Mean number of LLM generation/correction passes per question. Single-pass strategies show 1.00; self-correction shows ≥1.00.
- **Avg Latency:** Wall-clock time per question in milliseconds including LLM calls, query planning, and execution.
