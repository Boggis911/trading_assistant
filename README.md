# trading_assistant hosted on AWS services

After conducting a swing trading analysis using Python, I found that certain trading strategies consistently outperformed the broader market returns. This discovery prompted me to delve deeper into trading strategy analysis, culminating in the creation of a trading assistant that provides me with stock trading recommendations.

I developed the trading assistant using AWS services including Lambda, DynamoDB, EventBridge, and the Simple Email Service (SES). The core trading logic resides in a dedicated Lambda function, responsible for stock trend analysis, data recording in DynamoDB, and sending me key market condition summaries via AWS SES. This entire workflow is initiated by the EventBridge service. To efficiently manage stock symbols and technical indicator parameters tailored to each stock, I housed this information in a separate JSON file, easily accessible to the Lambda function when required.

The primary challenge in this endeavor was not the development of the trading logic or optimizing technical parameters — these were already established. Instead, the project's complexity came from ensuring a seamless workflow in real-time market conditions. One problem was the API usage limits set by our third-party provider, which I navigated using a sleep function to avoid reaching the api limit.

I have never done any AWS projects that had tangible business implications, so I also encountered many technical difficulties. As a novice, orchestrating major code segments was daunting, especially without a clear understanding of certain technical application aspects. Navigating the correct Lambda permissions, manual Lambda configuration, and understanding the Lambda event handling were among the challenges faced.

Today, my trading assistant remains an invaluable tool, keeping me updated with the latest stock market sentiment and guiding more informed stock trading decisions.


