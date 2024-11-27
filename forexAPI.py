from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from tradingview_ta import TA_Handler, Interval
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Create a Flask application instance
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) for specific routes
# This allows frontend applications running on other domains (e.g., Angular) to interact with the API
CORS(app, resources={r"/get_recommendation": {"origins": "http://localhost:4200"}})

# List of supported currency pairs for analysis
currency_pairs = ['EURUSD', 'USDJPY', 'GBPUSD', 'AUDUSD', 'USDCHF', 'NZDUSD', 
                  'USDCAD', 'USDCNH', 'USDSEK', 'USDRUB']

# Mapping of supported time intervals to TradingView intervals
intervals = {
    '1min': Interval.INTERVAL_1_MINUTE,
    '1h': Interval.INTERVAL_1_HOUR,
    '1day': Interval.INTERVAL_1_DAY,
    '1week': Interval.INTERVAL_1_WEEK,
    '1month': Interval.INTERVAL_1_MONTH
}

# Endpoint to generate and return chart data
@app.route('/get_chart', methods=['GET'])
def get_chart():
    # Dummy counts for pie chart data (can be replaced with real data)
    buy_count, neutral_count, sell_count = 1, 1, 1
    chart_data_base64 = get_chart_data(buy_count, neutral_count, sell_count)

    # Return the chart's URL for the client to fetch
    return jsonify({'chart_data': f'http://localhost:5000/get_chart/{chart_data_base64}'})

# Endpoint to serve saved chart images
@app.route('/get_chart/<filename>', methods=['GET'])
def serve_image(filename):
    # Send the requested image file to the client
    return send_file(f'./{filename}', mimetype='image/png')

# Endpoint to fetch trading recommendations
@app.route('/get_recommendation', methods=['GET', 'POST'])
def get_recommendation():
    if request.method == 'POST':
        # Extract data from POST request body
        data = request.get_json()
        selected_pair = data.get('selected_pair', '').upper()  # Selected currency pair
        selected_interval = data.get('selected_interval', '').lower()  # Selected time interval
    else:
        # Extract data from GET request query parameters
        selected_pair = request.args.get('selected_pair', '').upper()
        selected_interval = request.args.get('selected_interval', '').lower()

    # Validate input parameters
    if selected_pair not in currency_pairs or selected_interval not in intervals:
        return jsonify({'error': 'Invalid input parameters'}), 400

    # Perform technical analysis using TradingView API
    handler = TA_Handler(
        symbol=selected_pair,       # Currency pair
        screener='forex',           # Market type
        exchange='FX_IDC',          # Data provider
        interval=intervals[selected_interval]  # Analysis interval
    )

    analysis = handler.get_analysis()  # Fetch analysis results
    summary = analysis.summary         # Extract summary of indicators

    # Extract counts of BUY, SELL, and NEUTRAL signals
    buy_count = summary.get('BUY', 0)
    sell_count = summary.get('SELL', 0)
    neutral_count = summary.get('NEUTRAL', 0)

    # Determine overall recommendation based on counts
    if buy_count > sell_count:
        recommendation = 'BUY'
    elif sell_count > buy_count:
        recommendation = 'SELL'
    elif neutral_count >= max(buy_count, sell_count):
        recommendation = 'NEUTRAL'
    else:
        recommendation = 'NEUTRAL'

    # Generate chart URL for visualization
    chart_data = f'http://localhost:5000/get_chart/{get_chart_data(buy_count, neutral_count, sell_count)}'

    # Return recommendation and chart link as JSON response
    return jsonify({'recommendation': recommendation, 'chart_data': chart_data})

# Utility function to generate a pie chart and save it as an image
def get_chart_data(buy_count, neutral_count, sell_count):
    labels = ['SELL', 'NEUTRAL', 'BUY']  # Pie chart labels
    sizes = [sell_count, neutral_count, buy_count]  # Data for each segment
    colors = ['red', 'yellow', 'green']  # Segment colors

    # Create a pie chart
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Ensure the pie is circular
    plt.title(f'Recommendation Details')  # Add a title to the chart

    # Save the chart to a BytesIO stream for temporary storage
    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    # Save the chart to the server with a unique filename
    image_filename = f'chart_{buy_count}_{neutral_count}_{sell_count}.png'
    image_path = f'./{image_filename}'
    plt.savefig(image_path, format='png')
    plt.clf()  # Clear the plot for future charts

    return image_filename  # Return the filename for use in responses

# Run the Flask application on localhost at port 5000
if __name__ == '__main__':
    app.run(host='localhost', port=5000)
