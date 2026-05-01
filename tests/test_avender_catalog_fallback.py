from usr.plugins.avender.helpers.catalog_engine import CatalogEngine


def test_fallback_parser_filters_noise_lines():
    engine = CatalogEngine()
    text = "\n".join(
        [
            "$ 9.75",
            "Frutas Flambé $9.75",
            "### $12.00",
            "Pavlova $9.75",
            "---- $7.00",
            "Ceviche Santa Lucía $27.25",
        ]
    )

    items = engine._fallback_parse_catalog(text)
    names = [item["name"] for item in items]

    assert "Frutas Flambé" in names
    assert "Pavlova" in names
    assert "Ceviche Santa Lucía" in names
    assert "$" not in names
    assert "###" not in names
    assert "----" not in names


def test_fallback_parser_handles_dual_price_rows():
    engine = CatalogEngine()
    text = (
        "Macallan 15 años $585.00 $47.75 Cihuatán Nikté $310.00 $34.00\n"
        "SCALLOPS A LA PARMESANA $13.50 ENSALADA DE SALMÓN $18.25\n"
    )

    items = engine._fallback_parse_catalog(text)
    assert len(items) == 4
    assert items[0]["name"] == "Macallan 15 años"
    assert items[0]["price"] == 585.0
    assert items[0]["metadata"]["secondary_price"] == 47.75
    assert items[1]["name"] == "Cihuatán Nikté"
    assert items[1]["price"] == 310.0
    assert items[1]["metadata"]["secondary_price"] == 34.0


def test_fallback_parser_supports_decimal_prices_without_currency_symbol():
    engine = CatalogEngine()
    text = "Producto A 12.50 Producto B 8.00"
    items = engine._fallback_parse_catalog(text)
    names = [x["name"] for x in items]
    assert "Producto A" in names
    assert "Producto B" in names


def test_fallback_parser_ignores_plain_integer_noise():
    engine = CatalogEngine()
    text = "Menu 2024 Seccion 11 Pagina 5"
    items = engine._fallback_parse_catalog(text)
    assert items == []


def test_structured_parser_handles_integer_prices_in_spreadsheet_csv():
    engine = CatalogEngine()
    text = "\n".join(
        [
            "Producto,Precio,Descripción,Stock",
            "Aceite de CBD 500mg,49,Gotero de espectro completo 30ml,12",
            "Gomitas Relajantes,35,Frasco con 30 gomitas de CBD,25",
        ]
    )
    items = engine._parse_structured_catalog(text)

    assert len(items) == 2
    assert items[0]["name"] == "Aceite de CBD 500mg"
    assert items[0]["price"] == 49.0
    assert items[0]["description"] == "Gotero de espectro completo 30ml"
    assert items[0]["metadata"]["Stock"] == "12"


def test_structured_parser_returns_empty_without_name_or_price_columns():
    engine = CatalogEngine()
    text = "\n".join(
        [
            "A,B,C",
            "x,1,y",
            "z,2,w",
        ]
    )
    items = engine._parse_structured_catalog(text)
    assert items == []
