import credentials as cr
from dhanhq import dhanhq

dhan = dhanhq(cr.clientId,cr.apiToken)

holdingResponse = dhan.get_holdings()

# Check if the response is successful and contains data
if holdingResponse.get('status') == 'success' and 'data' in holdingResponse:
    holdings = holdingResponse['data']  # Extract the holdings data

    # Filter to show only the desired fields
    filtered_holdings = [{'Stock Name': item['tradingSymbol'], 'Quantity': item['totalQty'], 'Average Price': item['avgCostPrice'], 'Current Price': item['lastTradedPrice']} for item in holdings]

    # Print the filtered data
    for holding in filtered_holdings:
        print(holding)
else:
    print("Failed to retrieve holdings or no data available.")
