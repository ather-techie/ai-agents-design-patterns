# Self-Ask — control flow

```mermaid
flowchart LR
    Q([Question]) --> D["Decompose\nLLM → JSON array"]
    D --> SQ1[Sub-question 1]
    D --> SQ2[Sub-question 2]
    SQ1 --> A1[Answer 1]
    SQ2 --> A2["Answer 2\n(with A1 context)"]
    A1 & A2 --> Synth[Synthesize]
    Synth --> Final([Final Answer])
```

Three LLM call types: one decompose, one per sub-question (with prior answers in context), one synthesis.
The sub-questions are answered sequentially so each answer enriches the context for the next.
