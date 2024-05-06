---
base_model:
- 152334H/miqu-1-70b-sf
language:
- en
- de
- fr
- es
- it
library_name: transformers
tags:
- mergekit
- merge
license: other
---
# miqu-1-120b

![image/jpeg](https://cdn-uploads.huggingface.co/production/uploads/6303ca537373aacccd85d8a7/LxO9j7OykuabKLYQHIodG.jpeg)

- EXL2: [2.4bpw](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-2.4bpw-h6-exl2) | [2.65bpw](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-2.65bpw-h6-exl2) | [3.0bpw](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-3.0bpw-h6-exl2) | [4.0bpw](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-4.0bpw-h6-exl2) | [5.0bpw](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-5.0bpw-h6-exl2)
- GGUF: [Q2_K-Q5_K_M](https://huggingface.co/LoneStriker/wolfram_miqu-1-120b-GGUF/) | [IQ3_XXS](https://huggingface.co/wolfram/miqu-1-120b-GGUF)

This is a 120b frankenmerge of [miqu-1-70b](https://huggingface.co/miqudev/miqu-1-70b) created by interleaving layers of [miqu-1-70b-sf](https://huggingface.co/152334H/miqu-1-70b-sf) with itself using [mergekit](https://github.com/cg123/mergekit).

Inspired by [Venus-120b-v1.2](https://huggingface.co/nsfwthrowitaway69/Venus-120b-v1.2), [MegaDolphin-120b](https://huggingface.co/cognitivecomputations/MegaDolphin-120b), and [goliath-120b](https://huggingface.co/alpindale/goliath-120b).

Thanks for the support, [CopilotKit](https://github.com/CopilotKit/CopilotKit) - the open-source platform for building in-app AI Copilots into any product, with any LLM model. Check out their GitHub.

Thanks for the EXL2 and GGUF quants, [Lone Striker](https://huggingface.co/LoneStriker)!

Also available: [miquliz-120b-v2.0](https://huggingface.co/wolfram/miquliz-120b-v2.0) – Miqu's younger, fresher sister; a new and improved Goliath-like merge of Miqu and lzlv.

## Review

u/SomeOddCodeGuy wrote on r/LocalLLaMA:

> I love this model. It's slow as Christmas but it's SO GOOD. You did great on this.
>
> But this model is close to getting me to shut down my ChatGPT 4 subscription lol. Between it, Deepseek and a couple others, I'm not sure I'll be using ChatGPT much anymore.
>
> Im using the Q8 at 16k, and I can't express how true it remains to its context. I might try to do some testing this weekend, but its great so far.
>
> I've been using your miqu-1 the past two days and its phenomenal. It understands everything I'm saying in ways only ChatGPT did. I've been purposefully getting more and more vague/relaxed in my speaking, and talking about the most inane stuff, and it just follows right along like a person would.
>
> Miqu-1 does ignore instructions a little. I tried to make a more sarcastic/insulting AI assistant to chat with, and specifically told it (multiple times after a few tries) to not apologize to me after, and it wouldn't stop. So if it made a jab like "Wow, great work spelling that word. Quite the whiz kid huh?", making fun of me for misspelling something, it would refuse to not follow up with "Seriously, though, sometimes misspellings happen" lol. But that's the only issue I've had with it.

(Note: All I did was merge this, though, so the credit mostly belongs to [Mistral AI](https://mistral.ai/) (giving proper attribution!) and the creators of [mergekit](https://github.com/arcee-ai/mergekit) as well as [Venus-120b-v1.2](https://huggingface.co/nsfwthrowitaway69/Venus-120b-v1.2) and [MegaDolphin-120b](https://huggingface.co/cognitivecomputations/MegaDolphin-120b) who inspired it.)

## Model Details

- Max Context: 32764 tokens (kept the weird number from the original/base model)
- Layers: 140

### Prompt template: Mistral

```
<s>[INST] {prompt} [/INST]
```

See also: [🐺🐦‍⬛ LLM Prompt Format Comparison/Test: Mixtral 8x7B Instruct with **17** different instruct templates : LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/18ljvxb/llm_prompt_format_comparisontest_mixtral_8x7b/)

## Merge Details

### Merge Method

This model was merged using the passthrough merge method.

### Models Merged

The following models were included in the merge:

- [152334H/miqu-1-70b-sf](https://huggingface.co/152334H/miqu-1-70b-sf)

### Configuration

The following YAML configuration was used to produce this model:

```yaml
dtype: float16
merge_method: passthrough
slices:
- sources:
  - layer_range: [0, 20]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [10, 30]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [20, 40]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [30, 50]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [40, 60]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [50, 70]
    model: 152334H/miqu-1-70b-sf
- sources:
  - layer_range: [60, 80]
    model: 152334H/miqu-1-70b-sf
```

## Credits & Special Thanks

- original (unreleased) model: [mistralai (Mistral AI_)](https://huggingface.co/mistralai)
  - ⭐⭐⭐ **[Use their newer, better, official models here!](https://console.mistral.ai/)** ⭐⭐⭐
- leaked model: [miqudev/miqu-1-70b](https://huggingface.co/miqudev/miqu-1-70b)
- f16 model: [152334H/miqu-1-70b-sf](https://huggingface.co/152334H/miqu-1-70b-sf)
- mergekit: [arcee-ai/mergekit: Tools for merging pretrained large language models.](https://github.com/arcee-ai/mergekit)
- mergekit_config.yml: [nsfwthrowitaway69/Venus-120b-v1.2](https://huggingface.co/nsfwthrowitaway69/Venus-120b-v1.2)

### Support

- [My Ko-fi page](https://ko-fi.com/wolframravenwolf) if you'd like to tip me to say thanks or request specific models to be tested or merged with priority. Also consider supporting your favorite model creators, quantizers, or frontend/backend devs if you can afford to do so. They deserve it!

## Disclaimer

*This model contains leaked weights and due to its content it should not be used by anyone.* 😜

But seriously:

### License

**What I *know*:** [Weights produced by a machine are not copyrightable](https://www.reddit.com/r/LocalLLaMA/comments/1amc080/psa_if_you_use_miqu_or_a_derivative_please_keep/kpmamte/) so there is no copyright owner who could grant permission or a license to use, or restrict usage, once you have acquired the files.

### Ethics

**What I *believe*:** All generative AI, including LLMs, only exists because it is trained mostly on human data (both public domain and copyright-protected, most likely acquired without express consent) and possibly synthetic data (which is ultimately derived from human data, too). It is only fair if something that is based on everyone's knowledge and data is also freely accessible to the public, the actual creators of the underlying content. Fair use, fair AI!