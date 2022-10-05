# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/evaluation.ipynb.

# %% auto 0
__all__ = ['HierarchicalEvaluation']

# %% ../nbs/evaluation.ipynb 2
from inspect import signature
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

# %% ../nbs/evaluation.ipynb 5
class HierarchicalEvaluation:    
    """Hierarchical Evaluation Class.
    
    You can use your own metrics to evaluate the performance of each level in the structure.
    The metrics receive `y` and `y_hat` as arguments and they are numpy arrays of size `(series, horizon)`.
    Consider, for example, the function `rmse` that calculates the root mean squared error.

    This class facilitates measurements across the hierarchy, defined by the `tags` list.
    See also the [aggregate method](https://nixtla.github.io/hierarchicalforecast/utils.html#aggregate).

    **Parameters:**<br>
    `evaluators`: functions with arguments `y`, `y_hat` (numpy arrays).<br>
    """
    def __init__(self, 
                 evaluators: List[Callable]):
        self.evaluators = evaluators

    def evaluate(self, 
                 Y_hat_df: pd.DataFrame,
                 Y_test_df: pd.DataFrame,
                 tags: Dict[str, np.ndarray],
                 Y_df: Optional[pd.DataFrame] = None,
                 benchmark: Optional[str] = None):
        """Hierarchical Evaluation Method.

        **Parameters:**<br>
        `Y_hat_df`: pd.DataFrame, Forecasts indexed by `'unique_id'` with column `'ds'` and models to evaluate.<br>
        `Y_test_df`:  pd.DataFrame, True values with columns `['ds', 'y']`.<br>
        `tags`: np.array, each str key is a level and its value contains tags associated to that level.<br>
        `Y_df`: pd.DataFrame, Training set of base time series with columns `['ds', 'y']` indexed by `unique_id`.<br>
        `benchmark`: str, If passed, evaluators are scaled by the error of this benchark.<br>

        **Returns:**<br>
        `evaluation`: pd.DataFrame with accuracy measurements across hierarchical levels.
        """
        drop_cols = ['ds', 'y'] if 'y' in Y_hat_df.columns else ['ds']
        h = len(Y_hat_df.loc[[Y_hat_df.index[0]]])
        model_names = Y_hat_df.drop(columns=drop_cols, axis=1).columns.to_list()
        fn_names = [fn.__name__ for fn in self.evaluators]
        has_y_insample = any(['y_insample' in signature(fn).parameters for fn in self.evaluators])
        if has_y_insample and Y_df is None:
            raise Exception('At least one evaluator needs y insample, please pass `Y_df`')
        if benchmark is not None:
            fn_names = [f'{fn_name}-scaled' for fn_name in fn_names]
        tags_ = {'Overall': np.concatenate(list(tags.values()))}
        tags_ = {**tags_, **tags}
        index = pd.MultiIndex.from_product([tags_.keys(), fn_names], names=['level', 'metric'])
        evaluation = pd.DataFrame(columns=model_names, index=index)
        for level, cats in tags_.items():
            Y_h_cats = Y_hat_df.loc[cats]
            y_test_cats = Y_test_df.loc[cats, 'y'].values.reshape(-1, h)
            if has_y_insample:
                y_insample = Y_df.pivot(columns='ds', values='y').loc[cats].values
            for i_fn, fn in enumerate(self.evaluators):
                if 'y_insample' in signature(fn).parameters:
                    kwargs = {'y_insample': y_insample}
                else:
                    kwargs = {}
                fn_name = fn_names[i_fn]
                for model in model_names:
                    loss = fn(y_test_cats, Y_h_cats[model].values.reshape(-1, h), **kwargs)
                    if benchmark is not None:
                        scale = fn(y_test_cats, Y_h_cats[benchmark].values.reshape(-1, h), **kwargs)
                        if np.isclose(scale, 0., atol=np.finfo(float).eps):
                            scale += np.finfo(float).eps
                            if np.isclose(scale, loss, atol=1e-8):
                                scale = 1.
                        loss /= scale
                    evaluation.loc[(level, fn_name), model] = loss
        return evaluation
