import os
import boto3
import json
import requests
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime, timedelta
import time 


API_KEY = os.environ['API_KEY']
SENDER_EMAIL = os.environ['SENDER_EMAIL']
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('trading_bot_stocks')
ses = boto3.client('ses')

def load_indicator_parameters():
    with open('technical_indicators.json', 'r') as f:
        stock_parameters = json.load(f)
    return stock_parameters

indicator_parameters = load_indicator_parameters()





def get_current_data(stock_symbol):
    """Fetch the current action details for a stock from DynamoDB."""
    response = table.get_item(
        Key={
            'stock_symbol': stock_symbol
        }
    )
    # If there's an item with the given stock_symbol, return its data; otherwise, return None
    print("GET CURRENT DATA: ")
    print(response['Item'])
    return response['Item'] if 'Item' in response else None




def update_dynamo(stock_symbol, last_triggered_condition, action_date, price):
    """Update the DynamoDB table with new action details for a stock."""
    table.put_item(
        Item={
            'stock_symbol': stock_symbol,
            'action': last_triggered_condition,
            'action_date': str(action_date),
            'price': str(price)
        }
    )

        #set technical indicators:
def set_technical_indicators(symbol):
    """Set the technical indicator values based on the given stock symbol."""
    # Check if the symbol exists in the dictionary
    if symbol not in indicator_parameters:
        print(f"No parameters found for symbol: {symbol}")
        return

    # Retrieve and set the parameters
    params = indicator_parameters[symbol]
    
    sma_length = params['sma_length']
    sma_long = params['sma_long']
    standard_deviation = params['standard_deviation']
    tsi_length = params['tsi_length']
    ROC = params['ROC']
    SMA_direction_raw_number = params['SMA_direction_raw_number']
    TSI_min = params['TSI_min']

    # Print the set values (optional)
    print(f"Parameters set for {symbol}:")
    print(f"sma_length = {sma_length}")
    
    return sma_length, sma_long, standard_deviation, tsi_length, ROC, SMA_direction_raw_number, TSI_min


def calculate_tsi(data, r, s, signal_period):
    """
    Calculate True Strength Index (TSI) and its Signal line
    :param data: DataFrame
    :param r: int
        The time period for calculating momentum (default is 25)
    :param s: int
        The time period for calculating smoothed moving averages (default is 13)
    :param signal_period: int
        The time period for calculating the Signal line (default is 9)
    :return: DataFrame
    """
    diff = data.diff(1)
    diff.fillna(0, inplace=True)

    # Calculate absolute diff
    abs_diff = abs(diff)

    # Calculate EMA of diff
    EMA_diff = diff.ewm(span=r).mean()

    # Calculate EMA of abs_diff
    EMA_abs_diff = abs_diff.ewm(span=r).mean()

    # Calculate EMA of EMA_diff
    EMA_EMA_diff = EMA_diff.ewm(span=s).mean()

    # Calculate EMA of EMA_abs_diff
    EMA_EMA_abs_diff = EMA_abs_diff.ewm(span=s).mean()

    # Calculate TSI
    TSI = pd.Series(EMA_EMA_diff / EMA_EMA_abs_diff, name='TSI')

    # Calculate Signal line
    Signal = TSI.rolling(window=signal_period).mean()

    return TSI, Signal


def check_and_notify_difference(stock_symbol, last_triggered_condition, action_date, price):
    """Check for differences between current and new data."""
    current_data = get_current_data(stock_symbol)
    print("CURRENT DATA: ", current_data)
    differences = []

    if current_data:
        if current_data['action'] != last_triggered_condition:
            differences.append(f"Action for {stock_symbol}: {current_data['action']} -> {last_triggered_condition}")
        if current_data['action_date'] != str(action_date):
            differences.append(f"Action Date for {stock_symbol}: {current_data['action_date']} -> {str(action_date)}")
        if current_data['price'] != str(price):
            differences.append(f"Price for {stock_symbol}: {current_data['price']} -> {str(price)}")

    return differences

def send_all_differences_email(all_differences, stock_data_list):
    """Send an email with all differences and stock data using SES."""
    subject = 'Trading Bot Notifications'
    
    # Generate HTML content for each stock data and concatenate
    stock_data_content = "".join(stock_data_list)
    
    # Generate the complete HTML body with stock data and differences
    body = f"""
    <html>
    <body>
        <h3>Latest Stock Data:</h3>
        {stock_data_content}
        
        <h3>Differences Detected:</h3>
        <p>{'<br>'.join(all_differences)}</p>
    </body>
    </html>
    """
    
    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={
            'ToAddresses': [RECIPIENT_EMAIL]
        },
        Message={
            'Subject': {
                'Data': subject
            },
            'Body': {
                'Html': {
                    'Data': body
                }
            }
        }
    )
    

