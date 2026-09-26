# Project Data

This directory contains explicit project inputs and frozen datasets. It is
separate from `reports/`, which contains generated analytical evidence, and
from `outputs/baseline/`, which contains the current operational snapshot.

## `calendars/`

Contains calendar data and documentation for the MXMC implementation. The
verified 2026 dataset is explicit; projected calendar coverage must not be
treated as unlimited market-calendar certification.

## `synthetic/`

Contains deterministic known-truth research inputs. The current dataset is:

```text
data/synthetic/ftiie_ois_quotes_v1.csv
```

It is a frozen synthetic reference dataset, not observed market data. The
operational API accepts quote objects and a calendar directly; it does not
depend on the synthetic truth function.
