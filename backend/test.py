import pandas as pd

df = pd.DataFrame({
    "id": [1, 2],
    "name": ["Alice", "Bob"],
    "age": [23, 27],
    "score": [88, 92],
    "city": ["Delhi", "Mumbai"]
})

df.to_csv("test.csv", index=False)