# Program for testing "no new highs lately" or "dying bullish euphoria" (DBE)
# strategy. 

# Author: John Merkel
# Date: June 2019

# New to version 1.1
#   * User can download data from an Excel file (still has capability to
#     download from Y!)
#   * Fixes copy of dataframe. v 1.0 did this incorrectly, so that the 
#     original dataframe was modified in the loop.

# This is basically dbe_1.0.py placed in a double loop. This program tests
# a range of values for M (new M day high?) and N (in last N days?). The 
# output is stored in dataframes which are then written to seperate sheets
# of an Excel file.


# Import Modules
import pandas_datareader as web  # used to download stock prices from Yahoo!
import pandas as pd
import datetime                  
import numpy as np
#import math
#import json

#%% Upload historical prices from an Excel spreadsheet
#
#   For correct formating download data from Yahoo! into csv format and then 
#   simply "save as" a .xlsx spreadsheet. 

#   If you run this cell you probably do not want to run the next cell which
#   downloads prices from Y!

# NOTE: this cell need not be run every time a parameter is changed, as the
# data in this dataframe is not changed elsewhere in the program (unless you
# run the cell below which downloads data from Y!). Only run this cell if you
# update your spreadsheet.

# File name and sheet name
# Most recent data should be at the bottom.
eodDataFile = "snp500data_2019-6-18.xlsx" 
sheet = "Data"

# Reads in col headings as str. 
# Slight modifications to upload a csv file
origDataDF =  pd.read_excel(eodDataFile, sheet, index_col = 0)     

#%% Download Historical stock prices from Y!. Should include date, open, 
#   high, low, close, adjusted close, and volume.

# NOTE: this cell need not be run every time a parameter is changed, as the
# data in this dataframe is not changed elsewhere in the program. Only run
# this cell when parameters for this cell are changed! Otherwise you are
# querying Yahoo for data unnecessarily.

# Cell Parameters
tkr = 'bam'     # Stock ticker that data will be downloaded for
                  
# First trading day for SPY etf is 1993 Jan 29.
# By trial and error it seems the oldest date DataReader will allow is 
# 1970 Jan 1, even tho S&P 500 data on Yahoo! goes back to approx 1950 Jan 3
startDate = datetime.date(1980, 3, 17)  # start date (yr, mo, day)
endDate = datetime.date(2019, 6, 28)     # end date

# Download data. Most recent data is on bottom.
origDataDF = web.DataReader(tkr, 'yahoo', startDate, endDate)

#%% Main Loop

# Parameters
series = 'Adj Close'  # Can use 'Close', 'High', 'Low', 'Open', 'Adj Close'
                      # For indices 'Close' = 'Adj Close' (I think)
days_per_yr = 365.2422

# Create a range
Mrange = range(1,63)  # Range of M values. Looking for new M-day high                 
Nrange = range(10,100)  # Range of N values. M-day high in last N days

# Pick tracking start point. This will be the number of market days past the
# start date above. To assure you are getting meaningful statistics this value
# should be at least as large as the sum of the two largest numbers in the
# range above. This parameter assures uniformity along trials (different 
# values of M and N) by assuring that each trial starts tracking results on 
# the same day.
K = 200

# Create dataframes to hold statistics
cagr = pd.DataFrame(index = Mrange, columns = Nrange)
trades = pd.DataFrame(index = Mrange, columns = Nrange)
pctInMkt = pd.DataFrame(index = Mrange, columns = Nrange)

