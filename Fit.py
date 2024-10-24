from scipy.optimize import curve_fit
import numpy as np
import pandas as pd


class Fit:
    def __init__(self, name, x1, x2, y):
        self.name = name
        self.fitted_params = []

        self.x1 = x1
        self.x2 = x2
        self.y = y

        self.y_pred = []
        self.mse = np.nan
        self.rmse = np.nan
        self.r_squared = np.nan

        # Create a linspace for both x1 and x2 if x2 is valid
        self.x1_fit = np.linspace(min(self.x1), max(self.x1), 100)
        self.x2_fit = np.linspace(min(self.x2), max(self.x2), 100)

        self.y_fit = []

    def fit_linear_regression(self):
        popt, _ = curve_fit(self._linear_objective, self.x1, self.y)
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._linear_objective(
            self.x1, self.fitted_params[0], self.fitted_params[1]
        )
        self.y_fit = self._linear_objective(
            self.x1_fit, self.fitted_params[0], self.fitted_params[1]
        )

        self._compute_errors()

    def fit_double_linear_regression(self):
        popt, _ = curve_fit(self._double_linear_objective, [self.x1, self.x2], self.y)
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._double_linear_objective(
            [self.x1, self.x2],
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )
        self.y_fit = self._double_linear_objective(
            [self.x1_fit, self.x2_fit],
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )

        self._compute_errors()

    def fit_STL(
        self,
        init=[1, 1, 1, 1, 1],
        bounds=([0, 0, 0, 0, 0], [600, 1000, 1000, 1, 100000]),
    ):
        popt, _ = curve_fit(
            self._STL_objective, [self.x1, self.x2], self.y, p0=init, bounds=bounds
        )
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._STL_objective(
            [self.x1, self.x2],
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
            self.fitted_params[3],
            self.fitted_params[4],
            # self.fitted_params[5],
        )
        self.y_fit = self._STL_objective(
            [self.x1_fit, self.x2_fit],
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
            self.fitted_params[3],
            self.fitted_params[4],
            # self.fitted_params[5],
        )

        self._compute_errors()

    def fit_logistic(self, init=[1, 1, 1], bounds=([0, 0, 0], [600, 1, 100000])):
        popt, _ = curve_fit(
            self._logistic_objective, self.x1, self.y, p0=init, bounds=bounds
        )
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._logistic_objective(
            self.x1,
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )
        self.y_fit = self._logistic_objective(
            self.x1_fit,
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )

        self._compute_errors()

    def fit_exponential_decay(
        self, init=[1, 1, 1], bounds=([0, 0, 0], [1000, 1000, 1000])
    ):
        popt, _ = curve_fit(
            self._exponential_decay_objective, self.x1, self.y, p0=init, bounds=bounds
        )
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._exponential_decay_objective(
            self.x1,
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )
        self.y_fit = self._exponential_decay_objective(
            self.x1_fit,
            self.fitted_params[0],
            self.fitted_params[1],
            self.fitted_params[2],
        )

        self._compute_errors()

    def fit_exponential_decay2(self, init=[1, 1], bounds=([0, 0], [1000, 1000])):
        popt, _ = curve_fit(
            self._exponential_decay2_objective,
            self.x1,
            self.y,
            p0=init,
            bounds=bounds,
        )
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._exponential_decay2_objective(
            self.x1,
            self.fitted_params[0],
            self.fitted_params[1],
        )
        self.y_fit = self._exponential_decay2_objective(
            self.x1_fit,
            self.fitted_params[0],
            self.fitted_params[1],
        )

        self._compute_errors()

    def fit_reciprocal(self, init=[1, 10], bounds=([0, 0], [10, 1000])):
        popt, _ = curve_fit(
            self._reciprocal_objective, self.x1, self.y, p0=init, bounds=bounds
        )
        for param in popt:
            self.fitted_params.append(param)

        self.y_pred = self._reciprocal_objective(
            self.x1,
            self.fitted_params[0],
            self.fitted_params[1],
        )
        self.y_fit = self._reciprocal_objective(
            self.x1_fit,
            self.fitted_params[0],
            self.fitted_params[1],
        )

        self._compute_errors()

    def _STL_objective(self, X, a, b, c, d, e):
        pib_per_cap, rho = X
        saturation = self._exponential_decay_objective(rho, a, b, c)
        return saturation / (1 + np.exp(-d * (pib_per_cap - e)))

    def _logistic_objective(self, X, a, b, c):
        return a / (1 + np.exp(-b * (X - c)))

    def _exponential_decay_objective(self, X, a, b, c):
        return a * np.exp(-b * X) + c

    def _exponential_decay2_objective(self, X, a, b):
        return a * np.exp(-b * X)

    def _linear_objective(self, x1, a, b):
        return a * x1 + b

    def _double_linear_objective(self, X, a0, a1, a2):
        x1, x2 = X
        return a0 * x1 + a1 * x2 + a2

    def _compute_errors(self):
        self._compute_rmse()
        self._compute_r_squared()

    # Function to compute MSE
    def _compute_mse(self):
        self.mse = np.mean((self.y - self.y_pred) ** 2)

    # Function to compute RMSE
    def _compute_rmse(self):
        self._compute_mse()
        self.rmse = np.sqrt(self.mse)

    # Function to compute R-squared
    def _compute_r_squared(self):
        ss_res = np.sum((self.y - self.y_pred) ** 2)
        ss_tot = np.sum((self.y - np.mean(self.y)) ** 2)
        self.r_squared = 1 - (ss_res / ss_tot)
