# Dynamic pricing experiment

Run `python -m ml.run_experiments` from the project root. The simulation generates 400 time steps with merchant price, demand, inventory, season, competitor price, and merchant unit cost. Synthetic unit demand decreases with candidate price and is capped by inventory. The target is the candidate maximizing simulated gross profit.

The first 320 steps train ridge and random forest regression and the final 80 measure MAE, MSE, RMSE, R², and mean simulated gross profit. Previous merchant price is the baseline. The interactive lab applies the published ridge coefficients and model output bounds. The experiment concerns a simulated merchant and has no marketplace write path.
