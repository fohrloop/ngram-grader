# ngram-grader

Tool for creating effort estimates for character unigrams, bigrams and trigrams for keyboard layout optimization.

## sort_app

Application for creating an ordered ngram table. Launch:

```
❯ uv run textual run app/sort_app/sort_app.py <ngram-order-file> <config-file-yml>
```

for example:

```
❯ uv run textual run app/sort_app/sort_app.py  somefile examples/keyseq_effort.yml
```

## viewer_app

Application for viewing an ordered ngram table. Launch:

```
❯ uv run textual run app/viewer/viewer_app.py <ngram-order-file> <config-file-yml>
```

for example:

```
❯ uv run textual run app/viewer/viewer_app.py somefile examples/keyseq_effort.yml
```