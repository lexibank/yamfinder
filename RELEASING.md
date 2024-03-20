# Releasing the dataset

```shell
cldfbench lexibank.makecldf lexibank_yamfinder.py --glottolog-version v5.0
```

```shell
cldf validate cldf
```

```shell
cldfbench cldfreadme lexibank_yamfinder.py
```

```shell
cldfbench zenodo lexibank_yamfinder.py
```

```shell
cldfbench cldfviz.map cldf --output map.svg --format svg --width 20 --height 10 --no-legend --with-ocean --padding-left 2 --padding-top 1 --padding-right 2 --padding-bottom 1 --language-labels --markersize 12
```