def generate_html_content_for_stock_data(symbol, last_triggered_condition, action_date, price):
    """Generate HTML content with appropriate background color based on action."""
    # Determine the background color based on action
    if last_triggered_condition in ['flat_buy', 'hype_buy', 'rsi_buy']:
        bg_color = 'green'
    else:  # sell actions
        bg_color = 'red'
    
    return f"""
    <p style="background-color:{bg_color};">
        Symbol: {symbol}<br>
        Action: {last_triggered_condition}<br>
        Action Date: {action_date}<br>
        Price: {price}<br>
    </p>
    """
    
    
print('cold start finished')
    
    

def lambda_handler(event, context):
    all_differences = []
    stock_data_list = []
    max_wait_time = 15
    for symbol in indicator_parameters:
        # Define the parameters
        start_time = time.time()
        
        
        retries = 2
        success = False
        data = None
        
        while retries > 0 and not success:
            try:
                # Define the parameters
                interval = "60min"
                apikey = API_KEY
                
                CSV_URL = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&outputsize=full&apikey={apikey}&datatype=csv'
                
                with requests.Session() as s:
                    download = s.get(CSV_URL)
                    decoded_content = download.content.decode('utf-8')
                    data = StringIO(decoded_content)
                    long_data = pd.read_csv(data)
                    long_data = long_data.iloc[::-1].reset_index(drop=True)
                # if data retrieval was successful, set success to True
                success = True
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {str(e)}")
                retries -= 1
                if retries > 0:
                    print(f"Retrying for {symbol}. Remaining attempts: {retries}")
                    time.sleep(10)  # Wait for the specified time before retrying

        # If after all retries, data is still None, move to the next ticker
        if data is None:
            print(f"Failed to fetch data for {symbol} after multiple attempts. Skipping this ticker.")
            continue
        
        
        



        sma_length, sma_long, standard_deviation, tsi_length, ROC, SMA_direction_raw_number, TSI_min = set_technical_indicators(symbol)
        
        

        #Basic dataframe
        technical_indicators = pd.DataFrame ()
        technical_indicators["price"] = long_data["close"]
        #prints the length of iomported data
        print("price length: ", len(technical_indicators["price"]))
        
        

    
    
        # Assuming 'close' is your pandas Series with closing prices
        
        
        # Calculate TSI and Signal line
        tsi_line, signal = calculate_tsi(technical_indicators["price"], tsi_length, int(tsi_length/2), int(tsi_length/3))
        
        # Assign TSI and Signal to the technical_indicators DataFrame
        technical_indicators['TSI'] = tsi_line
        technical_indicators['TSI_signal'] = signal
        
        
       
        
        # Buy conditions
       
    
    
        # Sell conditions


      
    
        last_triggered_index = None
        last_triggered_condition = None
        
        # Loop through dataframe in reverse to find the last triggered condition
        for idx in reversed(technical_indicators.index):
            if flat_buy[idx] or hype_buy[idx] or rsi_buy[idx] or uptrend_sell[idx] or downtrend_sell[idx] or fall_sell[idx]:
                last_triggered_index = idx
                if flat_buy[idx]:
                    last_triggered_condition = 'flat_buy'
                elif hype_buy[idx]:
                    last_triggered_condition = 'hype_buy'
                elif rsi_buy[idx]:
                    last_triggered_condition = 'rsi_buy'
                elif uptrend_sell[idx]:
                    last_triggered_condition = 'uptrend_sell'
                elif downtrend_sell[idx]:
                    last_triggered_condition = 'downtrend_sell'
                elif fall_sell[idx]:
                    last_triggered_condition = 'fall_sell'
                break
        
        if last_triggered_condition:
            if last_triggered_index is not None:
                price = technical_indicators.loc[last_triggered_index, 'price']
            else:
                price = None
            # Calculate the date of the last triggered condition
            if last_triggered_condition:
                days_ago = (len(technical_indicators) - last_triggered_index) // 7
                action_date = (datetime.now() - timedelta(days=days_ago)).date()
                
               
                
                
            
            update_dynamo(symbol, last_triggered_condition, action_date, price)
            print("UPDATED DYNAMO values: ", symbol, last_triggered_condition, action_date, price)
            
            current_differences = check_and_notify_difference(symbol, last_triggered_condition, action_date, price)
        
            stock_data_html = generate_html_content_for_stock_data(symbol, last_triggered_condition, action_date, price)
            stock_data_list.append(stock_data_html)
            # Add this towards the end of your lambda_handler function, just before the return statement
            
        if current_differences:
            all_differences.extend(current_differences)
            
        end_time = time.time()
        elapsed_time = end_time - start_time
        additional_wait_time = max_wait_time - elapsed_time
        
        if additional_wait_time > 0:
            time.sleep(additional_wait_time)
    
    if all_differences or stock_data_list:
        send_all_differences_email(all_differences, stock_data_list)
    

    return {
        'statusCode': 200,
        'body': 'Email was sent successfully!' if all_differences else 'No differences found!'
    }


