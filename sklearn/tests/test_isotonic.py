import warnings
import numpy as np
import pickle
import copy

import pytest

from sklearn.isotonic import (check_increasing, isotonic_regression,
                              IsotonicRegression, _make_unique)

from sklearn.utils.validation import check_array
from sklearn.utils._testing import (assert_raises, assert_array_equal,
                                    assert_array_almost_equal,
                                    assert_warns_message, assert_no_warnings)
from sklearn.utils import shuffle, check_random_state

from scipy.special import expit


def test_permutation_invariance():
    # check that fit is permutation invariant.
    # regression test of missing sorting of sample-weights
    ir = IsotonicRegression()
    x = [1, 2, 3, 4, 5, 6, 7]
    y = [1, 41, 51, 1, 2, 5, 24]
    sample_weight = [1, 2, 3, 4, 5, 6, 7]
    x_s, y_s, sample_weight_s = shuffle(x, y, sample_weight, random_state=0)
    y_transformed = ir.fit_transform(x, y, sample_weight=sample_weight)
    y_transformed_s = \
        ir.fit(x_s, y_s, sample_weight=sample_weight_s).transform(x)

    assert_array_equal(y_transformed, y_transformed_s)


def test_check_increasing_small_number_of_samples():
    x = [0, 1, 2]
    y = [1, 1.1, 1.05]

    is_increasing = assert_no_warnings(check_increasing, x, y)
    assert is_increasing


def test_check_increasing_up():
    x = [0, 1, 2, 3, 4, 5]
    y = [0, 1.5, 2.77, 8.99, 8.99, 50]

    # Check that we got increasing=True and no warnings
    is_increasing = assert_no_warnings(check_increasing, x, y)
    assert is_increasing


def test_check_increasing_up_extreme():
    x = [0, 1, 2, 3, 4, 5]
    y = [0, 1, 2, 3, 4, 5]

    # Check that we got increasing=True and no warnings
    is_increasing = assert_no_warnings(check_increasing, x, y)
    assert is_increasing


def test_check_increasing_down():
    x = [0, 1, 2, 3, 4, 5]
    y = [0, -1.5, -2.77, -8.99, -8.99, -50]

    # Check that we got increasing=False and no warnings
    is_increasing = assert_no_warnings(check_increasing, x, y)
    assert not is_increasing


def test_check_increasing_down_extreme():
    x = [0, 1, 2, 3, 4, 5]
    y = [0, -1, -2, -3, -4, -5]

    # Check that we got increasing=False and no warnings
    is_increasing = assert_no_warnings(check_increasing, x, y)
    assert not is_increasing


def test_check_ci_warn():
    x = [0, 1, 2, 3, 4, 5]
    y = [0, -1, 2, -3, 4, -5]

    # Check that we got increasing=False and CI interval warning
    is_increasing = assert_warns_message(UserWarning, "interval",
                                         check_increasing,
                                         x, y)

    assert not is_increasing


def test_isotonic_regression():
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    y_ = np.array([3, 6, 6, 8, 8, 8, 10])
    assert_array_equal(y_, isotonic_regression(y))

    y = np.array([10, 0, 2])
    y_ = np.array([4, 4, 4])
    assert_array_equal(y_, isotonic_regression(y))

    x = np.arange(len(y))
    ir = IsotonicRegression(y_min=0., y_max=1.)
    ir.fit(x, y)
    assert_array_equal(ir.fit(x, y).transform(x), ir.fit_transform(x, y))
    assert_array_equal(ir.transform(x), ir.predict(x))

    # check that it is immune to permutation
    perm = np.random.permutation(len(y))
    ir = IsotonicRegression(y_min=0., y_max=1.)
    assert_array_equal(ir.fit_transform(x[perm], y[perm]),
                       ir.fit_transform(x, y)[perm])
    assert_array_equal(ir.transform(x[perm]), ir.transform(x)[perm])

    # check we don't crash when all x are equal:
    ir = IsotonicRegression()
    assert_array_equal(ir.fit_transform(np.ones(len(x)), y), np.mean(y))


