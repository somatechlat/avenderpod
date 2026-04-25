import pandas as pd
import os

data = {
    "Producto": [
        "Aceite de CBD 500mg",
        "Gomitas Relajantes",
        "Bálsamo Muscular CBD",
        "Flores Aromáticas",
    ],
    "Precio": [25.50, 15.00, 20.00, 10.00],
    "Descripción": [
        "Gotero de espectro completo 30ml",
        "Frasco con 30 gomitas de CBD",
        "Crema para dolores",
        "Cepa relajante 1g",
    ],
    "Stock": [50, 100, 30, 20],
}

df = pd.DataFrame(data)
out_path = os.path.join(os.path.dirname(__file__), "mock_catalog.xlsx")
df.to_excel(out_path, index=False)
print(f"Created {out_path} successfully")
