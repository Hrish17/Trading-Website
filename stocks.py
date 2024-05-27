import csv

csv_file_path = './static/ind_nifty50list.csv'
stocks_list = []
with open(csv_file_path, mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        stocks_list.append(row)