def test_isotonic_regression_ties_min():
    # Setup examples with ties on minimum
    x = [1, 1, 2, 3, 4, 5]
    y = [1, 2, 3, 4, 5, 6]
    y_true = [1.5, 1.5, 3, 4, 5, 6]

    # Check that we get identical results for fit/transform and fit_transform
    ir = IsotonicRegression()
    ir.fit(x, y)
    assert_array_equal(ir.fit(x, y).transform(x), ir.fit_transform(x, y))
    assert_array_equal(y_true, ir.fit_transform(x, y))


def test_isotonic_regression_ties_max():
    # Setup examples with ties on maximum
    x = [1, 2, 3, 4, 5, 5]
    y = [1, 2, 3, 4, 5, 6]
    y_true = [1, 2, 3, 4, 5.5, 5.5]

    # Check that we get identical results for fit/transform and fit_transform
    ir = IsotonicRegression()
    ir.fit(x, y)
    assert_array_equal(ir.fit(x, y).transform(x), ir.fit_transform(x, y))
    assert_array_equal(y_true, ir.fit_transform(x, y))


def test_isotonic_regression_ties_secondary_():
    """
    Test isotonic regression fit, transform  and fit_transform
    against the "secondary" ties method and "pituitary" data from R
     "isotone" package, as detailed in: J. d. Leeuw, K. Hornik, P. Mair,
     Isotone Optimization in R: Pool-Adjacent-Violators Algorithm
    (PAVA) and Active Set Methods

    Set values based on pituitary example and
     the following R command detailed in the paper above:
    > library("isotone")
    > data("pituitary")
    > res1 <- gpava(pituitary$age, pituitary$size, ties="secondary")
    > res1$x

    `isotone` version: 1.0-2, 2014-09-07
    R version: R version 3.1.1 (2014-07-10)
    """
    x = [8, 8, 8, 10, 10, 10, 12, 12, 12, 14, 14]
    y = [21, 23.5, 23, 24, 21, 25, 21.5, 22, 19, 23.5, 25]
    y_true = [22.22222, 22.22222, 22.22222, 22.22222, 22.22222, 22.22222,
              22.22222, 22.22222, 22.22222, 24.25, 24.25]

    # Check fit, transform and fit_transform
    ir = IsotonicRegression()
    ir.fit(x, y)
    assert_array_almost_equal(ir.transform(x), y_true, 4)
    assert_array_almost_equal(ir.fit_transform(x, y), y_true, 4)


def test_isotonic_regression_with_ties_in_differently_sized_groups():
    """
    Non-regression test to handle issue 9432:
    https://github.com/scikit-learn/scikit-learn/issues/9432

    Compare against output in R:
    > library("isotone")
    > x <- c(0, 1, 1, 2, 3, 4)
    > y <- c(0, 0, 1, 0, 0, 1)
    > res1 <- gpava(x, y, ties="secondary")
    > res1$x

    `isotone` version: 1.1-0, 2015-07-24
    R version: R version 3.3.2 (2016-10-31)
    """
    x = np.array([0, 1, 1, 2, 3, 4])
    y = np.array([0, 0, 1, 0, 0, 1])
    y_true = np.array([0., 0.25, 0.25, 0.25, 0.25, 1.])
    ir = IsotonicRegression()
    ir.fit(x, y)
    assert_array_almost_equal(ir.transform(x), y_true)
    assert_array_almost_equal(ir.fit_transform(x, y), y_true)


def test_isotonic_regression_reversed():
    y = np.array([10, 9, 10, 7, 6, 6.1, 5])
    y_ = IsotonicRegression(increasing=False).fit_transform(
        np.arange(len(y)), y)
    assert_array_equal(np.ones(y_[:-1].shape), ((y_[:-1] - y_[1:]) >= 0))


