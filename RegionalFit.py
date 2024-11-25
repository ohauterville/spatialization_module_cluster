from scipy.optimize import minimize
import numpy as np
from functools import partial
import matplotlib.pyplot as plt
import sys

class RegionalFit:
    def __init__(self, name, parent_x, parent_y,):
        self.name = name
        self.fitted_params = []

        self.parent_x = parent_x
        self.parent_y = parent_y

        self.pop_distrib = None
        self.data_x = None
        self.data_y = None
        self.constraints = []
        self.opt = None

        self.parent_y_pred = []
        self.mse = np.nan
        self.rmse = np.nan
        self.r_squared = np.nan

        self.tolerance_percentage = None
        self.nb_vars = 3
        self.colors_reg = ["blue", "orange", "green", "peru", "darkorange", "gold", "purple", "magenta", "chartreuse", "turquoise", "darkcyan", "deepskyblue", "brown",]

        # Create a linspace for both x1 and x2 if x2 is valid
        self.parent_x_fit = np.linspace(min(self.parent_x), max(self.parent_x), 100)

        self.parent_y_fit = []

    def logistic(self, x, s, k, x0):
        return s / (1 + np.exp(-k*(x-x0)))
    
    def constraint_datapoint(self, vars, subregion_idx=0, point_idx=0):
        return self.logistic(self.data_x[subregion_idx][point_idx], vars[subregion_idx*self.nb_vars+0], vars[subregion_idx*self.nb_vars+1], vars[subregion_idx*self.nb_vars+2]) - self.data_y[subregion_idx][point_idx]  

    def upper_bound_constraint(self, vars, subregion_idx=0, point_idx=0,):
        """Constraint that allows the function to pass near a point within a given tolerance."""
        logistic_value = self.logistic(
            self.data_x[subregion_idx][point_idx],
            vars[subregion_idx * self.nb_vars + 0],
            vars[subregion_idx * self.nb_vars + 1],
            vars[subregion_idx * self.nb_vars + 2]
        )
        observed_value = self.data_y[subregion_idx][point_idx]

        # Calculate the relative tolerance
        relative_tolerance = self.tolerance_percentage / 100 * observed_value

        # Constraint to enforce: logistic_value <= observed_value + relative_tolerance
        return observed_value + relative_tolerance - logistic_value

    def lower_bound_constraint(self, vars, subregion_idx=0, point_idx=0):
        logistic_value = self.logistic(
            self.data_x[subregion_idx][point_idx],
            vars[subregion_idx * self.nb_vars + 0],
            vars[subregion_idx * self.nb_vars + 1],
            vars[subregion_idx * self.nb_vars + 2]
        )
        observed_value = self.data_y[subregion_idx][point_idx]

        # Calculate the relative tolerance
        relative_tolerance = self.tolerance_percentage / 100 * observed_value

        # Constraint to enforce: logistic_value >= observed_value - relative_tolerance
        return logistic_value - (observed_value - relative_tolerance)

    def objective(self, vars):
        y_pred = np.zeros_like(self.parent_y)  # Initialize as array instead of list
        
        for idx in range(len(self.pop_distrib)):
            y_pred += self.pop_distrib[idx]*self.logistic(self.parent_x, vars[idx*self.nb_vars], vars[idx*self.nb_vars+1], vars[idx*self.nb_vars+2])
    
        return np.sqrt(np.mean((self.parent_y - y_pred) ** 2))
    
    def define_constraints(self):
        if self.pop_distrib is None:
            print("Please put the population distribution")
            sys.exit()
        if self.data_x is None or self.data_y is None:
            print("No data points !")
            sys.exit()

        for i in range(len(self.data_x)):
            for ii in range(len(self.data_x[i])):
                if self.tolerance_percentage is None:
                    self.constraints.append({'type': 'eq', 'fun': partial(self.constraint_datapoint, subregion_idx=i, point_idx=ii)})
                else:    
                    self.constraints.append({
                        'type': 'ineq',
                        'fun': partial(self.upper_bound_constraint, subregion_idx=i, point_idx=ii)})
                    self.constraints.append({
                        'type': 'ineq',
                        'fun': partial(self.lower_bound_constraint, subregion_idx=i, point_idx=ii)})


    def optimize(self):
        self.define_constraints()
        # Initial guess
        initial_guess = [50, 0.0003, 18000] * len(self.data_x)

        bounds = [(10, 250), (0.0001, 0.001), (10000, None)] * len(self.data_x)

        # Perform the optimization
        self.opt = minimize(self.objective, initial_guess, bounds=bounds, constraints=self.constraints, method="SLSQP",    options={"maxiter": 10000, "disp": True}
)

        # Display the opt
        if self.opt.success:
            print("Optimal solution:", self.opt.x)
            print("Objective function value:", self.opt.fun)
        else:
            print("Optimization failed:", self.opt.message)

    def plot(self):
        guessed_logistic = np.zeros_like(self.parent_x)  # Initialize as array instead of list

        plt.title("The fitted and consistent regional estimates")
        # plt.plot(x, national_logistic, color="k", label="national")

        for i in range(len(self.pop_distrib)):
            plt.scatter(self.data_x[i], self.data_y[i], color=self.colors_reg[i], ) #label=f"Data region {i}")
            plt.plot(self.parent_x, self.logistic(self.parent_x, self.opt.x[self.nb_vars*i+0], self.opt.x[self.nb_vars*i+1], self.opt.x[self.nb_vars*i+2]), color=self.colors_reg[i], linestyle="dashed", label=f"Estimated regional logistic {i}")
            guessed_logistic += self.pop_distrib[i] * self.logistic(self.parent_x, self.opt.x[self.nb_vars*i+0], self.opt.x[self.nb_vars*i+1], self.opt.x[self.nb_vars*i+2])

        plt.plot(self.parent_x, self.parent_y, color='k', label="parent")
        plt.plot(self.parent_x, guessed_logistic, color="r", label="fit")
        # plt.legend(loc="upper left")
        plt.plot()