---
puppeteer:
  format: "A4"
  waitUntil: "networkidle0"
  printBackground: true

toc:
  depth_from: 1
  depth_to: 6
  ordered: true
---

# Sparse Embeddings v2.0


[TOC]

## The good old days: string matching, full-text search and BM25

Almost every app needs search. If you’ve attempted to implement it in your app, you may have discovered that what seems simple on the surface is a deeply challenging technical problem that has kept the brightest minds in computer science busy for decades.

In recent years, machine learning has given us semantic search, vastly improving the capability of search. However, the black-box nature of these tools can make them unsuited for some domains, like academic literature review. How can those domains take advantage of better search, while still having reproducible results?

A simple string comparison like the unix tool grep is the obvious and naive way to implement search. Of course, we quickly see that it doesn’t get anywhere near the results that users want. It may produce false positives like “car” matching “scar,” and false negatives like “goose” not matching “geese.” It also isn’t fast enough once you have a decently-sized corpus of data to search across.

Full-text search has been the gold standard for decades, with powerful capabilities for this built into databases like Postgres. Full-text search uses complex heuristics for better matching (such as pluralization) and indexing to keep search fast in large datasets. [Elastic](https://app.dealroom.co/companies/elastic?ref=blog.elicit.com) built a $10 billion company on the foundation of full-text search.

This remained the state of the art for almost all apps until the arrival of general-purpose ML-powered search.

[BM25](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf) is a classic **lexical retrieval** algorithm used in search engines and retrieval systems. Its job is to rank documents by how well they match a query based on **exact term overlap**, while also correcting for things like **document length** and **term frequency saturation**. It comes from the probabilistic relevance framework and is still widely used because it is fast, strong, and easy to combine with newer neural methods.

At a high level, BM25 says: a document should score higher if it contains the query terms, especially when those terms are **rare in the collection** and appear **multiple times** in the document. But the gain from repetition is not linear. Seeing a term 3 times is usually much more useful than seeing it once, but seeing it 30 times is not 30 times better. BM25 captures that behavior with a **saturating term-frequency factor**, and it also normalizes for document length so long documents are not unfairly favored just because they contain more words. 

A common BM25 scoring form is:

$$
\text{BM25}(q,d)=\sum_{t \in q} \text{IDF}(t)\cdot
\frac{f(t,d)\cdot (k_1+1)}
{f(t,d)+k_1\cdot \left(1-b+b\cdot \frac{|d|}{avgdl}\right)}
$$

where **(f(t,d))** is the number of times term (t) appears in document (d), **(|d|)** is the document length, **(avgdl)** is the average document length in the corpus, **IDF** gives higher weight to rare terms, and **(k_1)** and **(b)** are tunable parameters. In practice, **(k_1)** controls how quickly term frequency saturates, while **(b)** controls how strongly document length normalization is applied. 

So in practice, **how BM25 works** is fairly straightforward. First, you tokenize the documents and queries. Then you build an inverted index so that for each term you know which documents contain it. At search time, for each query term, BM25 looks up the matching documents, computes the per-term contribution using the formula above, sums the contributions, and returns the top-ranked documents. This makes BM25 very efficient at inference because it only needs to score documents that share terms with the query. That is one reason it remains a standard **first-stage retriever** in modern retrieval and RAG systems.

### Pros
- **Out-of-domain robustness**. BM25 does not need task-specific training, so it often keeps working reasonably well when the query distribution changes or when the data contains unusual names, entities, or product strings. That same advantage is one reason sparse lexical methods are still strong baselines in retrieval. Because BM25 does not need to understand the concept first. It only needs the same words to appear in the document and the query. With terms like *GeForce RTX 4080* or “*Illidan Stormrage*,” those tokens are very specific and often rare. If a document contains them, BM25 gives them a strong score because: rare terms get high importance. A token like *RTX* or *Illidan* appears in very few documents, so it is highly discriminative.
- **Long-document handling**. BM25 explicitly uses term frequency and document-length normalization, so it is naturally suited to ranking long passages and documents without having every long text dominate just because it has more words.
- **Interpretability**. Its score comes from visible term matches and weights, so you can usually explain why a result was retrieved: which words matched, how rare they are, and how often they appeared. Sparse methods are generally valued for this explicit lexical behavior as well.
- **Efficiency and low compute / memory cost**. BM25 works with an inverted index, which is extremely efficient for first-stage retrieval at scale. That is one of the core reasons keyword-based retrieval remains standard in production search.

### Cons

- **Tokenization and typos**. BM25 depends on exact token matching, so small changes in spelling or formatting can hurt retrieval. In the video, the example is *Geforce RTX4080* versus *Giforce*. Even though a human can see these are meant to refer to the same thing, BM25 may fail because the tokens are different. It does not naturally know that *Giforce* is just a misspelling of *GeForce*, or that *RTX4080* and *RTX 4080* should be treated similarly. This makes BM25 brittle when queries contain typos, inconsistent spacing, or tokenization differences.

- **Synonyms**. BM25 also struggles with different words that mean nearly the same thing. The example in the video is *Nuclear → Atomic*. If a user searches for *nuclear energy* but a relevant document mainly uses the word *atomic*, BM25 may miss it or rank it lower because there is little or no exact lexical overlap. The model does not understand that these two words can be semantically related. It only sees different surface forms.

- **Different meanings of the same word**. Another weakness is that BM25 cannot properly disambiguate polysemy, where the same word has different meanings in different contexts. *Nuclear bomb → Nuclear Family → Nuclear Performance*, is an example. All of these contain the word *nuclear*, but the meaning changes completely across contexts. BM25 still gives importance to the repeated keyword, even when the retrieved document is about the wrong sense of the word. So a search involving *nuclear bomb* could retrieve text about family structure or even something like *nuclear performance* just because the token overlaps.

- **Weak semantic understanding**. BM25 is weak at capturing semantic meaning beyond the exact words in the query. The example in the video is *Best gaming gpu*. A relevant document might talk about *top graphics card for gaming* or recommend a specific model like RTX 4080, but if it does not use the same words as the query, BM25 may not rank it highly. It does not infer that GPU, graphics card, and a specific gaming card model are closely related in meaning. This is where semantic models or embeddings usually do better.

## Query Expansion

One folk practice of systematic reviewers is to manually create a huge fanout of search terms. This makes sure every possible permutation is included.

<p align="center">
  <img src="https://framerusercontent.com/images/9k6BpMGn4hG4HlIdNBkzfddEqg.png?width=1012&height=286" alt="alt" width="500">
</p>

Query expansion, then, is just automating this process. A generic language model can be prompted to specify all the variations on each search term, and those can be fed into a regular full-text search.

This method is transparent and understandable, as the intermediate step is directly legible to humans. The downside is that it’s slow, and the search results are generally still much worse than a vector search.


## New Approaches to Sparse Embeddings

These systems all try to improve on plain **BM25** by keeping the benefits of **sparse retrieval**—fast inverted-index search and some level of interpretability—while adding more **context** or **semantic matching**. But they do it in different ways: some **learn term weights**, some **expand text into related terms**, and some combine **sparse + dense** retrieval in one model.

- **SPLADE** [[1.]](https://arxiv.org/pdf/2107.05720) [[2.]](https://arxiv.org/pdf/2109.10086) stands for **Sparse Lexical and Expansion Model**. It is a learned sparse retriever that uses a transformer plus sparsity regularization to assign weights to vocabulary terms, including terms that were not explicitly present in the input text. That makes it stronger than BM25 on semantic mismatch, while still producing sparse vectors that can be searched with an inverted index.

- **BM42** [[3.]](https://qdrant.tech/articles/bm42/?utm_source=chatgpt.com) is a lightweight sparse method introduced by Qdrant. Instead of training a full sparse retriever like SPLADE, it uses **transformer attention weights** together with **IDF-style lexical weighting** to build sparse representations. Qdrant presents it as a fast baseline for hybrid retrieval, especially when you want something cheaper than SPLADE.

- **BGE-M3** [[5]](https://arxiv.org/pdf/2402.03216) is a more general embedding model than the others here. Its key feature is that one model supports **dense retrieval**, **multi-vector retrieval**, and **sparse retrieval**, and it is designed to work across **100+ languages**. So it is attractive when you want one retriever family that can support multilingual and hybrid setups without maintaining separate models for every retrieval style.

- **ELSER** [[6]](https://www.elastic.co/search-labs/blog/introducing-elastic-learned-sparse-encoder-elser) is Elastic’s **Learned Sparse Encoder**. It generates sparse token-weight representations for semantic search and is designed to work out of the box in the Elastic stack. Elastic describes it as an **out-of-domain** model, meaning it is meant to work without task-specific fine-tuning in many practical search applications.

- **DeepCT** [[7]](https://arxiv.org/pdf/1910.10687) is an earlier learned sparse method that predicts **context-aware term importance**. Instead of doing explicit term expansion like SPLADE, it reweights the original terms based on context, so the inverted index reflects which words matter more in a passage or query. It was an important step toward neural first-stage sparse retrieval.


### SPLADE & SPLADE++
Because of the two-stage retrieval drawbacks, much work has been put into improving single-stage retrieval systems [[3]](https://www.pinecone.io/learn/splade/). A part of that is the research into more robust and learnable sparse embedding models — and one of the most performant models in this space is SPLADE.

The idea behind the Sparse Lexical and Expansion models is that a pretrained language model like BERT can identify connections between words/sub-words (called word-pieces or “terms” in this article) and use that knowledge to enhance our sparse vector embedding.

This works in two ways:
- adding new terms (**expansion**) and/or removing existing terms (**compression**) from the document/query (in other words, SPLADE learns which terms are important and which ones are missing).
- estimating a term importance (term weighting) for such words, similarly to tf-idf.

<p align="center">
  <img src="https://europe.naverlabs.com/wp-content/uploads/2021/07/img_3_brande.png" alt="alt" width="700">
</p>


The most significant advantage of SPLADE is not necessarily that it can do term expansion but instead that it can learn term expansions. Whereas SPLADE can use the best language models to learn term expansions and even tweak them based on the sentence context.

#### Masked Language Modeling Head
As mentioned, we will use BERT with an MLM head. If you’re familiar with BERT and MLM, then great — if not, let’s break it down. The MLM head works by taking an input sentence; again, let’s use `Orangutans are native to the rainforests of Indonesia and Malaysia`. We tokenize the text and then replace random tokens with a `[MASK]` token.

<p align="center">
  <img src="https://www.pinecone.io/_next/image/?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Fvr8gru94%2Fproduction%2Fc42f70bc4a63b5ff24ac0eb763af20bdfe6d45fc-1770x363.png&w=3840&q=75" alt="alt" width="600">
</p>

This masked token sequence is passed as input to BERT. At the other end, we give the original sentence to the MLM head. BERT and the MLM head are then optimized for predicting the original word/sub-word token that had been replaced by a `[MASK]` token.

<p align="center">
  <img src="https://cdn.sanity.io/images/vr8gru94/production/d64d431fb1b50ae9aa94b5cd85e1cdffe5eb7ca1-2318x1516.png" alt="alt" width="700">
</p>

#### MLM and Sparse Vectors
These `30522` probability distributions $w_{ij}$ act as an indicator of which words/tokens from the vocab are most important. The MLM head outputs these distributions for every token $i$ input to the model.

<p align="center">
  <img src="https://www.pinecone.io/_next/image/?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Fvr8gru94%2Fproduction%2F08212e88d27be2dfb661ccd7330c1236f0b5a47a-2435x1457.png&w=3840&q=75" alt="alt" width="700">
</p>

SPLADE takes all these distributions and aggregates them into a single distribution called the importance estimation $w_j$. This importance estimation is the sparse vector produced by SPLADE. We can combine all these probability distributions into a single distribution that tells us the relevance of every token in the vocab to our input sentence.

$$
w_j = \sum_{i \in t} \log(1 + \mathrm{ReLU}(w_{ij}))
$$

Where:

- $i \in t$: Every token $i$ in the input set of tokens $t$.
- $w_{ij}$: Every predicted weight for all tokens $j$ in the vocab $V$, for each token $i$.

This allows us to identify relevant tokens that do not exist within the input sentence. For example, if we mask the word `rainforest`, we may return high predictions $w_j$ for the words `jungle`, `land`, and `forest`. These words and their associated probabilities would then be represented in the SPLADE-built sparse vector.

This **learned query/document expansion** to include other relevant terms is a crucial advantage of SPLADE over traditional sparse methods. Helping us minimize the vocabulary mismatch problem based on learned relationships and term context.

As many transformer models are pretrained with MLM, there are a large number of models that have trained MLM head weights that can be used for later SPLADE fine-tuning.

#### Controlling sparsity with regularization constraints

To learn which words to keep in the representations, we propose simply adding regularization constraints on representations when training the model. We use the FLOPS regularizer—introduced by [Paria et al.](https://arxiv.org/abs/2004.05665) in an ICLR 2020 paper) [[4]](https://europe.naverlabs.com/blog/splade-a-sparse-bi-encoder-bert-based-model-achieves-effective-and-efficient-first-stage-ranking/). Simply speaking, this regularization will penalize words that are often predicted but which are not really useful for retrieving relevant documents. This is useful because, if too many words are added, the lists in the inverted index become too big and latency will increase. Using regularization avoids this by enabling the model to perform a sort of compression by only retaining the most relevant words from a document/query.

| Document                                                                                                                                                                        | SPLADE BOW rep                                                                                                                                                                                                                                                                                                                                         | New terms (expansion)                                              | Dropped terms (compression)                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| Binary (or base-2) a numeric system that only uses two digits—0 and 1. Computers operate in binary, meaning they store data and perform calculations using only zeros and ones. | (binary, 2.96), (base, 1.83), (computer, 1.57), (2, 1.42), (decimal, 1.29), (computers, 1.29), (system, 1.25), (digit, 1.24), (nu, 1.17), (0, 0.76), (zero, 0.74), (:, 0.56), (the, 0.53), (two, 0.49), (harmony, 0.48), (operate, 0.4), (computing, 0.31), (digits, 0.24), (neon, 0.19), (pi, 0.17), (##meric, 0.14), (pc, 0.13), (-, 0.06)           | harmony, computing, digit, :, the, pc, decimal, computer, pi, neon | —, perform, ##s, or, meaning, data, ), (, store, in, 1, ,, 'only', calculations, and, ., that, they, using, a, uses, ones |
| Option Types: Calls & Puts In the special language of options, contracts fall into two categories - Calls and Puts. A Call represents the right of the holder to buy stock.     | (option, 2.16), (call, 1.92), (type, 1.75), (contract, 1.58), (put, 1.33), (language, 1.24), (holder, 1.18), (right, 0.95), (putting, 0.89), (deal, 0.83), (puts, 0.71), (options, 0.66), (special, 0.61), (buy, 0.6), (stock, 0.53), (contracts, 0.36), (calls, 0.34), (stuff, 0.25), (called, 0.14), (two, 0.05), (specialized, 0.04), (types, 0.02) | type, contract, put, deal, called, specialized, putting, stuff     | into, in, of, :, the, -, and, ., a, categories, &, fall, to, ,, represents                                                |

#### SPLADE Fine Tuning
SPLADE is fine-tuned from a pretrained BERT-base model on a ranking dataset by adapting BERT from a masked-language-model encoder into a sparse retriever. Instead of predicting a class label, the model takes a query or a document as input and produces a sparse weighted vector over the whole vocabulary. This representation is built from BERT’s contextualized token embeddings and its masked-language-model head, so the model can assign importance not only to the original input terms but also to useful expansion terms. During fine-tuning, training examples consist of a query, a relevant document, and one or more non-relevant documents, including hard negatives and in-batch negatives. The model computes a score for each query-document pair using the dot product between their sparse vectors, and it is trained so that the relevant document receives a higher score than the negatives. At the same time, SPLADE applies sparsity regularization to both query and document representations, encouraging most vocabulary dimensions to remain zero so retrieval stays efficient. The overall objective therefore combines a ranking loss, which improves relevance, with a regularization term, which controls efficiency. In this way, SPLADE is fine-tuned end-to-end to learn sparse lexical and expansion-aware representations that work effectively for first-stage document retrieval.

#### SPLADE++ Fine Tuning
...

#### Where SPLADE Works Well and Less Well


It’s deterministic, for a given SPLADE model.

- It’s transparent. Like manual query expansion, SPLADE adds additional language model tokens (conceptually very similar to human-readable search terms) to the query which can be viewed and double-checked by the user if they wish.

- It’s obviously faster, more accurate, and requires less human effort than manual expansion.

So the SPLADE path is fast and close to semantic search quality, while still giving us the reproducibility and transparency that literature search users demand.

As a bonus, we can also train a custom SPLADE model on the particular domain we’re operating in. That means the query expansion would be smarter about, for example, particular jargon used within a domain like athletics, biomedicine, or law.

SPLADE is an excellent approach to minimizing the vocabulary mismatch problem commonly found in sparse vector methods. However, there are some drawbacks that we need to consider.

Compared to other sparse methods, retrieval with SPLADE is *slow*. There are three primary reasons for this:

1. The number of non-zero values in SPLADE query and document vectors is typically greater than in traditional sparse vectors, and sparse retrieval systems are not optimized for this.
2. The distribution of non-zero values deviates from the traditional distribution expected by the sparse retrieval systems, again causing slowdowns.
3. SPLADE vectors are not natively supported by *most* sparse retrieval systems. Meaning we must perform multiple pre and post-processing steps, weight discretization, etc.

Fortunately, there are solutions to all of these problems. For (1), the authors of SPLADE addressed this in a later version of the model that minimizes the number of query vector non-zero values [[2]](https://arxiv.org/pdf/2109.10086).

Reducing the number of query vector non-zero values was made possible through two steps. First, by first improving the performance of the SPLADE document encodings via a max pooling modification to the original pooling strategy:

$$
w_j = \max_{i \in t} \log(1 + \mathrm{ReLU}(w_{ij}))
$$

Second, by limiting term expansion to the document encodings *only*. Thanks to the improved document encoding performance, dropping query expansions still leaves us with better performance than the original SPLADE model.

Both (2) and (3) are solved using the Pinecone vector database. (2) is solved by Pinecone’s retrieval engine being designed from the ground up to be agnostic to data distribution. Pinecone allows real-valued sparse vectors — meaning SPLADE vectors are supported by default.


### BM42

#### Why BM25 is not relevant for modern RAG search
For the last 40 years, BM25 has served as the standard for search engines. It is a simple yet powerful algorithm that has been used by many search engines, including Google, Bing, and Yahoo. However, the use case of text retrieval has significantly shifted since the introduction of RAG. Many assumptions upon which BM25 was built are no longer valid. For example, the typical length of documents and queries vary significantly between traditional web search and modern RAG systems. As we can see, the term importance in the document heavily depends on the statistics within the document. Moreover, statistics works well if the document is long enough. Therefore, it is suitable for searching webpages, books, articles, etc.

However, would it work as well for modern search applications, such as RAG? Let’s see.

The typical length of a document in RAG is much shorter than that of web search. In fact, even if we are working with webpages and articles, we would prefer to split them into chunks so that 
1. Dense models can handle them and 
2. We can pinpoint the exact part of the document which is relevant to the query

As a result, the document size in RAG is small and fixed. That effectively renders the term importance in the document part of the BM25 formula useless. The term frequency in the document is always 0 or 1, and the relative length of the document is always 1. So, the only part of the BM25 formula that is still relevant for RAG is `IDF`.

#### Why SPLADE is not always the answer
Before discussing our new approach, let’s examine the current state-of-the-art alternative to BM25 - SPLADE.

The idea behind SPLADE is interesting—what if we let a smart, end-to-end trained model generate a bag-of-words representation of the text for us? It will assign all the weights to the tokens, so we won’t need to bother with statistics and hyperparameters. The documents are then represented as a sparse embedding, where each token is represented as an element of the sparse vector.

This performance, however, comes at a cost:
- **Inappropriate Tokenizer**: To incorporate transformers for this task, SPLADE models require using a standard transformer tokenizer. These tokenizers are not designed for retrieval tasks. For example, if the word is not in the (quite limited) vocabulary, it will be either split into subwords or replaced with a [UNK] token. This behavior works well for language modeling but is completely destructive for retrieval tasks.
- **Expensive Token Expansion**: In order to compensate the tokenization issues, SPLADE uses token expansion technique. This means that we generate a set of similar tokens for each token in the query. There are a few problems with this approach:
    1. **It is computationally and memory expensive**. We need to generate more values for each token in the document, which increases both the storage size and retrieval time.
    2. **It is not always clear where to stop with the token expansion.** The more tokens we generate, the more likely we are to get the relevant one. But simultaneously, the more tokens we generate, the more likely we are to get irrelevant results
    3. **Token expansion dilutes the interpretability of the search**. We can’t say which tokens were used in the document and which were generated by the token expansion.
    4. **Domain and Language Dependency**: SPLADE models are trained on specific corpora. This means that they are not always generalizable to new or rare domains. As they don’t use any statistics from the corpora, they cannot adapt to the new domain without fine-tuning.
    5. **Inference Time**: Additionally, currently available SPLADE models are quite big and slow. They usually require a GPU to make the inference in a reasonable time.

#### The best of both worlds
As previously mentioned, `IDF` is the most important part of the BM25 formula. As for the second part of the formula, the term importance within the document needs to be rethought. Since we can’t rely on the statistics within the document, we can try to use the semantics of the document instead. And semantics is what transformers are good at. 

The one particularly interesting output for us is the **attention matrix**.

<p align="center">
  <img src="https://qdrant.tech/articles_data/bm42/attention-matrix.png" alt="alt" width="400">
</p>

The attention matrix is a square matrix, where each row and column corresponds to the token in the input sequence. It represents the importance of each token in the input sequence for each other. Apart from regular text tokens, the transformer model also has a special token called `[CLS]`. This token represents the whole sequence in the classification tasks, which is exactly what we need. By looking at the attention row for the `[CLS]` token, we can get the importance of each token in the document for the whole document.

```
sentences = "Hello, World - is the starting point in most programming languages"

features = transformer.tokenize(sentences)

# ...

attentions = transformer.auto_model(**features, output_attentions=True).attentions

weights = torch.mean(attentions[-1][0,:,0], axis=0)                       
#                ▲               ▲  ▲   ▲                                 
#                │               │  │   └─── [CLS] token is the first one
#                │               │  └─────── First item of the batch         
#                │               └────────── Last transformer layer       
#                └────────────────────────── Average all 6 attention heads

for weight, token in zip(weights, tokens):
    print(f"{token}: {weight}")

# [CLS]       : 0.434 // Filter out the [CLS] token
# hello       : 0.039
# ,           : 0.039
# world       : 0.107 // <-- The most important token
# -           : 0.033
# is          : 0.024
# the         : 0.031
# starting    : 0.054
# point       : 0.028
# in          : 0.018
# most        : 0.016
# programming : 0.060 // <-- The third most important token
# languages   : 0.062 // <-- The second most important token
# [SEP]       : 0.047 // Filter out the [SEP] token
```

The resulting formula for the BM42 score would look like this:
$$
\text{score}(D,Q) = \sum_{i=1}^{N} \text{IDF}(q_i) \times \text{Attention}(\text{CLS}, q_i)
$$

Note that classical transformers have multiple attention heads, so we can get multiple importance vectors for the same document. The simplest way to combine them is to simply average them.

#### WordPiece retokenization
The final piece of the puzzle we need to solve is the tokenization issue. In order to get attention vectors, we need to use native transformer tokenization. But this tokenization is not suitable for the retrieval tasks.

Actually, the solution we came up with is quite simple. We reverse the tokenization process after we get the attention vectors. Transformers use WordPiece tokenization. In case it sees the word, which is not in the vocabulary, it splits it into subwords.Here is how that looks:

```
"unbelievable" -> ["un", "##believ", "##able"]
```

What can merge the subwords back into the words. Luckily, the subwords are marked with the ## prefix, so we can easily detect them. Since the attention weights are normalized, we can simply sum the attention weights of the subwords to get the attention weight of the word.

After that, we can apply the same traditional NLP techniques, as

- Removing of the stop-words
- Removing of the punctuation
- Lemmatization

In this way, we can significantly reduce the number of tokens, and therefore minimize the memory footprint of the sparse embeddings. We won’t simultaneously compromise the ability to match (almost) exact tokens.

| Trait | BM25 | SPLADE | BM42 |
|---|---|---|---|
| Interpretability | High ✅ | Ok 🆗 | High ✅ |
| Document Inference speed | Very high ✅ | Slow 🐌 | High ✅ |
| Query Inference speed | Very high ✅ | Slow 🐌 | Very high ✅ |
| Memory footprint | Low ✅ | High ❌ | Low ✅ |
| In-domain accuracy | Ok 🆗 | High ✅ | High ✅ |
| Out-of-domain accuracy | Ok 🆗 | Low ❌ | Ok 🆗 |
| Small documents accuracy | Low ❌ | High ✅ | High ✅ |
| Large documents accuracy | High ✅ | Low ❌ | Ok 🆗 |
| Unknown tokens handling | Yes ✅ | Bad ❌ | Yes ✅ |
| Multi-lingual support | Yes ✅ | No ❌ | Yes ✅ |
| Best Match | Yes ✅ | No ❌ | Yes ✅ |

#### Benchmarks
To prove the point further we have conducted some benchmarks to highlight the cases where BM42 outperforms BM25. For out experiments we choose [quora](https://huggingface.co/datasets/BeIR/quora) dataset, which represents a question-deduplication task. 

The typical example of the dataset is the following:
```
{"_id": "109", "text": "How GST affects the CAs and tax officers?"}
{"_id": "110", "text": "Why can't I do my homework?"}
{"_id": "111", "text": "How difficult is it get into RSI?"}
```

It has pretty short texts, there are not much of the statistics to rely on. After encoding with BM42, the average vector size is only 5.6 elements per document.

As a reference point, we use:

- BM25 with [tantivy](https://github.com/quickwit-oss/tantivy)
- the sparse vector BM25 implementation with the same preprocessing pipeline like for BM42: tokenization, stop-words removal, and lemmatization

| | BM25 (tantivy) | BM25 (Sparse) | BM42 |
|---|---|---|---|
| Recall @ 10 | **0.89** | 0.83 | 0.85 |

### BGE-M3

Instead of supporting only one retrieval style, M3-Embedding supports **three retrieval styles at once**: **dense retrieval**, **sparse / lexical retrieval**, and **multi-vector retrieval**. The central idea is that **one encoder produces representations that can be reused in different ways**, and then those different retrieval signals can be **combined during both inference and training**. So the model is not “three separate retrievers glued together.” It is more like **one multilingual encoder with three heads or three scoring views** over the same hidden states.

---

#### Architecture: one encoder, three retrieval functionalities

The paper starts from a text encoder and feeds a query ($q$) and a passage/document ($p$) through it, producing token-level hidden states:

$$
H_q \in \mathbb{R}^{N \times d}, \qquad H_p \in \mathbb{R}^{M \times d}
$$

where ($N$) and ($M$) are the token lengths of the query and passage, and ($d$) is the hidden size. 

From these same hidden states, the model derives **three different retrieval scores**. For **dense retrieval**, it uses the hidden state of the `[CLS]` token as a single embedding for the whole text:

$$
e_q = \mathrm{norm}(H_q[0]), \qquad e_p = \mathrm{norm}(H_p[0])
$$

Then similarity is just the inner product:

$$
s_{\text{dense}}(q,p) = \langle e_q, e_p \rangle
$$

This is the familiar **single-vector retrieval** setup: one vector for the query, one vector for the document. It is efficient and good at capturing overall semantic similarity. 

For lexical retrieval, the model predicts a **weight for each token**, meaning how important that token is for matching. For a token (t) at position (i), the paper computes:

$$
w_q^t = \mathrm{ReLU}(W_{\text{lex}}^\top H_q[i])
$$

and similarly for the passage. If a token appears multiple times, the model keeps the **maximum** weight for that token. Then the lexical matching score is the sum over terms shared by query and passage:

$$
s_{\text{lex}}(q,p) = \sum_{t \in q \cap p} w_q^t \cdot w_p^t
$$

This behaves like a neural version of lexical matching: it still depends on **overlapping terms**, but the term importance is learned from contextual embeddings instead of hand-designed statistics like BM25. 

For multi-vector retrieval, instead of compressing the whole text into one vector, the model keeps a vector for **every token**, after a learnable projection:

$$
E_q = \mathrm{norm}(W_{\text{mul}}^\top H_q), \qquad
E_p = \mathrm{norm}(W_{\text{mul}}^\top H_p)
$$

Then it uses **late interaction**, similar to **ColBERT**. For each query token, it finds the best-matching passage token, and averages those best matches:

$$
s_{\text{mul}}(q,p) = \frac{1}{N}\sum_{i=1}^{N}\max_{j=1}^{M} E_q[i]\cdot E_p[j]^\top
$$

This is more fine-grained than dense retrieval. It is especially useful when relevance depends on **specific local alignments** between query words and passage words. 

#### Why combining the three is powerful

Each retrieval function captures a different aspect of relevance.
- **Dense retrieval** is good at broad semantic similarity. It can match paraphrases and conceptually related text even when wording differs.
- **Sparse retrieval** is good at exact or near-exact lexical overlap. This helps when certain keywords matter a lot.
- **Multi-vector retrieval** is good at token-level fine-grained matching. It can notice that some parts of a document match the query very strongly even if the whole document is long or noisy.

So the model benefits from **diversity of evidence**. The paper explicitly argues that these are **heterogeneous predictors**, and that combining them can form a stronger signal than any one of them alone. 


#### How retrieval is combined at inference time

Once the three scores are available, the model can combine them into one final ranking score:

$$
s_{\text{rank}} = w_1 s_{\text{dense}} + w_2 s_{\text{lex}} + w_3 s_{\text{mul}}
$$

The weights ($w_1, w_2, w_3$) depend on the task. 

This means the system can work in a **hybrid retrieval pipeline**:

First, retrieve candidates with dense retrieval and/or sparse retrieval. Then optionally use multi-vector retrieval as a **reranker**, because it is more expensive. Finally, combine the scores.

This is important because **multi-vector scoring is powerful but costly**, while dense and sparse retrieval are better suited for first-stage candidate generation. The paper’s architecture therefore gives a practical tradeoff: **fast first-stage retrieval plus stronger re-ranking**. The diagram around Figure 2 shows this idea visually: the same M3 model produces dense, lexical, and interaction-based scores, and these are integrated together. 



<p align="center">
  <img src="https://figures.semanticscholar.org/677f89b61eff0f5ad3ae10c2b9208aaa16aa4239/4-Figure2-1.png" alt="alt" width="700">
</p>

#### Training objective before distillation and self-knowledge distillation

Each retrieval function has its own contrastive training objective. The model is trained to give a higher score to the positive passage ($p^*$) than to negatives ($P'$). The paper uses an **InfoNCE-style loss**:

So in principle, one could train all three objectives jointly:

$$
L = \frac{\lambda_1 L_{\text{dense}} + \lambda_2 L_{\text{lex}} + \lambda_3 L_{\text{mul}} + L_{\text{inter}}}{4}
$$

where ($L_{\text{inter}}$) comes from an integrated score, and ($\lambda_1,\lambda_2,\lambda_3$) are balancing weights. 

But the authors point out an important problem: **the objectives can conflict with each other.**

For example, dense retrieval prefers a globally smooth semantic space, while sparse retrieval focuses strongly on exact term overlap. Those pressures are not always aligned. If you simply optimize all losses together, one function may hurt another.

The paper’s solution is **self-knowledge distillation**, where the model first combines the three retrieval scores into a stronger **teacher signal**, and then uses that teacher to guide each individual retrieval function. 

They define an integrated score:

$$
s_{\text{inter}} = w_1 s_{\text{dense}} + w_2 s_{\text{lex}} + w_3 s_{\text{mul}}
$$

This is conceptually an **ensemble prediction**. Since dense, sparse, and multi-vector retrieval each capture different evidence, their combination should be a better estimate of true relevance. Instead of training each function only against hard labels like “this passage is positive, these are negative,” the model converts the integrated score into a soft distribution with softmax:

$$
p(s_{\text{inter}})
$$

Then each individual retrieval function is trained to imitate this distribution:

$$
L'** = -, p(s*{\text{inter}}),\log p(s_*)
$$

where ($s_*$) can be the dense, sparse, or multi-vector score. 

This is clever because the teacher is not an external model. The teacher is the model’s **own combined judgment**. That is why it is called **self-knowledge distillation**.

The distillation losses are averaged:

$$
L' = \frac{\lambda_1 L'*{\text{dense}} + \lambda_2 L'*{\text{lex}} + \lambda_3 L'_{\text{mul}}}{3}
$$

and the final loss is:

$$
L_{\text{final}} = \frac{L + L'}{2}
$$

So training has two simultaneous goals:

The model must still separate positives from negatives in the ordinary contrastive sense, but each retrieval function must also **agree with the ensemble teacher**. 

Without distillation, each function says, “I only care about my own objective.” With distillation, each function says, “I still optimize my own objective, but I should also move toward the consensus formed by all retrieval views.”

That consensus is often better because it contains:

* **semantic evidence** from dense retrieval,
* **lexical evidence** from sparse retrieval,
* **fine-grained interaction evidence** from multi-vector retrieval.

So the model learns not only from labels, but also from the richer structure of how the three retrieval functions jointly rank candidates. This is especially useful when the training objectives would otherwise pull the shared encoder in different directions. 

The ablation study supports this: removing self-knowledge distillation reduces performance across all functionalities, and the drop is especially large for sparse retrieval. On MIRACL, sparse retrieval falls from **53.9** to **36.7** without this distillation. Dense and multi-vector also drop. 


### ELSER
Elastic Learned Sparse EncodeR - or ELSER - is an NLP model trained by Elastic that enables you to perform semantic search by using sparse vector representation. Instead of literal matching on search terms, semantic search retrieves results based on the intent and the contextual meaning of a search query.

Elastic’s Learned Sparse Encoder uses text-expansion to breathe meaning into simple search queries and supercharge relevance. It captures the semantic relationships between words in the English language and based on them, it expands search queries to include relevant terms that are not present in the query. This model helps mitigate the [*vocabulary mismatch problem*](https://en.wikipedia.org/wiki/Vocabulary_mismatch#:~:text=Vocabulary%20mismatch%20is%20a%20common,study%20the%20vocabulary%20mismatch%20problem.): Even if the query terms are not present in the documents, Elastic Learned Sparse Encoder will return relevant documents if they exist.

#### ELSER performance results
As we discussed before, we use a subset of BEIR to evaluate our performance. The table below shows the performance of Elastic Learned Sparse Encoder compared to Elasticsearch's BM25 with an English analyzer broken down by the 12 data sets we evaluated. We have 10 wins, 1 draw, and 1 loss and an average improvement in NDCG@10 of 17%.

<p align="center">
  <img src="https://www.elastic.co/search-labs/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Fme0ej585%2Fsearch-labs-import-testing%2F36fcb82c7e9e22195e43a5fb93ff3a197cee9e8a-1440x271.png&w=1920&q=75" alt="alt" width="800">
</p>

In the following table, we compare our average performance to some other strong baselines. We've separated out the OpenAI results because they use a different subset of the BEIR suite. Specifically, they average over ArguAna, Climate FEVER, DBPedia, FEVER, FiQA, HotpotQA, NFCorpus, QuoraRetrieval, SciFact, TREC COVID and Touche.

<p align="center">
  <img src="https://www.elastic.co/search-labs/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Fme0ej585%2Fsearch-labs-import-testing%2F8ecb29edc0b4b1cd169320de06325d6fa0dd7c59-829x137.png&w=1920&q=75" alt="alt" width="700">
</p>

#### Exploring the training design space for ELSER

When training models for retrieval, there are two common paradigms: contrastive approaches and distillation approaches. We adopted the distillation approach because this was shown to be very effective for training SPLADE in this paper. The distillation approach is slightly different from the common paradigm, which informs the name, of shrinking a large model to a small, but almost as accurate, “copy.” Instead the idea is to distill the ranking information present in a cross-encoder architecture. This poses a small technical challenge: since the representation is different, it isn't immediately clear how one should mimic the behavior of the cross-encoder with the model being trained. The standard idea we used is to present both models with triplets of the form (query, relevant document, irrelevant document). The teacher model computes a score margin, namely $score(query,relevantdocument)−score(queryirrelevantdocument)$, and we train the student model to reproduce this score margin using MSE to penalize the errors it makes [[8]](https://www.elastic.co/search-labs/blog/elastic-learned-sparse-encoder-elser-retrieval-performance).


### DeepCT
...


# Bibliography
[[1]](https://arxiv.org/pdf/2107.05720) SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking
[[2]](https://arxiv.org/pdf/2109.10086) SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval
[[3]](https://www.pinecone.io/learn/splade/) SPLADE for Sparse Vector Search Explained
[[4]](https://europe.naverlabs.com/blog/splade-a-sparse-bi-encoder-bert-based-model-achieves-effective-and-efficient-first-stage-ranking/) SPLADE – a sparse bi-encoder BERT-based model achieves effective and efficient first-stage ranking
[[5]](https://qdrant.tech/articles/bm42/?utm_source=chatgpt.com) BM42: New Baseline for Hybrid Search
[[6]](https://arxiv.org/pdf/2402.03216) M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation
[[7]](https://www.elastic.co/search-labs/blog/introducing-elastic-learned-sparse-encoder-elser) Introducing Elastic Learned Sparse Encoder: Elastic’s AI model for semantic search
[[8]](https://www.elastic.co/search-labs/blog/elastic-learned-sparse-encoder-elser-retrieval-performance) Improving information retrieval in the Elastic Stack: Introducing Elastic Learned Sparse Encoder, our new retrieval model
[[9]](https://arxiv.org/pdf/1910.10687) Context-Aware Sentence/Passage Term Importance Estimation For First Stage Retrieval
[[10]](https://www.diva-portal.org/smash/get/diva2:1979031/FULLTEXT01.pdf) BM42 vs. Conventional Methods: Evaluating Next-Generation Hybrid Search Techniques for Information Retrieval
[[11]](https://qdrant.tech/articles/modern-sparse-neural-retrieval/#state-of-the-art-of-modern-sparse-neural-retrieval) Modern Sparse Neural Retrieval: From Theory to Practice
[[12]](https://elicit.com/blog/semantic-search/) From grep to SPLADE: A Journey Through Semantic Search


## The central efficiency lesson

**SPLADE is not usually faster or cheaper than BM25.** Its production advantage is that it can deliver much of the semantic-retrieval quality associated with dense models while retaining an **inverted-index architecture**.

A useful way to position the three methods is:

* **BM25:** minimum infrastructure and latency.
* **Dense retrieval:** predictable vector storage and fast approximate search, but usually requires a separate vector-search stack and neural query encoding.
* **SPLADE:** semantic term expansion inside a conventional lexical index, but with larger posting lists and more expensive query processing than BM25.

Therefore, SPLADE is preferable mainly when you need **better semantic recall than BM25**, but want to remain inside a sparse-search architecture or preserve lexical control and interpretability.

---

# 1. Separate three different costs

Students often hear “retrieval latency” as though it were one number. In a product, it consists of:

[
T_{\text{total}}
================

T_{\text{query encoding}}
+
T_{\text{index search}}
+
T_{\text{network/orchestration}}
]

This distinction changes the comparison considerably.

| Component                 |           BM25 |       SPLADE bi-encoder |    SPLADE document-only |                 Dense retrieval |
| ------------------------- | -------------: | ----------------------: | ----------------------: | ------------------------------: |
| Neural document encoding  |             No |            Yes, offline |            Yes, offline |                    Yes, offline |
| Neural query encoding     |             No |                     Yes |                      No |                     Usually yes |
| Search structure          | Inverted index |          Inverted index |          Inverted index |   ANN index, typically HNSW/IVF |
| Search mode               |  Usually exact | Usually exact or pruned | Usually exact or pruned |             Usually approximate |
| CPU-only serving          |      Very easy |    Possible, but costly |          Very practical | Possible, often less attractive |
| Exact lexical constraints |         Native |                  Native |                  Native | Requires extra filtering/search |

**Document-only SPLADE** deserves special attention. Documents are expanded offline, but user queries remain ordinary lexical queries. This eliminates the query-side Transformer and makes its serving profile much closer to BM25.

---

# 2. Retrieval speed: what experiments show

## BM25 remains the latency floor

An OpenSearch experiment on MS MARCO modelled retrieval latency as a fixed overhead plus a cost that grows with collection size:

[
T(N)=b+kN
]

The reported parameters were:

| System                      | Fixed overhead | Increment per 1M documents |
| --------------------------- | -------------: | -------------------------: |
| BM25                        |     **5.4 ms** |                **2.80 ms** |
| Document-only neural sparse |     **8.7 ms** |                **5.15 ms** |

Thus, document-only sparse retrieval was approximately **1.8× slower than BM25**, but remained in the same operational range. By contrast, bi-encoder sparse retrieval had a fixed overhead of **265.4 ms** and a search slope of **20.58 ms per million documents** in that setup, largely because of query-model inference and query expansion. ([OpenSearch][1])

For illustration, the fitted values imply:

| Collection size |     BM25 | Document-only sparse |
| --------------: | -------: | -------------------: |
|    1M documents |  ~8.2 ms |             ~13.9 ms |
|   10M documents | ~33.4 ms |             ~60.2 ms |
|  100M documents |  ~285 ms |              ~524 ms |

These are extrapolations from that experiment, not universal latency guarantees.

### Lecture takeaway

> **The inverted index does not automatically make SPLADE as fast as BM25.**
> SPLADE activates more query terms, so the engine traverses more and longer posting lists.

---

## Efficient SPLADE can approach BM25

The 2022 SPLADE efficiency study modified training and architecture using query-side L1 regularization, separate document/query encoders, FLOPS-aware middle training and smaller query encoders. Its strongest configurations achieved latency **within 4 ms of BM25**, while remaining within **10% MRR@10 of state-of-the-art single-stage neural retrievers** on in-domain evaluation. ([arXiv][2])

This is important because it shows that SPLADE efficiency is not fixed. It is a **trainable operating point**:

[
\text{Effectiveness} \longleftrightarrow
\text{number and document frequency of activated terms}
\longleftrightarrow
\text{latency}
]

A fully expanded, effectiveness-maximised SPLADE and an efficiency-trained SPLADE should not be discussed as though they were the same product.

---

## Unoptimised SPLADE can be dramatically slower

In another MS MARCO experiment using a conventional sparse retrieval implementation, mean response times were:

| Model        | MRR@10 | Recall@1000 | Mean response time |
| ------------ | -----: | ----------: | -----------------: |
| DeepImpact   |  0.327 |       0.948 |        **33.7 ms** |
| DeeperImpact |  0.373 |       0.968 |        **39.6 ms** |
| SPLADE       |  0.384 |       0.983 |       **476.7 ms** |

Here SPLADE gained roughly **0.011 MRR@10** over DeeperImpact, about a 3% relative improvement, but retrieval was approximately **12× slower**. ([arXiv][3])

The lesson is not that SPLADE always takes 477 ms. It is that **expansion density and retrieval-engine optimisation dominate SPLADE latency**.

---

# 3. Why short queries can be surprisingly expensive

A 2025 study evaluated sparse retrieval over collections ranging from tens of millions to billions of web-document titles. On its overloaded in-house search environment, it reported:

| Model           | Long queries, avg. 4.5 words | Short queries, avg. 1.5 words | Relative to BM25 |
| --------------- | ---------------------------: | ----------------------------: | ---------------: |
| BM25            |                   **1.02 s** |                    **0.75 s** |               1× |
| SPLADE          |                   **1.96 s** |                    **4.75 s** |    1.92× / 6.27× |
| Expanded-SPLADE |                   **1.20 s** |                    **2.39 s** |    1.27× / 3.15× |

The absolute latencies are not representative of normal interactive search—the authors intentionally overloaded the system—but the relative behaviour is instructive. Short lexical queries can cause SPLADE to add many expansion terms, creating a much wider disjunction than the original query. ([arXiv][4])

This makes SPLADE less attractive for workloads dominated by:

* one-word navigational queries;
* SKU or product-code lookup;
* person or company names;
* error codes;
* queries where the literal token is already sufficient.

For these workloads, BM25 often gives both the correct behaviour and the lowest cost.

---

# 4. Index size and memory

## Dense retrieval has a predictable lower bound

For a dense vector of dimension (d), storage before ANN overhead is approximately:

[
S_{\text{dense}} = N \times d \times b
]

where (b) is bytes per dimension.

For 8.8 million passages and 768 dimensions:

* float32: (8.8M \times 768 \times 4 \approx 27.0) GB;
* float16: approximately **13.5 GB**;
* int8: approximately **6.8 GB**.

An HNSW index also stores graph links and metadata, so its total footprint exceeds raw-vector storage.

Published MS MARCO results report roughly **25 GB** for several 110M-parameter dense retriever indexes, and **135 GB** for 7B–8B RepLLaMA representations. In the same comparison, BM25 occupied **2.6 GB**, while recent learned-sparse indexes remained below approximately **8 GB**. ([arXiv][5])

These numbers are model- and implementation-dependent, but they illustrate why sparse indexes can be attractive when dense vectors are high-dimensional or uncompressed.

---

## SPLADE is not necessarily smaller than BM25

Original SPLADE experiments demonstrated a highly regularised configuration with averages of only **18 non-zero document terms** and **6 non-zero query terms**, requiring less than **1.4 GB** for the 8.8M-passage MS MARCO index. ([piwowarski.fr][6])

However, stronger SPLADE variants generally activate more expansion terms. Other experiments report an original SPLADE index of **6.4 GB**, reduced to **2.8 GB** through hybrid thresholding, alongside a **3.1× retrieval speed-up** with only a small effectiveness reduction. ([UCSB Computer Science][7])

The correct conclusion is:

> SPLADE index size is **not an intrinsic constant**. It is controlled by document sparsity, quantisation, pruning and the chosen effectiveness target.

A dense index has a mostly fixed number of values per document. SPLADE has a **variable number of postings per document**, making its footprint less predictable but more tunable.

---

# 5. Query encoder cost

Both ordinary dense bi-encoders and full SPLADE models normally require a Transformer forward pass for every query.

This means that comparing only:

* Lucene inverted-index traversal for SPLADE; against
* HNSW traversal for dense retrieval

is incomplete.

You must also compare:

[
T_{\text{SPLADE encoder}} + T_{\text{inverted search}}
]

against:

[
T_{\text{dense encoder}} + T_{\text{ANN search}}
]

Dense ANN search can be only a few milliseconds once the vector exists. Similarly, SPLADE inverted-index search may be reasonably fast once the sparse query exists. In many deployments, **model inference is the fixed cost**, particularly for small collections.

That gives three practical cases:

### Small collection, low query volume

Search itself is cheap for every method, so the neural encoder dominates. **BM25 usually wins decisively on cost.**

### Large collection, moderate query volume

Index traversal becomes significant. SPLADE can be attractive because it avoids scanning or maintaining high-dimensional dense vectors while still providing semantic expansion.

### High query volume with batching

Dense retrieval can exploit GPU-batched encoding and ANN search very efficiently. SPLADE can also be GPU-accelerated, but conventional Lucene SPLADE retrieval is often CPU- and memory-bandwidth-bound.

A 2026 experimental GPU sparse system reported exact SPLADE retrieval on 8.8M MS MARCO passages at **1.27 ms/query and 787 QPS**, using batches of 500 on an H100. Its Lucene/Pyserini baseline required **298 ms/query** single-threaded. The GPU index occupied **8.5 GB**, although peak memory reached **44 GB** because of batched scoring buffers. This is promising, but it compares a highly batched GPU implementation against single-threaded CPU exact retrieval, so it should not be presented as a general 235× production advantage. ([arXiv][8])

---

# 6. Updates and document ingestion

For dynamic products, indexing cost matters as much as query speed.

## BM25

A new document only requires:

1. tokenisation;
2. term-frequency calculation;
3. insertion into posting lists.

No model inference is needed.

## SPLADE

Every new or modified document requires neural encoding before indexing. This creates:

* GPU or CPU inference cost;
* indexing delay;
* model-version management;
* potential full re-encoding when the SPLADE model changes.

## Dense retrieval

Dense systems have the same neural-encoding requirement and must also insert the vector into an ANN structure. HNSW supports incremental insertion, but continual updates can affect graph quality, memory use and operational predictability.

Therefore:

* **BM25 is best for extremely high-churn corpora.**
* SPLADE and dense retrieval are reasonable when documents are read much more often than they are written.
* SPLADE has an operational advantage when the organisation already runs Lucene/OpenSearch/Elasticsearch and does not want a separate vector index.

---

# 7. Where SPLADE brings a genuine resource advantage

## Scenario A: You already operate a large lexical-search platform

Suppose a company already has:

* Lucene or Elasticsearch clusters;
* sharding, replication and filtering infrastructure;
* access-control filters;
* field-level boosts;
* Boolean constraints;
* monitoring and index-lifecycle management.

SPLADE can reuse much of this architecture. Dense retrieval may require a vector engine, ANN tuning, graph rebuilding, vector-memory planning and a hybrid lexical path for exact filters.

Here, SPLADE’s advantage is not necessarily **lower benchmark latency**. It is **lower system complexity relative to introducing dense search**.

---

## Scenario B: Semantic recall is needed, but exact tokens remain important

Examples include:

* product search with brand names and attributes;
* legal retrieval with statutes and citations;
* technical support with error codes and component names;
* biomedical search with entities and terminology;
* enterprise search with acronyms and internal names.

SPLADE preserves token-level matching while adding learned expansions. A dense system may still need BM25 in parallel to protect exact-term recall. That creates two retrieval systems:

[
T_{\text{hybrid}}
\approx
\max(T_{\text{BM25}},T_{\text{dense}})
+
T_{\text{fusion}}
]

and two indexes to store and operate.

A well-tuned SPLADE index may replace this dual candidate-generation path with one index. This is the clearest potential **whole-system resource saving**, even when SPLADE is slower than BM25 alone.

---

## Scenario C: CPU-centric deployment

SPLADE search can run on established CPU inverted-index engines. Dense retrieval can also run on CPUs, but strong throughput at high vector dimensionality often benefits from SIMD-optimised ANN or GPUs.

Document-only SPLADE is particularly suitable when:

* query latency must be CPU-only;
* query traffic is too high to justify Transformer inference;
* document encoding can be done asynchronously offline;
* semantic expansion of documents is sufficient.

---

## Scenario D: Memory is constrained but some semantic matching is required

On MS MARCO, reported examples include:

* BM25: approximately **2.6 GB**;
* learned sparse: below approximately **8 GB** for recent configurations;
* conventional 768-dimensional dense indexes: approximately **25 GB**;
* large-model dense representations: up to **135 GB**. ([arXiv][5])

SPLADE may therefore offer a useful middle ground, particularly against unquantised dense vectors. This advantage can disappear when dense vectors are aggressively quantised or when SPLADE expansion is insufficiently pruned.

---

# 8. Cases where SPLADE is not the efficient choice

**Choose BM25** when literal matching is sufficient, the corpus changes constantly, the product needs very low tail latency, or the value of semantic expansion is small.

**Choose dense retrieval** when semantic similarity dominates, queries and documents have little lexical overlap, dense vectors can be heavily batched, multilingual or cross-modal representations are required, or approximate retrieval is acceptable.

**Choose SPLADE** when semantic expansion matters but you still need sparse-system properties: exact lexical signals, filtering, inspectable matching, CPU inverted indexes and compatibility with an existing search stack.

---

# A defensible lecture conclusion

You could express the comparison as:

> **BM25 optimises raw efficiency. Dense retrieval optimises semantic geometry. SPLADE optimises the compromise between semantic retrieval and classical search infrastructure.**

The experimental evidence does **not** support saying that SPLADE is generically faster than dense retrieval or BM25. It supports the narrower claims that:

1. **Standard SPLADE is normally slower and larger than BM25.**
2. **Efficiency-trained or document-only SPLADE can approach BM25-class latency**, with published configurations within 4 ms of BM25 or around 1.8× BM25 retrieval time. ([arXiv][2])
3. **SPLADE indexes can be much smaller than full-precision dense indexes**, although pruning and quantisation can change the ordering. ([arXiv][5])
4. **The main production advantage is architectural consolidation:** semantic expansion, lexical matching and standard inverted-index operations in one retrieval system.
5. **The advantage is greatest in read-heavy, lexically sensitive products already built on Lucene-class infrastructure.**

[1]: https://opensearch.org/blog/a-deep-dive-into-faster-semantic-sparse-retrieval-in-os-2-12/?utm_source=chatgpt.com "A deep dive into faster semantic sparse retrieval in ..."
[2]: https://arxiv.org/abs/2207.03834?utm_source=chatgpt.com "An Efficiency Study for SPLADE Models"
[3]: https://arxiv.org/pdf/2405.17093?utm_source=chatgpt.com "DeeperImpact: Optimizing Sparse Learned Index Structures"
[4]: https://arxiv.org/html/2511.22263v1 "Efficiency and Effectiveness of SPLADE Models on Billion-Scale Web Document Title"
[5]: https://arxiv.org/html/2504.10816v1?utm_source=chatgpt.com "Learned Sparse Retrieval with Causal Language Models"
[6]: https://www.piwowarski.fr/publication/formal_splade_2021-lwjxesk9/formal_splade_2021-LWJXESK9.pdf?utm_source=chatgpt.com "Sparse Lexical and Expansion Model for First Stage Ranking"
[7]: https://sites.cs.ucsb.edu/~tyang/papers/2023SIGIR-HT.pdf?utm_source=chatgpt.com "Representation Sparsification with Hybrid Thresholding for ..."
[8]: https://arxiv.org/abs/2606.26441?utm_source=chatgpt.com "GPUSparse: GPU-Accelerated Learned Sparse Retrieval with Parallel Inverted Indices"



https://github.com/naver/splade?utm_source=chatgpt.com