def test_isotonic_regression_auto_decreasing():
    # Set y and x for decreasing
    y = np.array([10, 9, 10, 7, 6, 6.1, 5])
    x = np.arange(len(y))

    # Create model and fit_transform
    ir = IsotonicRegression(increasing='auto')
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        y_ = ir.fit_transform(x, y)
        # work-around for pearson divide warnings in scipy <= 0.17.0
        assert all(["invalid value encountered in "
                    in str(warn.message) for warn in w])

    # Check that relationship decreases
    is_increasing = y_[0] < y_[-1]
    assert not is_increasing


def test_isotonic_regression_auto_increasing():
    # Set y and x for decreasing
    y = np.array([5, 6.1, 6, 7, 10, 9, 10])
    x = np.arange(len(y))

    # Create model and fit_transform
    ir = IsotonicRegression(increasing='auto')
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        y_ = ir.fit_transform(x, y)
        # work-around for pearson divide warnings in scipy <= 0.17.0
        assert all(["invalid value encountered in "
                    in str(warn.message) for warn in w])

    # Check that relationship increases
    is_increasing = y_[0] < y_[-1]
    assert is_increasing


def test_assert_raises_exceptions():
    ir = IsotonicRegression()
    rng = np.random.RandomState(42)
    assert_raises(ValueError, ir.fit, [0, 1, 2], [5, 7, 3], [0.1, 0.6])
    assert_raises(ValueError, ir.fit, [0, 1, 2], [5, 7])
    assert_raises(ValueError, ir.fit, rng.randn(3, 10), [0, 1, 2])
    assert_raises(ValueError, ir.transform, rng.randn(3, 10))


def test_isotonic_sample_weight_parameter_default_value():
    # check if default value of sample_weight parameter is one
    ir = IsotonicRegression()
    # random test data
    rng = np.random.RandomState(42)
    n = 100
    x = np.arange(n)
    y = rng.randint(-50, 50, size=(n,)) + 50. * np.log(1 + np.arange(n))
    # check if value is correctly used
    weights = np.ones(n)
    y_set_value = ir.fit_transform(x, y, sample_weight=weights)
    y_default_value = ir.fit_transform(x, y)

    assert_array_equal(y_set_value, y_default_value)


def test_isotonic_min_max_boundaries():
    # check if min value is used correctly
    ir = IsotonicRegression(y_min=2, y_max=4)
    n = 6
    x = np.arange(n)
    y = np.arange(n)
    y_test = [2, 2, 2, 3, 4, 4]
    y_result = np.round(ir.fit_transform(x, y))
    assert_array_equal(y_result, y_test)


def test_isotonic_sample_weight():
    ir = IsotonicRegression()
    x = [1, 2, 3, 4, 5, 6, 7]
    y = [1, 41, 51, 1, 2, 5, 24]
    sample_weight = [1, 2, 3, 4, 5, 6, 7]
    expected_y = [1, 13.95, 13.95, 13.95, 13.95, 13.95, 24]
    received_y = ir.fit_transform(x, y, sample_weight=sample_weight)

    assert_array_equal(expected_y, received_y)


def test_isotonic_regression_oob_raise():
    # Set y and x
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="raise")
    ir.fit(x, y)

    # Check that an exception is thrown
    assert_raises(ValueError, ir.predict, [min(x) - 10, max(x) + 10])


def test_isotonic_regression_oob_clip():
    # Set y and x
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="clip")
    ir.fit(x, y)

    # Predict from  training and test x and check that min/max match.
    y1 = ir.predict([min(x) - 10, max(x) + 10])
    y2 = ir.predict(x)
    assert max(y1) == max(y2)
    assert min(y1) == min(y2)


def test_isotonic_regression_oob_nan():
    # Set y and x
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="nan")
    ir.fit(x, y)

    # Predict from  training and test x and check that we have two NaNs.
    y1 = ir.predict([min(x) - 10, max(x) + 10])
    assert sum(np.isnan(y1)) == 2


def test_isotonic_regression_oob_bad():
    # Set y and x
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="xyz")

    # Make sure that we throw an error for bad out_of_bounds value
    assert_raises(ValueError, ir.fit, x, y)


