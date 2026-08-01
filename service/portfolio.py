
import pandas as pd

def read_portfolio(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        data = pd.read_excel(uploaded_file)
    else:
        raise ValueError ("unsupported file format")
    return data


def valid_coloumn(data):
    required_column = ["Stock","Quantity","Average Price"]

    missing_column = []

    for column in required_column:
        if column not in data.column:
            missing_column.append(column)
    return missing_column

def clean_data(data):
    data = data.dropna
    data = data.drop_duplicates()
    return data
