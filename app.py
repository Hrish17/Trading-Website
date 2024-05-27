from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from jugaad_data import nse
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from stocks import stocks_list
from jugaad_data.nse import NSELive
import threading

n = NSELive()
live_stock_data = []

def background_process():
    for i in range(49):
        q = n.stock_quote(stocks_list[i]["Symbol"])
        a = q['priceInfo']
        a['Symbol'] = stocks_list[i]["Symbol"]
        a['Company_Name'] = stocks_list[i]["Company_Name"]
        live_stock_data.append(q['priceInfo'])

background_thread = threading.Thread(target=background_process)
background_thread.start()

def getStockDataDaily(sym):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=100)
    stk_df = nse.stock_df(sym, start_date, end_date)
    stk_data = stk_df[["DATE", "OPEN", "CLOSE", "HIGH", "LOW", "LTP", "VOLUME", "VALUE", "NO OF TRADES"]]
    stk_data["AVG. PRICE"] = stk_data["VALUE"]/stk_data["VOLUME"]
    # print(stk_data)
    return(stk_data)

def getStockDataWeekly(sym):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=500)
    stk_df = nse.stock_df(sym, start_date, end_date)
    stk_data = stk_df[["DATE", "OPEN", "CLOSE", "HIGH", "LOW", "LTP", "VOLUME", "VALUE", "NO OF TRADES"]]
    stk_data["AVG. PRICE"] = stk_data["VALUE"]/stk_data["VOLUME"]
    stk_data = stk_data.reset_index(drop=True)
    stk_data_filtered = stk_data[stk_data.index % 5 == 1]
    return stk_data_filtered

def getStockDataMonthly(sym):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3*365)
    stk_df = nse.stock_df(sym, start_date, end_date)
    stk_data = stk_df[["DATE", "OPEN", "CLOSE", "HIGH", "LOW", "LTP", "VOLUME", "VALUE", "NO OF TRADES"]]
    stk_data["AVG. PRICE"] = stk_data["VALUE"]/stk_data["VOLUME"]
    stk_data = stk_data.reset_index(drop=True)
    stk_data_filtered = stk_data[stk_data.index % 21 == 1]
    return stk_data_filtered

def compareStocks(stk_array):
    l = len(stk_array)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=28)
    stk_data_array = [""]*l
    for i in range(l):
        stk_df = nse.stock_df(stk_array[i], start_date, end_date)
        stk_data = stk_df[["DATE", "OPEN", "CLOSE", "HIGH", "LOW", "LTP", "VOLUME", "VALUE", "NO OF TRADES"]]
        stk_data["AVG. PRICE"] = stk_data["VALUE"]/stk_data["VOLUME"]
        stk_data_array[i] = stk_data
    return stk_data_array

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# Initialize Database within Application Context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('index'))

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'user_id' in session:
        if request.method == 'POST':
            order_by = request.form.get('order')
            filter_by = request.form.get('filter')
            min_value = request.form.get('minValue')
            max_value = request.form.get('maxValue')
            if(min_value == ''): min_value = 0
            if(max_value == ''): max_value = 9999999999
            filtered_data = [stock for stock in live_stock_data if float(stock[filter_by]) >= float(min_value) and float(stock[filter_by]) <= float(max_value)]
            ordered_data = sorted(filtered_data, key=lambda x: x[order_by])

            return render_template('dashboard.html', username=session['username'], data=ordered_data)
        else:
            return render_template('dashboard.html', username=session['username'], data=live_stock_data)
    else:
        return redirect(url_for('index'))
    
@app.route('/<symbol>/daily')
def daily(symbol):
    if 'user_id' in session:
        stk_data = getStockDataDaily(symbol)
        prices = stk_data["AVG. PRICE"].to_numpy()
        dates = stk_data["DATE"].to_numpy()
        fig = go.Figure(data=go.Scatter(x=dates, y=prices,mode='lines',marker=dict(color='red')))
        fig.update_layout(
            hovermode='x unified',
            yaxis_title="Share Price",
            xaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 0
            ),
            yaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 50
            ),
            margin=dict(
                l=50,  # Left margin
                r=50,  # Right margin
                b=50,  # Bottom margin
                t=50,  # Top margin
            ),
        )
        fig.write_html('./static/Images/daily.html')
        return render_template('daily_graph.html')
    else:
        return redirect(url_for('index'))

