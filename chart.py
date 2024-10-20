import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def parse_csv(file_path):
    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = []
        for row in reader:
            if row:
                data.append(row)
        return data


def chart_data(file_path):
    data = parse_csv(file_path)

    # Convert the 'Month' column to datetime objects (format: "Month Year")
    dates = [datetime.strptime(row['Month'], '%B %Y') for row in data]
    player_counts = [float(row['Avg_Players']) for row in data]
    dates = [row['Month'] for row in data]  # Replace 'Date' with the actual date column name

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.bar(dates, player_counts, color='blue')

    # Set the title and labels
    plt.title('War Thunder Player Count Over Time')
    plt.xlabel('Date')
    plt.ylabel('Player Count')

    # Set major ticks for every year and format them
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    # Set minor ticks for every month
    plt.gca().xaxis.set_minor_locator(mdates.MonthLocator())

    # Hide the minor tick labels
    plt.gca().tick_params(axis='x', which='minor', length=0)

    # Rotate the major tick labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Adjust layout to avoid label overlap
    plt.tight_layout()

    # Show the chart
    plt.show()


if __name__ == "__main__":
    chart_data('charts_data.csv')