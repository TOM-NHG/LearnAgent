---
title: 'Specialized Smart Answer Formatter Agent for MRP Graph QA'
type: 'feature'
created: '2026-09-04'
status: 'done'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Running dual-round local LLM inference in GraphCypherQAChain (1st round for Cypher, 2nd round for answering) takes 20–35s and frequently halluncinates or truncates numbers.
**Approach:** Create a specialized `SmartAnswerFormatterAgent` that receives the user question and raw Neo4j records, leverages question keywords to determine intent, and deterministically renders structured Markdown tables, KPI cards, or concise executive takeaways in < 5ms without invoking a second LLM inference cycle.

## Boundaries & Constraints

**Always:**
- Extract numerical values, dates, and names directly from raw Neo4j query records without alterations or hallucinated numbers.
- Format currency fields as Vietnamese Dong (e.g. `150,000,000 VNĐ`) and percentages as `%`.
- Provide direct, context-driven headers matching user question keywords (e.g. Khoa Luật, Nợ học phí, Top 5).
- Allow seamless fallback or enhancement when Cloud API is active.

**Ask First:**
- Deprecating or removing existing LangChain default QA prompt fallback completely.

**Never:**
- Invoke a second CPU-heavy local Ollama call just to write generic conversational glue prose when query records are present.
- Hardcode rigid regular expressions that break on unexpected column names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tabular Multi-Record | List of dicts with >=2 rows (e.g. departments, students) | Markdown table with formatted numbers & summary footer | Fallback to key-value list if dict keys are non-uniform |
| Single KPI / Aggregation | Single record with sum/count/avg | Prominent KPI card with bolded metric and keyword context | Display `0 VNĐ` or `0` if None/null |
| Empty Graph Result | Empty list `[]` from Neo4j | Contextual friendly notification citing question entities and suggesting relaxation | Provide suggested related keywords |
| Cypher Error / Exception | Exception message string | Clean error advisory with Cypher inspection details | Graceful UI message without stack trace dump |

</frozen-after-approval>

## Code Map

- `d:/NHG/AgentofMRP/smart_formatter_agent.py` -- New dedicated agent class `SmartAnswerFormatterAgent`
- `d:/NHG/AgentofMRP/graph_qa.py` -- Interface providing direct Cypher generation & raw record execution without calling LLM QA chain
- `d:/NHG/AgentofMRP/main.py` -- Integrate `SmartAnswerFormatterAgent` into `/chat` endpoint pipeline
- `d:/NHG/AgentofMRP/tests/test_smart_formatter.py` -- Unit tests verifying zero-LLM formatting, KPI detection, and currency rendering

## Tasks & Acceptance

**Execution:**
- [ ] `smart_formatter_agent.py` -- Implement `SmartAnswerFormatterAgent` with intent detection, column localization, Markdown table generation, and KPI card synthesis.
- [ ] `graph_qa.py` -- Add helper function `execute_graph_query_raw(question: str)` returning generated Cypher and raw result records directly from Neo4j.
- [ ] `main.py` -- Update `/chat` route to use `execute_graph_query_raw` + `SmartAnswerFormatterAgent`, reducing response time from ~25s to ~3s.
- [ ] `tests/test_smart_formatter.py` -- Add unit tests covering single metric, multi-row table, empty results, and edge-case formatting.

**Acceptance Criteria:**
- Given a natural language question and Neo4j query records, when `SmartAnswerFormatterAgent.format()` is executed, then a structured Markdown response is generated in < 10ms matching question keywords.
- Given a single count/sum query, when processed, then values are formatted with `VNĐ` or numeric grouping without invoking a second LLM turn.

## Design Notes

The agent implements a 3-tier presentation pipeline:
1. `_detect_intent(question)`: classifies intent (`TABLE`, `KPI_SUMMARY`, `RANKING`, `STATUS_CHECK`).
2. `_localize_columns(keys)`: maps raw Cypher aliases (`ten_khoa`, `tong_no`, `so_sv`) into human-readable Vietnamese headers.
3. `_render_markdown(intent, records)`: builds clean GFM tables and highlighted callout cards.

## Verification

**Commands:**
- `.\venv\Scripts\python.exe -m pytest tests/test_smart_formatter.py` -- expected: All formatter unit tests pass.
- `.\venv\Scripts\python.exe -c "from smart_formatter_agent import SmartAnswerFormatterAgent; print('Agent imported successfully')"` -- expected: Clean import with 0 exit code.
