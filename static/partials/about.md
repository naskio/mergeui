MergeUI is an [open-source project](https://github.com/naskio/mergeui) that aims to provide a user-friendly interface
for discovering and analyzing merged large language models (Merged LLMs) from
the [Hugging Face Hub](https://huggingface.co/models?other=merge&sort=trending).
It is particularly focused on models that have been merged using [MergeKit](https://github.com/arcee-ai/mergekit).

## 📢 Introduction

Model merging is an innovative technique that combines two or more large language models (LLMs) into a single, more
capable model. It's a relatively new and experimental approach that enables the creation of state-of-the-art models in a
cost-effective manner, without the need for expensive GPU resources.
Remarkably, model merging has yielded impressive results, producing top-performing models on
the [Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard).

With MergeUI, researchers and developers can seamlessly browse, explore, and compare the available merged LLMs, gaining
valuable insights into their lineage, benchmark results, and other key details.
MergeUI makes it easy to:

- **Understand performance**: Explore the performance of each model in the family tree to understand its impact on the
  final model score and find out the best way to combine them and maximize performance.
- **Explore merge strategies**: Analyze the different methods used to merge each model in the family tree to identify
  its impact on the final model.
- **Check license permissiveness**: Ensure compatibility with your projects by checking the license of each model in the
  lineage.
- **Verify data provenance**: For each relationship, you can check Its provenance and how the data was extracted.

## 🥇 Merged LLM Leaderboard

MergeUI includes a leaderboard for merged models based on
the [Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard).

The **average score** is calculated based on the performance of the model on the following benchmarks:

- **AI2 Reasoning Challenge (ARC)** - Grade-School Science Questions (25-shot)
- **HellaSwag** - Commonsense Inference (10-shot)
- **MMLU** - Massive Multi-Task Language Understanding, knowledge on 57 domains (5-shot)
- **TruthfulQA** - Propensity to Produce Falsehoods (0-shot)
- **Winogrande** - Adversarial Winograd Schema Challenge (5-shot)
- **GSM8k** - Grade School Math Word Problems Solving Complex Mathematical Reasoning (5-shot)

Please refer to the [Open LLM Leaderboard Results](https://huggingface.co/datasets/open-llm-leaderboard/results) for
more details.

## 🤝 Contributing

MergeUI is a new project, and any contribution would make a difference! Whether you find a bug, have valuable feedback
or suggestions, or simply want to get involved, we welcome your help! Check out the project
on [GitHub](https://github.com/naskio/mergeui).