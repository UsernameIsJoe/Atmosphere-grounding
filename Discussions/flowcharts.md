# High-architecture flowcharts

Mermaid diagrams for slides. GitHub renders these automatically when viewing this file on github.com.

---

## Full pipeline (recommended for architecture slide)

```mermaid
flowchart TB
    subgraph DATA["0 · Data (Google Places API)"]
        P[Places · reviews ≤5 · photos ≤10<br/>paired by place_id]
    end

    subgraph GATE["1 · Pre-gates"]
        G[Image OK · Comment OK<br/>Review↔photo match → soft weight w]
    end

    subgraph LB["2 · Layer B — Image features (primary)"]
        VC[Visual ontology v1<br/>Grounding DINO · Mask2Former · SigLIP · metrics]
        PP[Per-image vectors → place profile]
        VC --> PP
    end

    subgraph LA["3 · Layer A — Text (LLM extract only)"]
        PA[Pass A: comment → lexicon + adj + nouns]
        PB[Pass B: comment + Layer B top-k<br/>confirm / carry-over / add features]
        PA --> PB
    end

    subgraph FEAT["4 · Image feature data"]
        IFD[Layer B place profile<br/>+ ontology-mapped text add-ons]
    end

    subgraph LEARN["5 · Co-occurrence learner"]
        CO[Lexicon/adj ↔ features<br/>soft weights · dual score tracks]
    end

    subgraph OUT["6 · Output & validation"]
        O[Strength per lexicon + ranked features<br/>Held-out places]
    end

    P --> G
    G --> VC
    G --> PA
    PP --> PB
    PP --> IFD
    PB --> IFD
    PA --> CO
    PB --> CO
    IFD --> CO
    CO --> O
```

**Slide legend (optional footer):** LLM = extract only · Learner = scientific association · Not caption-level grounding

---

## Compact one-slide version

```mermaid
flowchart LR
    A[Google reviews + photos<br/>same place] --> B[Pre-gates<br/>soft match weights]
    B --> C[Layer B<br/>DINO · Seg · SigLIP · metrics]
    B --> D[Pass A / B<br/>Ollama llama3.2]
    C --> E[Image feature data]
    D --> F[Lexicon + adj mentions]
    E --> G[Co-occurrence learner]
    F --> G
    G --> H[Lexicon strengths +<br/>ranked features]
    H --> I[Held-out validation]
```

---

## Research stages (pilot → LoRA)

```mermaid
flowchart LR
    S0[Stage 0 · Pilot<br/>Cambridge places<br/>co-occurrence tables] --> S1[Stage 1 · Corpus maps<br/>lexicon ↔ feature prominence]
    S1 --> S2[Stage 2 · LoRA<br/>predict atmospheres +<br/>ontology features from text]
```

---

## Final goal — LoRA distillation

```mermaid
flowchart LR
    A[Stages 0–1<br/>Places + Layer A/B] --> B[Co-occurrence tables<br/>lexicon ↔ features]
    B --> C[Structured targets<br/>profiles + ranks]
    C --> D[LoRA fine-tune<br/>small instruct LLM]
    D --> E[New text in →<br/>lexicon strengths +<br/>ranked features out]
    D --> F[Feature profile in →<br/>matching atmospheres out]
```

---

## Two layers (conceptual)

```mermaid
flowchart TB
    subgraph TEXT["Layer A — Text"]
        T[Reviews → LLM → lexicon + adj + nouns]
    end
    subgraph VIS["Layer B — Vision"]
        V[Photos → DINO / Seg / SigLIP / metrics → 49 families]
    end
    T --> L[Co-occurrence learner]
    V --> L
    L --> OUT[Strength per lexicon + ranked features]
```
