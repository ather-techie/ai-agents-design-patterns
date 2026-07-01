# Constitutional AI — control flow

```mermaid
flowchart TD
    Task([Task]) --> Draft[Generate draft]
    Draft --> CritLoop{"For each\nprinciple"}
    CritLoop --> Critique[Critique]
    Critique --> CritLoop
    CritLoop --> Revise["Revise draft\nagainst critiques"]
    Revise --> More{"More passes?"}
    More -->|yes| CritLoop
    More -->|no| Final([Final draft])
```

The critique–revision loop repeats up to `max_revisions` times. If `principles` is empty the
initial draft is returned immediately without any critique or revision steps.