def test_isotonic_regression_oob_bad_after():
    # Set y and x
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="raise")

    # Make sure that we throw an error for bad out_of_bounds value in transform
    ir.fit(x, y)
    ir.out_of_bounds = "xyz"
    assert_raises(ValueError, ir.transform, x)


def test_isotonic_regression_pickle():
    y = np.array([3, 7, 5, 9, 8, 7, 10])
    x = np.arange(len(y))

    # Create model and fit
    ir = IsotonicRegression(increasing='auto', out_of_bounds="clip")
    ir.fit(x, y)

    ir_ser = pickle.dumps(ir, pickle.HIGHEST_PROTOCOL)
    ir2 = pickle.loads(ir_ser)
    np.testing.assert_array_equal(ir.predict(x), ir2.predict(x))


def test_isotonic_duplicate_min_entry():
    x = [0, 0, 1]
    y = [0, 0, 1]

    ir = IsotonicRegression(increasing=True, out_of_bounds="clip")
    ir.fit(x, y)
    all_predictions_finite = np.all(np.isfinite(ir.predict(x)))
    assert all_predictions_finite


def test_isotonic_ymin_ymax():
    # Test from @NelleV's issue:
    # https://github.com/scikit-learn/scikit-learn/issues/6921
    x = np.array([1.263, 1.318, -0.572, 0.307, -0.707, -0.176, -1.599, 1.059,
                  1.396, 1.906, 0.210, 0.028, -0.081, 0.444, 0.018, -0.377,
                  -0.896, -0.377, -1.327, 0.180])
    y = isotonic_regression(x, y_min=0., y_max=0.1)

    assert np.all(y >= 0)
    assert np.all(y <= 0.1)

    # Also test decreasing case since the logic there is different
    y = isotonic_regression(x, y_min=0., y_max=0.1, increasing=False)

    assert np.all(y >= 0)
    assert np.all(y <= 0.1)

    # Finally, test with only one bound
    y = isotonic_regression(x, y_min=0., increasing=False)

    assert np.all(y >= 0)


def test_isotonic_zero_weight_loop():
    # Test from @ogrisel's issue:
    # https://github.com/scikit-learn/scikit-learn/issues/4297

    # Get deterministic RNG with seed
    rng = np.random.RandomState(42)

    # Create regression and samples
    regression = IsotonicRegression()
    n_samples = 50
    x = np.linspace(-3, 3, n_samples)
    y = x + rng.uniform(size=n_samples)

    # Get some random weights and zero out
    w = rng.uniform(size=n_samples)
    w[5:8] = 0
    regression.fit(x, y, sample_weight=w)

    # This will hang in failure case.
    regression.fit(x, y, sample_weight=w)


def test_fast_predict():
    # test that the faster prediction change doesn't
    # affect out-of-sample predictions:
    # https://github.com/scikit-learn/scikit-learn/pull/6206
    rng = np.random.RandomState(123)
    n_samples = 10 ** 3
    # X values over the -10,10 range
    X_train = 20.0 * rng.rand(n_samples) - 10
    y_train = np.less(rng.rand(n_samples),
                      expit(X_train)).astype('int64').astype('float64')

    weights = rng.rand(n_samples)
    # we also want to test that everything still works when some weights are 0
    weights[rng.rand(n_samples) < 0.1] = 0

    slow_model = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
    fast_model = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")

    # Build interpolation function with ALL input data, not just the
    # non-redundant subset. The following 2 lines are taken from the
    # .fit() method, without removing unnecessary points
    X_train_fit, y_train_fit = slow_model._build_y(X_train, y_train,
                                                   sample_weight=weights,
                                                   trim_duplicates=False)
    slow_model._build_f(X_train_fit, y_train_fit)

    # fit with just the necessary data
    fast_model.fit(X_train, y_train, sample_weight=weights)

    X_test = 20.0 * rng.rand(n_samples) - 10
    y_pred_slow = slow_model.predict(X_test)
    y_pred_fast = fast_model.predict(X_test)

    assert_array_equal(y_pred_slow, y_pred_fast)


