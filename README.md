# Dying-Bullish-Euphoria
Study of the Dying Bullish Euphoria stock market timing algorithm as discussed on the Mechanical Investing Board on the Motley Fool Website. <br>
This algorithm has two parameters: M (looking for a new M-day high) and N (in the last N days). This program found that SPY returns are maximized for M in the range M=138-142, and N=214. <br>
DBE.py allows you to pick values for M and N and download the daily progress to a spreadsheet. DBE_loop conducts a grid search, running through a range of values for M and N and again allowing you to save output to a spreadsheet. Both programs can read data from a spreadsheet (data is included but could be updated) or from an internet source.
