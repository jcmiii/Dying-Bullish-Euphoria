# Program for testing "no new highs lately" or "dying bullish euphoria" (DBE)
# strategy. 

# Author: John Merkel
# Date: June 2019

# New to version 2.0
#   * Added a ticker price threshold for reentry. When the ticker (index) falls
#     below a user entered percent of the most recent new high then the program
#     reenters the market regardless of the signal (bull or bear). 

# New to version 1.2
#   * Added plotting
#   * Counts days since last M-day high

# New to version 1.1
#   * Can upload data from a spreadsheet. For some reason downloading from
#     this program only retrieves data since about 1970 for the S&P 500. 
#     However, you can manually download data from Y! that goes back to 1950.
#     Similar issues for other indices. Hence uploading from a spreadsheet 
#     may be prefered.
#   * Fixes copy of dataframe. v 1.0 did this incorrectly, so that the original
#     dataframe was modified in the loop. I don't think it caused any issues,
#     but it was not consistent with my intention.
 
# Import Modules
import pandas as pd
import datetime                  
import numpy as np
#import math 
#import json

#%% Upload historical prices from an Excel spreadsheet
#   If you want to download data from Yahoo! don't run this cell.
#
#   For correct formating download data from Yahoo! into csv format and then 
#   simply "save as" a .xlsx spreadsheet. 

#   If you run this cell you probably do not want to run the next cell which
#   downloads prices from Y!

# File name and sheet name
# Most recent data should be at the bottom.
eodDataFile = "snp500data_2019-6-18.xlsx" 
sheet = "Data"

# Reads in col headings as str. 
origDataDF =  pd.read_excel(eodDataFile, sheet, index_col = 0)    

# Do this if you want a smaller dataset for testing, checking post-discovery
# results, etc.
#origDataDF = origDataDF.tail(1000)

#%% Download Historical stock prices from Y!. 
#   Should include date, open, high, low, close, adjusted close, and volume.
#   If you imported data from a spreadsheet above don't run this cell.

# Import module to download stock prices from Yahoo!
import pandas_datareader as web 

# NOTE: this cell need not be run every time a parameter is changed, as the
# data in this dataframe is not changed elsewhere in the program. Only run
# this cell when parameters for this cell are changed! Otherwise you are
# querying Yahoo for data unnecessarily.

# Cell Parameters
tkr = '^IXIC'     # Stock ticker that data will be downloaded for
                  
# First trading day for SPY etf is 1993 Jan 29.
# By trial and error it seems the oldest date DataReader will allow is 
# 1970 Jan 1, even tho S&P 500 data on Yahoo! goes back to approx 1950 Jan 3
# For NASDAQ (^IXIC) 1971, Feb 5
startDate = datetime.date(1971, 2, 1)   # start date (yr, mo, day)
endDate = datetime.date(2019, 8, 2)      # end date

# Download data. Most recent data is on bottom.
origDataDF = web.DataReader(tkr, 'yahoo', startDate, endDate)

#%% Parameters
reentryPct = 0.01     # If the price drops below (reentryPct * most recent New 
                      # high) then reenter position regardless of signal. 
                      # To disable set to 0
M = 107               # Looking for a new M-day hi
N = 134               # in last N days
K = 250               # Starting point for calculations. Should be at least
                      # as large as M+N
series = 'Adj Close'  # Can use 'Close', 'High', 'Low', 'Open', 'Adj Close'
                      # For indices 'Close' = 'Adj Close' (I think)

###################################################                  
# Have we had a new M-day high in the last N days?

# First copy original downloaded data into new dataframe so we get clean data
# each time we rerun this cell.                      
eodDF = origDataDF.copy(deep = True)

# Find new M-day highs (True) and calculate reentry price
eodDF['MdayHi'] = eodDF[series].rolling(M).max()
eodDF['newHi'] = np.where(eodDF[series] == eodDF['MdayHi'], True, False)
eodDF['rePt'] = reentryPct*eodDF['MdayHi']