@app.route('/<symbol>/weekly')
def weekly(symbol):
    if 'user_id' in session:
        stk_data = getStockDataWeekly(symbol)
        prices = stk_data["AVG. PRICE"].to_numpy()
        dates = stk_data["DATE"].to_numpy()
        fig = go.Figure(data=go.Scatter(x=dates, y=prices,mode='lines',marker=dict(color='red')))
        fig.update_layout(
            hovermode='x unified',
            yaxis_title="Share Price",
            xaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 0
            ),
            yaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 50
            ),
            margin=dict(
                l=50,  # Left margin
                r=50,  # Right margin
                b=50,  # Bottom margin
                t=50,  # Top margin
            ),
        )
        fig.write_html('./static/Images/weekly.html')
        return render_template('weekly_graph.html')
    else:
        return redirect(url_for('index'))

@app.route('/<symbol>/monthly')
def monthly(symbol):
    if 'user_id' in session:
        stk_data = getStockDataMonthly(symbol)
        prices = stk_data["AVG. PRICE"].to_numpy()
        dates = stk_data["DATE"].to_numpy()
        fig = go.Figure(data=go.Scatter(x=dates, y=prices,mode='lines',marker=dict(color='red')))
        fig.update_layout(
            hovermode='x unified',
            yaxis_title="Share Price",
            xaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 0
            ),
            yaxis=dict(
                title_font=dict(size=20,color='red'),
                tickfont=dict(size=14,color='blue'),
                # title_standoff = 50
            ),
            margin=dict(
                l=50,  # Left margin
                r=50,  # Right margin
                b=50,  # Bottom margin
                t=50,  # Top margin
            ),
        )
        fig.write_html('./static/Images/monthly.html')
        return render_template('monthly_graph.html')
    else:
        return redirect(url_for('index'))

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user_id' in session:
        if request.method == 'POST':
            order_by = request.form.get('order')
            filter_by = request.form.get('filter')
            min_value = request.form.get('minValue')
            max_value = request.form.get('maxValue')
            if(min_value == ''): min_value = 0
            if(max_value == ''): max_value = 9999999999
            filtered_data = [stock for stock in live_stock_data if float(stock[filter_by]) >= float(min_value) and float(stock[filter_by]) <= float(max_value)]
            ordered_data = sorted(filtered_data, key=lambda x: x[order_by])

            stock_price = []
            for i in range(len(ordered_data)):
                stk_data = getStockDataDaily(ordered_data[i]["Symbol"])
                prices = stk_data["AVG. PRICE"].to_numpy()
                price = round(prices[-1],2)
                stock_price.append(price)
                
            return render_template('compare_stocks.html', data=ordered_data, prices=stock_price)
        else: 
            stocks_price = []
            for i in range(len(stocks_list)):
                stk_data = getStockDataDaily(stocks_list[i]["Symbol"])
                prices = stk_data["AVG. PRICE"].to_numpy()
                price = round(prices[-1],2)
                stocks_price.append(price)
            return render_template('compare_stocks.html', data=stocks_list, prices=stocks_price)
    else:
        return redirect(url_for('index'))

## get api to get stock_list
@app.route('/api/stock_list', methods=['GET'])
def get_stock_list():
    if 'user_id' in session:
        return jsonify(stocks_list)
    else:
        return jsonify({'message': 'You are not logged in'}), 401
    
@app.route('/api/save_selected_stocks', methods=['POST'])
def save_selected_stocks():
    if 'user_id' not in session:
        return jsonify({'message': 'You are not logged in'}), 401
    data = request.get_json()
    selected_stocks = data.get('selectedStocks', [])
    compare_graph_func(selected_stocks)
    return jsonify({'message': 'Selected stocks received successfully'})

@app.route('/compare_graph')
def compare_graph():
    if 'user_id' in session:
        return render_template('compare_graph.html')
    else:
        return redirect(url_for('index'))

# @app.route('/<symbol>/compare_graph')
def compare_graph_func(selected_stocks):
    colors = ['red', 'green', 'blue', 'purple', 'orange']

    fig = go.Figure()

    for symbol, color in zip(selected_stocks, colors):
        stk_data = getStockDataDaily(symbol)
        prices = stk_data["AVG. PRICE"].to_numpy()
        dates = stk_data["DATE"].to_numpy()
        
        fig.add_trace(go.Scatter(x=dates, y=prices, mode='lines', marker=dict(color=color), name=symbol))

    fig.update_layout(
        hovermode='x unified',
        yaxis_title="Share Price",
        xaxis=dict(
            title_font=dict(size=20,color='red'),
            tickfont=dict(size=14,color='blue'),
            # title_standoff = 0
        ),
        yaxis=dict(
            title_font=dict(size=20,color='red'),
            tickfont=dict(size=14,color='blue'),
            # title_standoff = 50
        ),
        margin=dict(
            l=50,  # Left margin
            r=50,  # Right margin
            b=50,  # Bottom margin
            t=50,  # Top margin
        ),
    )

    fig.write_html('./static/Images/compare.html')
    return

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/<name>')
def user(name):
     return render_template('Error404.html')

if __name__ == '__main__':
    app.run(debug=True)
