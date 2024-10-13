from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
from prisma import Prisma, register
from prisma.models import TradeHistory, Portfolio
import asyncio

app = Flask(__name__)
CORS(app)

@app.route('/api/stock-price', methods=['GET'])
def get_stock_price():
    symbol = request.args.get('symbol', '')
    if not symbol:
        return jsonify({"error": "No stock symbol provided"}), 400

    try:
        ticker = yf.Ticker(symbol)
        current_price = ticker.info['currentPrice']
        return jsonify({
            "symbol": symbol.upper(),
            "price": current_price
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stock price: {str(e)}"}), 500

@app.route('/api/search', methods=['GET'])
def search_stocks():
    query = request.args.get('q', '')
    time_range = request.args.get('range', 'month')  # Default to month if not specified
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    try:
        # Search for stocks
        ticker = yf.Ticker(query)
        info = ticker.info
        
        # Determine the start date based on the time range
        end_date = datetime.now()
        if time_range == 'day':
            start_date = end_date - timedelta(days=1)
            interval = '1d'
        elif time_range == 'week':
            start_date = end_date - timedelta(weeks=1)
            interval = '1d'
        elif time_range == 'month':
            start_date = end_date - timedelta(days=30)
            interval = '1d'
        elif time_range == '6months':
            start_date = end_date - timedelta(days=180)
            interval = '1mo'
        elif time_range == 'year':
            start_date = end_date - timedelta(days=365)
            interval = '3mo'
        elif time_range == '5years':
            start_date = end_date - timedelta(days=1825)
            interval = '3mo'
        else:
            return jsonify({"error": "Invalid time range"}), 400

        # Fetch the historical data
        history = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if len(history) >= 2:
            yesterday_close = history.iloc[-2]['Close']
            current_price = history.iloc[-1]['Close']
            percent_change = ((current_price - yesterday_close) / yesterday_close) * 100
        else:
            percent_change = None

        # Prepare historical data for the chart
        chart_data = [
            {"date": date.strftime("%Y-%m-%d %H:%M:%S"), "price": round(row['Close'], 2)}
            for date, row in history.iterrows()
        ]

        # Extract relevant information
        stock_info = {
            "symbol": info.get("symbol"),
            "name": info.get("longName"),
            "price": info.get("currentPrice") or current_price,
            "change": percent_change,
            "chartData": chart_data
        }

        return jsonify(stock_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio', methods=['GET'])
async def get_portfolio():
    print('api to get portfolio called')
    prisma = Prisma()
    await prisma.connect()
    
    try:
        portfolio = await prisma.portfolio.find_many()
        result = []
        
        for item in portfolio:
            try:
                stock = yf.Ticker(item.symbol)
                info = stock.info
                current_price = info.get('regularMarketPrice') or info.get('currentPrice')
                
                if current_price is None:
                    raise ValueError(f"Unable to fetch current price for {item.symbol}")
                
                change = ((current_price - item.averagePrice) / item.averagePrice) * 100

                result.append({
                    'symbol': item.symbol,
                    'name': info.get('longName', 'Unknown'),
                    'shares': item.quantity,
                    'price': current_price,
                    'change': round(change, 2),
                    'avg_price':  round(item.averagePrice,2),
                    'value': round(current_price * item.quantity, 2)
                })
            except Exception as e:
                print(f"Error processing {item.symbol}: {str(e)}")
                # Optionally, add a placeholder entry or skip this stock
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        await prisma.disconnect()

@app.route('/api/buy', methods=['POST'])
async def buy_stock():
    prisma = Prisma()
    await prisma.connect()
    
    try:
        data = request.json
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        
        if not symbol or not quantity:
            return jsonify({"error": "Symbol and quantity are required"}), 400
        
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({"error": "Quantity must be positive"}), 400
        
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            
            if current_price is None:
                raise ValueError(f"Unable to fetch current price for {symbol}")
        except Exception as e:
            return jsonify({"error": f"Error fetching stock data: {str(e)}"}), 500
        
        # Record the trade
        trade = await prisma.tradehistory.create({
            'symbol': symbol,
            'quantity': quantity,
            'price': current_price,
            'action': 'buy',
            'timestamp': datetime.now()
        })
        
        # Update or create portfolio entry
        portfolio_item = await prisma.portfolio.find_first(where={'symbol': symbol})
        if portfolio_item:
            new_quantity = portfolio_item.quantity + quantity
            new_avg_price = ((portfolio_item.quantity * portfolio_item.averagePrice) + (quantity * current_price)) / new_quantity
            await prisma.portfolio.update(
                where={'id': portfolio_item.id},
                data={
                    'quantity': new_quantity,
                    'averagePrice': new_avg_price
                }
            )
        else:
            await prisma.portfolio.create({
                'symbol': symbol,
                'quantity': quantity,
                'averagePrice': current_price
            })
        
        return jsonify({
            "message": f"Successfully bought {quantity} shares of {symbol}",
            "trade_id": trade.id
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        await prisma.disconnect()

@app.route('/api/sell', methods=['POST'])
async def sell_stock():
    prisma = Prisma()
    await prisma.connect()
    
    try:
        data = request.json
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        
        if not symbol or not quantity:
            return jsonify({"error": "Symbol and quantity are required"}), 400
        
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({"error": "Quantity must be positive"}), 400
        
        portfolio_item = await prisma.portfolio.find_first(where={'symbol': symbol})
        if not portfolio_item or portfolio_item.quantity < quantity:
            return jsonify({"error": "Not enough shares to sell"}), 400
        
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            
            if current_price is None:
                raise ValueError(f"Unable to fetch current price for {symbol}")
        except Exception as e:
            return jsonify({"error": f"Error fetching stock data: {str(e)}"}), 500
        
        # Record the trade
        trade = await prisma.tradehistory.create({
            'symbol': symbol,
            'quantity': quantity,
            'price': current_price,
            'action': 'sell',
            'timestamp': datetime.now()
        })
        
        # Update portfolio
        new_quantity = portfolio_item.quantity - quantity
        if new_quantity == 0:
            await prisma.portfolio.delete(where={'id': portfolio_item.id})
        else:
            await prisma.portfolio.update(
                where={'id': portfolio_item.id},
                data={'quantity': new_quantity}
            )
        
        return jsonify({
            "message": f"Successfully sold {quantity} shares of {symbol}",
            "trade_id": trade.id
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        await prisma.disconnect()

@app.route('/api/trade-history', methods=['GET'])
async def get_trade_history():
    prisma = Prisma()
    await prisma.connect()
    
    try:
        trades = await prisma.tradehistory.find_many(
            order={'timestamp': 'desc'}
        )
        
        result = []
        for trade in trades:
            result.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'quantity': trade.quantity,
                'price': trade.price,
                'action': trade.action,
                'timestamp': trade.timestamp.isoformat()
            })
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        await prisma.disconnect()

if __name__ == '__main__':
    app.run(debug=True)