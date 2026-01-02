from __future__ import annotations

from pathlib import Path
import pandas as pd
import pycountry

# Ścieżki do plików: dane wejściowe i jeden gotowy plik wyjściowy do wizualizacji
DATA_PATH = Path("data/WHR_15_23.csv")
OUT_DIR = Path("out")
OUT_FILE = OUT_DIR / "whr_viz.csv"

# Lista czynników (kolumn), które chcemy zachować w danych
CZYNNIKI = [
    "gdp_per_capita",
    "social_support",
    "healthy_life_expectancy",
    "freedom_to_make_life_choices",
    "generosity",
]

# Ręczne poprawki dla nazw, które nie pasują do bazy pycountry
ISO3_OVERRIDES = {
    "Congo (Brazzaville)": "COG",
    "Congo (Kinshasa)": "COD",
    "Hong Kong S.A.R. of China": "HKG",
    "Ivory Coast": "CIV",
    "Kosovo": "XKX",
    "Palestinian Territories": "PSE",
    "State of Palestine": "PSE",
    "Russia": "RUS",
    "Swaziland": "SWZ",
    "Eswatini": "SWZ",
    "Turkey": "TUR",
    "Turkiye": "TUR",
    "Taiwan Province of China": "TWN",
}

# Byty, które nie mają poligonu "państwa" na mapie świata,
# więc i tak nie będą się dobrze wizualizować jako kraj
NO_POLYGON = {
    "North Cyprus",
    "Somaliland Region",
    "Somaliland region",
}


def to_iso3(country: str) -> str | None:
    """
    Zamienia nazwę kraju na kod ISO-3 (np. Poland -> POL).

    Zasady:
    1) NO_POLYGON -> None
    2) ISO3_OVERRIDES -> wartość z override
    3) w innym przypadku -> pycountry lookup
    """
    if not isinstance(country, str):
        return None

    c = country.strip()
    if not c:
        return None

    if c in NO_POLYGON:
        return None

    if c in ISO3_OVERRIDES:
        return ISO3_OVERRIDES[c]

    try:
        obj = pycountry.countries.lookup(c)
    except LookupError:
        return None

    return getattr(obj, "alpha_3", None)


def main() -> None:
    # Tworzymy katalog wyjściowy, jeśli go nie ma
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Wczytujemy dane z CSV
    df = pd.read_csv(DATA_PATH)

    # Sprawdzamy, czy CSV ma wszystkie potrzebne kolumny
    required = {"country", "region", "year", "happiness_score", *CZYNNIKI}
    missing_cols = sorted(required - set(df.columns))
    if missing_cols:
        raise ValueError(f"Brak wymaganych kolumn w CSV: {missing_cols}")

    # Proste czyszczenie tekstu: usuwamy spacje z początku i końca
    df["country"] = df["country"].astype("string").str.strip()
    df["region"] = df["region"].astype("string").str.strip()

    # Kolumny liczbowe konwertujemy na typ numeryczny,
    # Jeśli są błędy w danych, zamieniamy je na NaN
    num_cols = ["year", "happiness_score", *CZYNNIKI]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Usuwamy rekordy bez podstawowych danych
    df.dropna(subset=["country", "year", "happiness_score"]).copy()

    # Rok ustawiamy jako int i filtrujemy zakres lat 2015-2023
    df["year"] = df["year"].astype(int)
    df = df[df["year"].between(2015, 2023)].copy()

    # Wyznaczamy ISO-3 dla każdego kraju
    df["iso3"] = df["country"].astype(str).apply(to_iso3)

    # Jeśli mamy duplikaty country+year, to:
    # - wartości liczbowe uśredniamy
    # - region i iso3 bierzemy z pierwszego wiersza
    group_cols = ["country", "year"]
    agg = {c: "mean" for c in ["happiness_score", *CZYNNIKI]}
    agg["region"] = "first"
    agg["iso3"] = "first"
    df = df.groupby(group_cols, as_index=False).agg(agg)

    # Sortujemy dla porządku i zapisujemy jeden gotowy plik do wizualizacji
    df = df.sort_values(["year", "country"]).reset_index(drop=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")

    # Wypisujemy brakujące ISO-3 (dla kontroli jakości danych)
    missing_iso = df[df["iso3"].isna()]
    if not missing_iso.empty:
        rows = (
            missing_iso.groupby(["country", "region"])["year"]
            .apply(lambda s: ", ".join(map(str, sorted(pd.unique(s)))))
            .reset_index(name="years")
            .sort_values(["country", "region"])
        )

        print("Brak ISO-3 dla poniższych krajów (country | region | years):")
        for _, r in rows.iterrows():
            print(f"{r['country']} | {r['region']} | {r['years']}")
        print(
            f"Podsumowanie: {len(rows)} krajów bez ISO-3, "
            f"{len(missing_iso)} wierszy bez ISO-3."
        )
    else:
        print("Podsumowanie: wszystkie kraje mają ISO-3.")

    print(f"Saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