# Count days since last new M-day high.  
# I found this soln on Stack Overflow. 
# First run comparison to find where new contiguous groups begin (True)
eodDF['dSinceNewHi'] = (eodDF['newHi'] != eodDF['newHi'].shift(1))

# Now use cumsum() (cummulative sum) to count the number of "groups"
eodDF['dSinceNewHi'] = eodDF['dSinceNewHi'].cumsum()

# Now groupby() with cumcount() to form running count of each group. This 
# counts first occurance as 0, which is correct when we transition to a new
# high (Trues), but is 1 too small when we transistion to "not a new high" 
# (false). We are counting days since a new high (Falses) so add 1.
eodDF['dSinceNewHi'] = eodDF.groupby('dSinceNewHi').cumcount() + 1

# Finally, all occurances of 'True' in 'newHi' col yield a corresponding 0 in
# 'dSinceNewHi' col.
eodDF.loc[eodDF['newHi'] == True, 'dSinceNewHi'] = 0

# Have we had a new M-day high in the last N days?
eodDF.loc[eodDF['dSinceNewHi'] < N, 'signal'] = 'bull'  
eodDF.loc[eodDF['signal'] != 'bull', 'signal'] = 'bear'  

# Erase any signals prior to start of tracking
eodDF.loc[eodDF.index.values < eodDF.index.values[K], 'signal'] = np.nan

# IMPORTANT: we are assuming the signal is an end-of-day signal. So when
# the signal changes from 'bear' to 'bull' we would purchase the tkr at market
# close. We would therefor be in the market the following day. So there is a 
# one-day lag between the signal and returns. The shift moves all signals
# foward one day. We then change the wording: bull=True, bear=False.
eodDF['inMkt'] = eodDF['signal'].shift(1)
eodDF['inMkt'] = eodDF['inMkt'].where(eodDF['inMkt'] == 'bull', False)
eodDF['inMkt'] = eodDF['inMkt'].where(eodDF['inMkt'] == False, True)

# Set values to False prior to when we start tracking. First possible valid 
# signal day occurs at index M+N, but we will not be in the market that day.
eodDF.loc[eodDF.index.values <= eodDF.index.values[K], 'inMkt'] = False

############################################################################
# Now we calculate reetnry points due to price crossing below user set 
# threashold. This will trigger if the signal is bear but the price has dropped
# below a user set percent of the most recent new high. We will then get back 
# into the market and stay there until a new high is reached again. 

# Create new column in dataframe, populate with NaN
eodDF['reentrySignal'] = np.nan      

# Retrieve indexes where price is below reentry point and signal is 'bear'. 
# If the signal rises above the reentry point while the signal is still 'bear'
# that will not be captured here, so we will forward fill below.
idxList = eodDF.loc[
            (eodDF.Low < eodDF.rePt) & (eodDF.signal == 'bear')].index

# We want to be in the market on these days        
eodDF.loc[idxList, 'reentrySignal'] = True 

# Marker for a new high; turn off reentrySignal
eodDF.loc[eodDF.dSinceNewHi == 0, 'reentrySignal'] = False

# Now forward fill. True will forward fill until we hit the False marker.
# False will forward fill until it hits a True.
eodDF['reentrySignal'] = eodDF['reentrySignal'].fillna(method = 'ffill')

# All is good except that we need to extend the sequence of Trues by 1 so that
# we can transfer them to the inMkt column. Otherwise we'll be in the market
# until we hit a new high (good) and then we will be out one day (bad) before
# jumping back in. 

# This gets the True where we need it.
eodDF['reentrySignal'] = ( eodDF['reentrySignal'] + 
                           eodDF['reentrySignal'].shift(1) )

# But now we have a bunch of 2s that should be 1s. Fix that.
eodDF.loc[ eodDF['reentrySignal'] == 2, 'reentrySignal' ] = 1

# Not necessary, but change back to Trues and Falses
eodDF.loc[ eodDF['reentrySignal'] == 0, 'reentrySignal' ] = False
eodDF.loc[ eodDF['reentrySignal'] == 1, 'reentrySignal' ] = True

