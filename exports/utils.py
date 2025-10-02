import matplotlib.pyplot as plt
from io import BytesIO

def generate_revenue_chart(data):
    """data = {'2021': 1000, '2022': 1200, '2023': 900}"""
    fig, ax = plt.subplots()
    ax.plot(list(data.keys()), list(data.values()), marker="o")
    ax.set_title("Revenue")
    ax.set_ylabel("CZK")

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    return buffer
