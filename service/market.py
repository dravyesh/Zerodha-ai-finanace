import yfinance as yf
import pandas as pd
#taking data from the portfolios
def get_current_price(symbol):
    try:
        stock = yf.Ticker(f"{symbol}.NS")
        history = stock.history(period = "1d") #give latest price of one day ago
        if history.empty:
            return None
        current_price = history["close"].iloc[-1] #give last data
        return round(current_price,2)
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None

def updated_current_price(df):
    current_price = []
    for symbol in df["stock symbol"]:
        price = get_current_price(symbol)
        current_price.append(price)
    df["Current Price"] = current_price
    return df

def get_stock_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {"company name": info.get("longname"),
                "Current Price": info.get("currentPrice"),
                "sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Markey Cap": info.get("marketCap"),
                "PE Ratio": info.get("trailling PE")}

    except Exception as e:
        print(f"Error feching data for {symbol} : {e}")
        return {}