# Now copy the Trues over the inMkt column
eodDF.loc[ eodDF['reentrySignal'] == True, 'inMkt' ] = True


#%%###############################
# Calculate returns and statistics

# Calculate daily tkr returns. shift(1) is previous day's data
eodDF['tkrRtnDay'] = eodDF['Adj Close']/eodDF['Adj Close'].shift(1) 

# Calculate running return. Note that first valid sell signal occurs at least
# M+N days after first day of data. Must estable M-day hi followed by N days
# w/o a new M-day hi. So this col only makes sence for index location 
# past M+N
eodDF['tkrCumRtn'] = eodDF['Adj Close']/eodDF['Adj Close'][K]

# Calculate running CAGR. 
# Intermediate calculatioin: years since starting date at M+N index
days_per_yr = 365.2422
eodDF['yrs'] = (eodDF.index.values - eodDF.index.values[K]).astype(
               'timedelta64[D]') / (days_per_yr * np.timedelta64(1, 'D'))
eodDF['tkrCAGR'] = eodDF['tkrCumRtn']**(1 / eodDF['yrs'])

# Calculate daily return for algorithm. Same as return for ticker, except 1
# when inMkt is False
eodDF['dbeRtnDay'] = eodDF['tkrRtnDay'].where(eodDF['inMkt'] == True, 1) 

# Calculate cumulative return starting at index K. To do this we will shift
# returns prior to K "off" the dataframe, then use the "cumprod()" fcn,
# then shift the cumulative product back into place. This will create "Not a
# Number" (NaN) entries prior to index K, which is probably a good thing,
# since those calculations would not be valid anyway.
eodDF['dbeCumRtn'] = eodDF['dbeRtnDay'].shift(-K).cumprod().shift(K)

# Calculate algorithm CAGR
eodDF['dbeCAGR'] = eodDF['dbeCumRtn']**(1 / eodDF['yrs'])

# Calculate mean trades per year
# Determine when trades took place
eodDF['trade'] = eodDF['inMkt'].shift(-1) - eodDF['inMkt']

# Erase any trades that occured before we start tracking
eodDF.loc[eodDF.index.values < eodDF.index.values[K], 'trade'] = 0

# Sum trades: Take absolute value then add
tradesPerYr = eodDF.trade.abs().sum() / eodDF['yrs'].iloc[-1]

# Calculate percent of time in the market
# Count 'bull' and 'bear' days and calculate percent.
numBulls = len(eodDF[eodDF['signal'] == 'bull'])
numBears = len(eodDF[eodDF['signal'] == 'bear'])
pctInMkt = 100 * numBulls / (numBulls + numBears)

#################################
# Print parameters and statistics
#print('Tkr = ', tkr)
print('M = ', M)
print('N = ', N)
print('K = ', K)
print('Reentry Pct = ', reentryPct)
print('Tkr CAGR = ', eodDF['tkrCAGR'].iloc[-1])
print('DBE CAGR = ', eodDF['dbeCAGR'].iloc[-1])
print('Years = ', eodDF['yrs'].iloc[-1])
print('Trades/yr = ', tradesPerYr)
print('Pct in mkt = ', pctInMkt, '%')

#%%############################################## 
# Run this cell to write output to an Excel file.
# Kind of slow, so probably don't want to run it
# unless necessary.

# Parameters
excelOut = 'dbeCalculations.xlsx'  # Excel file name
sheetName = 'dbe'                  # Sheet name

# Write to Excel file
# If you don't know which folder this is writing to try typing "pwd" at the 
# prompt. It should return the current working directory.
writerObj = pd.ExcelWriter(excelOut)
eodDF.to_excel(writerObj,'dbe' )       # writes to an excel sheet
writerObj.save()                       # saves the excel workbook to disk

#%%############################################## 
# Second (improved) attempt at plotting returns. Trying unsucessfully to get 
# rid of discontinuity.

# Import Modules
import matplotlib.pyplot as plt

# Definitions
def plotFcn(group):
    global ax
    color = 'r' if (group['color'] < 1).all() else 'g'
    ax.plot(group.index, group.dbe, c=color, linewidth=1)

