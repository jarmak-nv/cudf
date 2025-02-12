# Copyright (c) 2021-2023, NVIDIA CORPORATION.

import numpy as np
import pandas as pd
import pytest

from dask.base import tokenize
from dask.dataframe import assert_eq
from dask.dataframe.methods import is_categorical_dtype

import cudf


def test_is_categorical_dispatch():
    assert is_categorical_dtype(pd.CategoricalDtype([1, 2, 3]))
    assert is_categorical_dtype(cudf.CategoricalDtype([1, 2, 3]))

    assert is_categorical_dtype(cudf.Series([1, 2, 3], dtype="category"))
    assert is_categorical_dtype(pd.Series([1, 2, 3], dtype="category"))

    assert is_categorical_dtype(pd.Index([1, 2, 3], dtype="category"))
    assert is_categorical_dtype(cudf.Index([1, 2, 3], dtype="category"))


def test_pyarrow_conversion_dispatch():
    from dask.dataframe.dispatch import (
        from_pyarrow_table_dispatch,
        to_pyarrow_table_dispatch,
    )

    df1 = cudf.DataFrame(np.random.randn(10, 3), columns=list("abc"))
    df2 = from_pyarrow_table_dispatch(df1, to_pyarrow_table_dispatch(df1))

    assert type(df1) == type(df2)
    assert_eq(df1, df2)


@pytest.mark.parametrize("index", [None, [1, 2] * 5])
def test_deterministic_tokenize(index):
    # Checks that `dask.base.normalize_token` correctly
    # dispatches to the logic defined in `backends.py`
    # (making `tokenize(<cudf-data>)` deterministic).
    df = cudf.DataFrame(
        {"A": range(10), "B": ["dog", "cat"] * 5, "C": range(10, 0, -1)},
        index=index,
    )

    # Matching data should produce the same token
    assert tokenize(df) == tokenize(df)
    assert tokenize(df.A) == tokenize(df.A)
    assert tokenize(df.index) == tokenize(df.index)
    assert tokenize(df) == tokenize(df.copy(deep=True))
    assert tokenize(df.A) == tokenize(df.A.copy(deep=True))
    assert tokenize(df.index) == tokenize(df.index.copy(deep=True))

    # Modifying a column element should change the token
    original_token = tokenize(df)
    original_token_a = tokenize(df.A)
    df.A.iloc[2] = 10
    assert original_token != tokenize(df)
    assert original_token_a != tokenize(df.A)

    # Modifying an index element should change the token
    original_token = tokenize(df)
    original_token_index = tokenize(df.index)
    new_index = df.index.values
    new_index[2] = 10
    df.index = new_index
    assert original_token != tokenize(df)
    assert original_token_index != tokenize(df.index)

    # Check MultiIndex case
    df2 = df.set_index(["B", "C"], drop=False)
    assert tokenize(df) != tokenize(df2)
    assert tokenize(df2) == tokenize(df2)


@pytest.mark.parametrize("preserve_index", [True, False])
def test_pyarrow_schema_dispatch(preserve_index):
    from dask.dataframe.dispatch import (
        pyarrow_schema_dispatch,
        to_pyarrow_table_dispatch,
    )

    df = cudf.DataFrame(np.random.randn(10, 3), columns=list("abc"))
    df["d"] = cudf.Series(["cat", "dog"] * 5)
    table = to_pyarrow_table_dispatch(df, preserve_index=preserve_index)
    schema = pyarrow_schema_dispatch(df, preserve_index=preserve_index)

    assert schema.equals(table.schema)
