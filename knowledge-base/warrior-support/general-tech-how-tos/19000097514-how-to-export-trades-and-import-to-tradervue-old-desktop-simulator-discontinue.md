<!-- source: https://support.warriortrading.com/support/solutions/articles/19000097514-how-to-export-trades-and-import-to-tradervue-old-desktop-simulator-discontinued-platform- -->
<!-- category: General Tech Support -->
<!-- folder: General Tech How-Tos -->
<!-- modified: Wed, Jul 15, 2026 at 1:05 PM -->

# How to Export Trades and Import to Tradervue | Old Desktop Simulator (Discontinued Platform)

This article talks about the Windows-based, downloadable edition of the Warrior Trading Simulator, which is being retired after July 31st, 2026. Users of the new, web-based platform [should refer to this folder instead](https://support.warriortrading.com/support/solutions/folders/19000178514).

Members can use the [Member Renewal & Information page](https://www.warriortrading.com/member-renewal-information/#Second_Point_Header) to learn more about how to transition to the new platform.

Follow the guide below to learn how and where to access trade data in your simulator, how to import it to Tradervue, and how to edit your data columns.

- [Understanding the Trading Monitor](#Understanding-the-Trading-Monitor)
- [Exporting Data from the Simulator](#Exporting-Data-from-the-Simulator)
- [Importing Data into Tradervue](#Importing-Data-into-Tradervue)
- [Editing Export Columns](#Editing-Export-Columns)

### Understanding the Trading Monitor

To open a Trading Monitor, go to the main menu and click Windows > Trading Monitor.
 
Your order details will appear in the window in real-time.  You can filter the orders by using the tabs at the bottom of the window:

- 
All Orders – Shows all orders on the day, whether open, filled, canceled, etc.
- 
Open Orders – Shows only your current open orders.
- 
Executions – Shows only your fills for the day.
- 
Previous date executions – You can call up executions from the previous day under the fourth tab.
 
You can further filter the data you are viewing by right clicking on a column heading and selecting Filter > Add/Edit Filter. Once checked, click the Filter button on the top right to enable the filter. 

Tip: Left-clicking a column will auto-sort the data by that column.

### Exporting Data from the Simulator

- Click your previous day's execution tab from your Trading Monitor window. (If only uploading today's data, you can use today's execution tab.)

[image]

- Go to Actions > Export > Executions by Date Range, and select the days you want to export, up to 31 days.

[image]

- Click OK and the export will begin.

### Importing Data into Tradervue

To import data from the Warrior Trading Simulator to Tradervue, please follow these steps:

- On the left side of the upload page in Tradervue, select the date format your data uses (e.g. month-first or day-first).
- Go to the Trading Monitor in the simulator, and make sure to include these (and only these) columns in exactly this order: Date/Time/Sym/Qty/Exe Price/Side
If the columns do not appear in exactly this order, proceed to [the instructions below under "Editing Export Columns"](#Editing-Export-Columns) before continuing with the step below.
- Export the data to a text file. Save the file anywhere you want – just remember where you put it! The data in the file should look something like this: 10/10/13,11:44:59,ECTE,99,3.04,S,
- In Tradervue, on the import page, click Choose file, click the name of the file that you created above, and click Upload.

Keep in mind, if there are any MKT (market) orders listed instead of fill prices, then those orders will come back as "failed to upload."

If you have issues with Tradervue outside of the use of our simulator, please contact Tradervue support directly or follow their support procedures.

### Editing Export Columns

If your export to Tradervue did not work, you might not have the right order of columns. Please follow the steps below:

- Click View from the WT Sim Trading Monitor window, and go to Settings. . .

[image]
 
- Click the Columns tab. Under Prior Date Executions, make sure the following columns, and only the following columns, are selected: Date/Time/Sym/Side/Qty/Exe Price

[image]
 
- On the Trading Monitor window, click and drag the title of the Side column so that it appears to the right of the Exe Price column.

[image]

- Proceed to the export procedure above to export data.