# Pick starting, ending dates
startDate = datetime.date(1951, 6, 1)  # start date (yr, mo, day)
endDate = datetime.date(2019, 6, 1)     # end date

# Create a new dataframe to hold graph data. Probably other ways to do it but 
# I found this idea on Stack Overflow. The tricky part is getting the graph to
# be two-colored; red = out of market, green = in market
plotDF = pd.DataFrame()
plotDF['dbe'] = eodDF[startDate : endDate]['dbeRtnDay'].cumprod() 
plotDF['tkr'] = eodDF[startDate : endDate]['tkrRtnDay'].cumprod()

# Create color map: red = 0, green = 1. Basically red where inMkt = False(0),
# and green where inMkt = True(1).
plotDF['color'] = eodDF[startDate : endDate]['inMkt']

# Now find boundries. Make first entry a 0
plotDF['bdry'] = plotDF['color'] - plotDF['color'].shift(1)
plotDF['bdry'] = plotDF['bdry'].abs()
plotDF.loc[ plotDF.index[0], 'bdry']  = 0

# Calculate groups
plotDF['groups'] = plotDF['bdry'].cumsum()

# Plot returns
fig, ax = plt.subplots()

# plot of DBE. This throws out the endpoints of the sequences creating a 
# non-continuous graph
plotDF.groupby( plotDF['groups'] ).apply(plotFcn)

# add "buy and hold"
ax.plot(plotDF.index, plotDF.tkr, 'blue', linewidth=1)

#%%##############################
# Test code 2

for x in range(K, eodDF.shape[0]):
    print(eodDF['yrs'][x])

#%%############################################## 
# Initial attempt at plotting returns

# Import Modules
import matplotlib.pyplot as plt

# Definitions
def plotFcn(group):
    global ax
    color = 'r' if (group['color'] < 1).all() else 'g'
    ax.plot(group.index, group.dbe, c=color, linewidth=1)

# Pick starting, ending dates
startDate = datetime.date(2016, 3, 1)  # start date (yr, mo, day)
endDate = datetime.date(2016, 7, 1)     # end date

# Create a new dataframe to hold graph data. Probably other ways to do it but 
# I found this idea on Stack Overflow. The tricky part is getting the graph to
# be two-colored; red = out of market, green = in market
plotDF = pd.DataFrame()
plotDF['dbe'] = eodDF[startDate : endDate]['dbeRtnDay'].cumprod() 
plotDF['tkr'] = eodDF[startDate : endDate]['tkrRtnDay'].cumprod()

# Create color map: red = -1, green = 1. Basically red where inMkt = False(0),
# and green where inMkt = True(1), but we want to tack an extra False onto the 
# beginning of the False sequence due to the lag in reacting to the signal.
plotDF['color'] = eodDF[startDate : endDate]['inMkt']

# Close, but now we need to tack on that extra False to the begining. This
# creates sequences of 0s and 2s with a single 1 seperating each sequence.
# Also, last entry is NaN. Change that to have same value as penultimate entry
plotDF['color'] = plotDF['color'] + plotDF['color'].shift(-1)
plotDF.loc[ plotDF.index[-1], 'color']  = plotDF['color'].iloc[-2]

# Now each sequence (0s or 2s) is seperated by a 1. Change the 1s to 0s, then 
# subtract 1 from everything.
plotDF['color'] = plotDF['color'].where( plotDF['color'] != 1, 0)
plotDF['color'] = plotDF['color'] - 1

# Plot returns
fig, ax = plt.subplots()

# plot of DBE. This throws out the endpoints of the sequences creating a 
# non-continuous graph
plotDF.groupby( (plotDF['color'] * plotDF['color'].shift(1) < 0
                 ).cumsum() ).apply(plotFcn)

# add "buy and hold"
ax.plot(plotDF.index, plotDF.tkr, 'k', linewidth=1)

#%%#########################

eodDF[['Close','newHi','rePt','dSinceNewHi','signal']]        





