# Scientific Paper Rhetorical Section Classifier

A tool to automatically classify sections of scientific research papers into their rhetorical roles (e.g., Introduction, Methodology, Results, Discussion).

Authors: Daniel Verdi, Jacob Aarup Dalsgaard, Roberta Sinatra

---

# 📊 Dataset & Methodology
* **Dataset:** [S2ORC: The Semantic Scholar Open Research Corpus](https://github.com/allenai/s2orc)

## Classification Labels

The model categorizes text into the following rhetorical roles, ranging from standard research sections to field-specific categories:

### Standard Research Labels
* **Introduction:** Sets the stage, introduces the topic, explains motivation, states the core problem or research questions, and provides a structural overview.
* **Literature Review:** Discusses previous work and state-of-the-art. Also serves as the main body for review papers without new findings.
* **Methods:** Details how the research was conducted, including study design, data, algorithms, and experimental setups.
* **Results:** Presentation of findings, data, and primary observations.
* **Discussion:** Interprets results and discusses broader implications and study limitations.
* **Conclusion:** Summarizes the paper, provides concluding remarks, and outlines future work.

### Field-Specific Labels
* **Development:** Used for core argumentative or theoretical sections that aren't empirical (common in Philosophy, Theoretical Math, or Law).
* **Case Report:** Specific to Medicine; a narrative of patient cases, profiles, unique events, or specific interventions and outcomes.

### Fallback Labels (Use Sparingly)
* **Something Else:** Administrative or miscellaneous sections that do not fit the functional labels above.
* **Ambiguous:** A last-resort label used only when it is impossible to determine the section's purpose from the provided context.