# NLP Learning Path — KindleDict Project

## Why this project is perfect for learning NLP

You have what most learners don't:
- **610k real parallel sentence pairs** (OpenSubtitles NL-HU)
- **142k Dutch + 78k Hungarian dictionary entries** (Wiktionary)
- **A measurable task**: given a Dutch word, find the best Hungarian translation
- **A baseline to beat**: your current corpus lookup + DeepL pipeline

Every technique below can be tested against your existing dictionary quality scores.

---

## Learning Modules

### Module 1: Text Processing & Embeddings (Foundation)
**Goal**: Understand how machines represent words and sentences.
**Your task**: Build better word matching for your dictionary.

- [ ] Tokenization (BPE, WordPiece) — why "aangesproken" gets split
- [ ] Word embeddings (Word2Vec, FastText) — find similar Dutch words
- [ ] Sentence embeddings (Sentence-BERT) — match subtitle pairs better
- [ ] Hands-on: Use FastText to find Dutch words missing from your dictionary
- [ ] Hands-on: Use sentence embeddings to re-score OpenSubtitles translation quality

**Key libraries**: `gensim`, `sentence-transformers`, `fasttext`

### Module 2: Classical NLP for Dictionary Building
**Goal**: Extract structured knowledge from unstructured text.

- [ ] POS tagging & lemmatization (spaCy) — normalize Dutch verb forms
- [ ] Named Entity Recognition — filter out names from subtitle corpus
- [ ] TF-IDF & keyword extraction — find domain-specific terms
- [ ] Hands-on: Improve OpenSubtitles import by lemmatizing before matching
- [ ] Hands-on: Build a frequency-weighted translation scorer

**Key libraries**: `spacy` (nl_core_news_lg, hu_core_news_lg), `scikit-learn`

### Module 3: Running Local LLMs (The Interview Story)
**Goal**: Run and evaluate open-source LLMs on your translation task.

- [ ] Set up Ollama or llama.cpp on your Mac
- [ ] Run Mistral 7B / Phi-3 / Gemma 2 locally
- [ ] Prompt engineering: get the LLM to translate NL→HU with context
- [ ] Benchmark: compare local LLM translations vs DeepL vs corpus lookup
- [ ] Hands-on: Build a `translate_local_llm.py` script (like your translate_deepl.py)
- [ ] Cost analysis: tokens/sec, cost per 1000 translations vs DeepL API

**Key tools**: `ollama`, `llama-cpp-python`, `vllm` (if GPU available)

### Module 4: Fine-Tuning a Small LLM (The Core Interview Demo)
**Goal**: Train a model that's better at NL→HU than the base model — and cheaper than DeepL.

- [ ] Understand LoRA / QLoRA — parameter-efficient fine-tuning
- [ ] Prepare training data from your OpenSubtitles corpus
  - Format: instruction pairs ("Translate to Hungarian: {nl_sentence}" → "{hu_sentence}")
  - Split: train/val/test from your 610k pairs
- [ ] Fine-tune Mistral 7B or Phi-3 with QLoRA
- [ ] Evaluate: BLEU score, translation accuracy on held-out dictionary entries
- [ ] Compare: base model vs fine-tuned vs DeepL (quality + cost + speed)
- [ ] Hands-on: Integrate fine-tuned model into your dictionary pipeline

**Key libraries**: `transformers`, `peft`, `trl`, `datasets`, `bitsandbytes`
**Hardware**: Apple Silicon MPS or free Colab/Kaggle GPU

### Module 5: RAG for Dictionary Enrichment
**Goal**: Combine your corpus with an LLM for better translations.

- [ ] Vector databases (ChromaDB, FAISS) — index your subtitle pairs
- [ ] RAG pipeline: given a Dutch word, retrieve relevant subtitle pairs, then ask LLM to pick best translation
- [ ] Hands-on: Build a RAG-powered translation script
- [ ] Compare: RAG vs pure fine-tuning vs DeepL

**Key libraries**: `chromadb`, `faiss-cpu`, `langchain` (optional)

### Module 6: Evaluation & MLOps
**Goal**: Measure everything properly — this is what makes the interview story credible.

- [ ] BLEU, chrF, COMET scores for translation quality
- [ ] A/B comparison framework: rate translations blind
- [ ] Track experiments (MLflow or Weights & Biases)
- [ ] Model serving: wrap your fine-tuned model in an API
- [ ] Hands-on: Dashboard showing quality/cost/speed tradeoffs

**Key libraries**: `sacrebleu`, `comet`, `mlflow`, `wandb`

---

## The Interview Narrative

> "I have a hobby project — a multilingual e-reader dictionary builder. I had 610k
> Dutch-Hungarian subtitle pairs and a real translation quality problem. I fine-tuned
> a 7B parameter model with QLoRA on my parallel corpus. The fine-tuned model matches
> DeepL quality for this specific language pair at ~1/50th the cost per translation.
> I can show you the training pipeline, the evaluation metrics, and the model running
> live on my laptop."

This story demonstrates:
1. You understand the full ML lifecycle (data → training → evaluation → deployment)
2. You can identify when a small specialized model beats a large general one
3. You know how to measure and compare approaches objectively
4. You've done it on real data with a real use case, not a tutorial

---

## Suggested Order

Start with **Module 3** (local LLM) — it's the fastest to get running and most exciting.
Then **Module 1** (embeddings) — builds understanding for everything else.
Then **Module 4** (fine-tuning) — the core interview demo.
Modules 2, 5, 6 fill in as you go.

---

## Hardware Notes

- **Apple Silicon Mac**: Can run 7B models locally via Ollama (MLX backend). Fine-tuning possible with QLoRA on MPS, but slow. Use Colab/Kaggle for serious training.
- **Google Colab (free)**: T4 GPU, enough for QLoRA on 7B models
- **Kaggle**: 2x T4 GPUs free, 30h/week
- **Lambda / RunPod**: ~$0.50/hr for A100 if you need more

---

## Resources to Start

| Topic | Resource |
|-------|----------|
| Local LLMs | [Ollama](https://ollama.com) — one command install |
| Fine-tuning | [Unsloth](https://github.com/unslothai/unsloth) — 2x faster QLoRA |
| Embeddings | [Sentence-Transformers docs](https://www.sbert.net) |
| Translation eval | [SacreBLEU](https://github.com/mjpost/sacrebleu) |
| Dutch NLP | spaCy `nl_core_news_lg` model |
| Hungarian NLP | spaCy `hu_core_news_lg` model |
