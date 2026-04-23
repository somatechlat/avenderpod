import pandas as pd

data = {
    "Producto": ["Aceite de CBD 500mg", "Gomitas Relajantes", "Bálsamo Muscular CBD", "Flores Aromáticas"],
    "Precio": [25.50, 15.00, 20.00, 10.00],
    "Descripción": ["Gotero de espectro completo 30ml", "Frasco con 30 gomitas de CBD", "Crema para dolores", "Cepa relajante 1g"],
    "Stock": [50, 100, 30, 20]
}

df = pd.DataFrame(data)
df.to_excel("mock_catalog.xlsx", index=False)
print("Created mock_catalog.xlsx successfully")