def test_isotonic_copy_before_fit():
    # https://github.com/scikit-learn/scikit-learn/issues/6628
    ir = IsotonicRegression()
    copy.copy(ir)


def test_isotonic_dtype():
    y = [2, 1, 4, 3, 5]
    weights = np.array([.9, .9, .9, .9, .9], dtype=np.float64)
    reg = IsotonicRegression()

    for dtype in (np.int32, np.int64, np.float32, np.float64):
        for sample_weight in (None, weights.astype(np.float32), weights):
            y_np = np.array(y, dtype=dtype)
            expected_dtype = \
                check_array(y_np, dtype=[np.float64, np.float32],
                            ensure_2d=False).dtype

            res = isotonic_regression(y_np, sample_weight=sample_weight)
            assert res.dtype == expected_dtype

            X = np.arange(len(y)).astype(dtype)
            reg.fit(X, y_np, sample_weight=sample_weight)
            res = reg.predict(X)
            assert res.dtype == expected_dtype


@pytest.mark.parametrize(
    "y_dtype", [np.int32, np.int64, np.float32, np.float64]
)
def test_isotonic_mismatched_dtype(y_dtype):
    # regression test for #15004
    # check that data are converted when X and y dtype differ
    reg = IsotonicRegression()
    y = np.array([2, 1, 4, 3, 5], dtype=y_dtype)
    X = np.arange(len(y), dtype=np.float32)
    reg.fit(X, y)
    assert reg.predict(X).dtype == X.dtype


def test_make_unique_dtype():
    x_list = [2, 2, 2, 3, 5]
    for dtype in (np.float32, np.float64):
        x = np.array(x_list, dtype=dtype)
        y = x.copy()
        w = np.ones_like(x)
        x, y, w = _make_unique(x, y, w)
        assert_array_equal(x, [2, 3, 5])


@pytest.mark.parametrize("increasing", [True, False])
def test_isotonic_thresholds(increasing):
    rng = np.random.RandomState(42)
    n_samples = 30
    X = rng.normal(size=n_samples)
    y = rng.normal(size=n_samples)
    ireg = IsotonicRegression(increasing=increasing).fit(X, y)
    X_thresholds, y_thresholds = ireg.X_thresholds_, ireg.y_thresholds_
    assert X_thresholds.shape == y_thresholds.shape

    # Input thresholds are a strict subset of the training set (unless
    # the data is already strictly monotonic which is not the case with
    # this random data)
    assert X_thresholds.shape[0] < X.shape[0]
    assert np.in1d(X_thresholds, X).all()

    # Output thresholds lie in the range of the training set:
    assert y_thresholds.max() <= y.max()
    assert y_thresholds.min() >= y.min()

    assert all(np.diff(X_thresholds) > 0)
    if increasing:
        assert all(np.diff(y_thresholds) >= 0)
    else:
        assert all(np.diff(y_thresholds) <= 0)


def test_isotonic_strict():
    # check on enforcing strictly increasing regression
    n = 100
    x = np.arange(n)
    rs = check_random_state(0)
    y = rs.randint(-50, 50, size=(n,)) + 50. * np.log1p(np.arange(n))

    ireg = IsotonicRegression(strict=True)
    ireg.fit(x, y)
    x_test = np.linspace(-10, 110, 1000)
    pred = ireg.predict(x_test)

    assert all(np.diff(ireg.y_thresholds_) > 0)
    assert all(np.diff(pred) > 0)

    # enforcing strictly decreasing regression
    y_rev = y[::-1]
    ireg = IsotonicRegression(increasing=False, strict=True)
    ireg.fit(x, y_rev)
    pred = ireg.predict(x_test)

    assert all(np.diff(ireg.y_thresholds_) < 0)
    assert all(np.diff(pred) < 0)

    # check ValueError is raised if strict monotonicity is impossible
    # fitting a strictly decreasing function on increasing data
    # gives a constant function.
    ireg = IsotonicRegression(increasing=False, strict=True)
    with pytest.raises(ValueError):
        ireg.fit(x, y)
