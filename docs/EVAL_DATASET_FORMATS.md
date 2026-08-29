# Evaluation Dataset Formats

This guide describes the dataset inputs expected by Promptfoo and DeepEval, and recommends a neutral source format that can be exported to either framework.

JSONL is the safest format to generate: each line is one complete JSON test case. It is append-friendly, streamable, and supported by both tools.

## Promptfoo

Promptfoo test cases contain:

- `vars`: values inserted into the prompt template.
- `assert`: one or more grading rules.
- `description`: an optional human-readable case name.
- `metadata`: optional fields for filtering and analysis.

Example `promptfoo-dataset.jsonl`:

```jsonl
{"description":"Basic refund question","vars":{"input":"Can I return an item after 10 days?"},"assert":[{"type":"contains","value":"refund"}],"metadata":{"category":"refund","difficulty":"easy"}}
{"description":"Exact calculation","vars":{"input":"What is 5 × 6?"},"assert":[{"type":"equals","value":"30"}],"metadata":{"category":"math"}}
{"description":"Open-ended support answer","vars":{"input":"Help me cancel my account"},"assert":[{"type":"llm-rubric","value":"Clearly explains the cancellation process and does not invent policies"}]}
```

The prompt template must use the names defined inside `vars`:

```yaml
prompts:
  - "{{input}}"

tests: file://promptfoo-dataset.jsonl
```

Variable names are application-defined. For example, a test may provide `input`, `question`, `context`, or `customer_type`, as long as the prompt references the same names.

### Promptfoo CSV alternative

Promptfoo also supports CSV. Ordinary columns become prompt variables, while special `__expected` columns define assertions.

```csv
input,__expected,__description
"What is 5 × 6?","equals: 30","Basic multiplication"
"Can I get a refund?","llm-rubric: Correctly explains the refund policy","Refund policy"
```

Multiple assertions can be represented as `__expected1`, `__expected2`, and so on.

See the [Promptfoo test-case documentation](https://www.promptfoo.dev/docs/configuration/test-cases/).

## DeepEval

DeepEval calls source dataset entries **goldens**. A single-turn golden contains:

- `input`: required input sent to the application.
- `expected_output`: optional reference answer.
- `context`: optional list of ideal, static reference passages.
- `expected_tools`: optional list of tools the agent should call.
- `additional_metadata`: optional fields for filtering and analysis.

Example `deepeval-dataset.jsonl`:

```jsonl
{"input":"What is the refund period?","expected_output":"Customers may request a refund within 30 days.","context":["The company offers refunds within 30 days of purchase."],"additional_metadata":{"category":"refund","difficulty":"easy"}}
{"input":"What is 5 × 6?","expected_output":"30","additional_metadata":{"category":"math"}}
```

Do not normally generate these runtime fields in a golden:

- `actual_output`: the application response produced during the run.
- `retrieval_context`: the passages actually retrieved during the run.
- `tools_called`: the tools actually invoked during the run.

The distinction between the two context fields is important:

- `context` is the ideal or ground-truth information stored in the dataset.
- `retrieval_context` is what the application actually retrieved at runtime.

### DeepEval multi-turn datasets

Use conversational goldens for multi-turn tests:

```jsonl
{"scenario":"A frustrated customer wants a refund.","expected_outcome":"The agent explains eligibility and either completes the refund or escalates appropriately.","context":["Refunds are available within 30 days."]}
```

A DeepEval dataset may contain either single-turn goldens or multi-turn conversational goldens, but not both.

See the [DeepEval dataset documentation](https://deepeval.com/docs/evaluation-datasets).

## Recommended neutral generator format

If one generator must target both frameworks, generate a tool-neutral source dataset and write small exporters for Promptfoo and DeepEval.

Example `eval-source.jsonl`:

```jsonl
{"id":"refund-001","input":"Can I return an item after 10 days?","expected_output":"The item is eligible for return within the 30-day period.","reference_context":["Returns are accepted within 30 days."],"grading":{"type":"semantic","rubric":"The answer correctly applies the 30-day return policy without inventing conditions."},"expected_tools":[],"metadata":{"category":"refund","difficulty":"easy"}}
```

Recommended fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable identifier used to track regressions. |
| `input` | User question, task, or other application input. |
| `expected_output` | Optional reference answer. |
| `reference_context` | Optional ideal information needed to answer correctly. |
| `grading` | Exact, containment, semantic, or rubric-based success definition. |
| `expected_tools` | Optional tools and arguments the agent should use. |
| `metadata` | Category, difficulty, source, risk, split, and similar labels. |

### Export mapping

| Neutral field | Promptfoo | DeepEval |
| --- | --- | --- |
| `input` | `vars.input` | `input` |
| `expected_output` | Assertion `value` | `expected_output` |
| `reference_context` | `vars.context` | `context` |
| `grading` | `assert` | Metric or `GEval` configuration |
| `expected_tools` | Tool-call assertion | `expected_tools` |
| `metadata` | `metadata` | `additional_metadata` |

## Generation rules

1. Generate one independently understandable case per JSONL line.
2. Give every case a stable `id` and useful metadata.
3. Define success with an exact answer, reference context, expected tools, or a concise rubric.
4. Use exact-match grading only when wording or structure must truly be exact.
5. Use semantic or rubric grading for valid answers that can be phrased in several ways.
6. Keep source cases separate from runtime results so the same dataset can compare different prompts, models, and application versions.
7. Include normal, boundary, ambiguous, malformed, adversarial, and known-regression cases in proportion to product risk.

The dataset and the evaluator are separate concerns: the dataset supplies inputs and reference information, while Promptfoo assertions or DeepEval metrics determine how the resulting behavior is scored.