# Loop thru parameter values.  
for M in Mrange:     # Looking for a new M day hi
  print('M = ', M)
  for N in Nrange:   # in last N days 
    #print('N = ', N)

    ###################################################                  
    # Have we had a new M-day high in the last N days?
    
    # First copy original downloaded data into new dataframe so that we
    # don't modify the original dataframe. 
    eodDF = origDataDF.copy(deep = True)
    #eodDF = origDataDF[datetime.date(2009, 3, 17):].copy(deep = True)
    
    # Find new M-day highs
    eodDF['MdayHi'] = eodDF[series].rolling(M).max()
    eodDF['newHi'] = np.where(eodDF[series] == eodDF['MdayHi'], True, False)
    
    # Have we had a new M-day high in the last N days?
    # Sum last N days of 'NewHi' col. Note True=1, False=0.
    eodDF['signal'] = eodDF['newHi'].rolling(N).sum()
    
    # If sum is 0, no new high in N days (bear). Otherwise 'bull'
    eodDF['signal'] = eodDF.signal.where(eodDF.signal == 0, 'bull')
    
    # Change 0s to 'bear's. If 'bull' keep it. Otherwise 'bear'. 
    eodDF['signal'] = eodDF.signal.where(eodDF.signal == 'bull', 'bear')
    
    # IMPORTANT: we are assuming the signal is an end-of-day signal. So when
    # the signal changes from 'bear' to 'bull' we would purchase the tkr at 
    # market close. We would therefor be in the market the following day. So 
    # there is a one-day lag between the signal and returns. This shift will 
    # move all signals foward one day. We then change the wording: 
    # bull=True, bear=False.
    eodDF['inMkt'] = eodDF['signal'].shift(1)
    eodDF['inMkt'] = eodDF['inMkt'].where(eodDF['inMkt'] == 'bull', False)
    eodDF['inMkt'] = eodDF['inMkt'].where(eodDF['inMkt'] == False, True)
    
    # Set values to False prior to when we start tracking. If we start tracking
    # at index K that will be when we get our first signal, but we will not be
    # in the market on that day. The first possible valid signal occurs at 
    # index M+N.
    eodDF.loc[eodDF.index.values <= eodDF.index.values[K], 'inMkt'] = False
    
    ##################################
    # Calculate returns and statistics
        
    # Calculate daily tkr returns. shift(1) is previous day's data
    # Adjusted close will take stock splits and dividends into account
    eodDF['tkrRtnDay'] = eodDF['Adj Close']/eodDF['Adj Close'].shift(1) 
    
    # Calculate cumulative return. Note that first valid sell signal occurs at 
    # least M+N days after first day of data. Must estable M-day hi followed 
    # by N days w/o a new M-day hi. So this column only makes sence for index 
    # location past M+N
    
    # Intermediate calculatioin: years since starting date at M+N index
    eodDF['yrs'] = (eodDF.index.values - eodDF.index.values[K]).astype(
                   'timedelta64[D]') / (days_per_yr * np.timedelta64(1, 'D'))

    # Calculate daily return for dbe. Same as return for ticker, except 1
    # when inMkt is False
    eodDF['dbeRtnDay'] = eodDF['tkrRtnDay'].where(eodDF['inMkt'] == True, 1) 
    
    # Now calculate cumulative return starting at index K. To do this we will 
    # shift returns prior to K "off" the dataframe, then apply the "cumprod()" 
    # fcn, then shift the cumulative product back into place. This will create
    # "Not a Number" (NaN) entries prior to index K, which is probably a good 
    # thing since we are not tracking yet.
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
    # Erase any signals prior to start of tracking
    eodDF.loc[eodDF.index.values < eodDF.index.values[K], 'signal'] = np.nan
    
    # Count 'bull' and 'bear' days and calculate percent.
    numBulls = len(eodDF[eodDF['signal'] == 'bull'])
    numBears = len(eodDF[eodDF['signal'] == 'bear'])
    p = 100 * numBulls / (numBulls + numBears)
    
    #################################
    # Place statistics into dataframes
    cagr.loc[M,N] = eodDF['dbeCAGR'].iloc[-1]
    trades.loc[M,N] = tradesPerYr
    pctInMkt.loc[M,N] = p
    
# Calculate CAGR for the ticker
tkrRtn = eodDF['Adj Close'][-1] / eodDF['Adj Close'][K]
yrs = eodDF['yrs'].iloc[-1]
tkrCAGR = tkrRtn**(1/yrs)

# Print some statistics
print('Ticker CAGR = ', tkrCAGR)    
print('Years = ', yrs)
print('Max CAGR = ', cagr.max())
#%%############################################## 
# Run this cell to write output to an Excel file.
# Kind of slow.

# Parameters
excelOut = 'dbeStats.xlsx'       # Excel file name
sheet0 = 'dbe'                   # Sheet name
sheet1 = 'cagr'                  # Sheet name
sheet2 = 'trades'
sheet3 = 'pctInMkt'

# Write to Excel file
# IF you don't know which folder this is writing to try typing "pwd" at the 
# prompt. It should return the current working directory.
writerObj = pd.ExcelWriter(excelOut)
eodDF.to_excel(writerObj, sheet0)       # writes to an excel sheet
cagr.to_excel(writerObj, sheet1)        # writes to an excel sheet
trades.to_excel(writerObj, sheet2) 
pctInMkt.to_excel(writerObj, sheet3) 
writerObj.save()                        # saves the excel workbook to disk
