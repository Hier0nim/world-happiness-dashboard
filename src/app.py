from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

from prepare_data import main as prepare_data_main, DATA_PATH as RAW_DATA_PATH, OUT_FILE as PREPARED_FILE

TOP_N = 10

# Opisy czynników do osi i etykiet
CZYNNIKI = {
    "gdp_per_capita": "PKB na osobę",
    "social_support": "Wsparcie społeczne",
    "healthy_life_expectancy": "Oczekiwana długosz życia w zdrowiu",
    "freedom_to_make_life_choices": "Wolność wyboru",
    "generosity": "Szczodrość",
}


def ensure_prepared_data() -> Path:
    """Sprawdza, czy gotowy plik istnieje i jest aktualny.
    Jeśli nie, uruchamia przygotowanie danych i zwraca ścieżkę do pliku wynikowego.
    """
    raw_path = Path(RAW_DATA_PATH)
    out_path = Path(PREPARED_FILE)

    # Jeśli brak pliku wyjściowego, to tworzymy go
    if not out_path.exists():
        prepare_data_main()
        return out_path

    # Jeśli surowe dane są nowsze niż plik wyjściowy, to przeliczamy
    try:
        if raw_path.exists() and raw_path.stat().st_mtime > out_path.stat().st_mtime:
            prepare_data_main()
    except OSError:
        # Jeśli nie da się porównać czasów modyfikacji, to po prostu przeliczamy
        prepare_data_main()

    return out_path


# Zapewniamy gotowy plik out/whr_viz.csv
prepared_csv = ensure_prepared_data()

# Wczytujemy już oczyszczone dane (zawiera też iso3)
df = pd.read_csv(prepared_csv)

# Dopinamy typy i usuwamy wiersze bez podstawowych danych
df["country"] = df["country"].astype(str).str.strip()
df["region"] = df["region"].astype(str).str.strip()
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

kolumny_num = ["happiness_score"] + list(CZYNNIKI.keys())
for k in kolumny_num:
    df[k] = pd.to_numeric(df[k], errors="coerce")

df.dropna(subset=["country", "region", "year", "happiness_score"]).copy()
df["year"] = df["year"].astype(int)

# Listy do kontrolek
LATA = sorted([int(y) for y in df["year"].unique()])
REGIONY = sorted(df["region"].unique())
KRAJE = sorted(df["country"].unique())

DOMYSLNY_ROK = max(LATA) if LATA else 2015
DOMYSLNY_CZYNNIK = "gdp_per_capita"
DOMYSLNY_KRAJ = "Switzerland" if "Switzerland" in KRAJE else (KRAJE[0] if KRAJE else "")

# Konfiguracja aplikacji
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Szczęście na świecie (2015-2023)"

# Panel z filtrami globalnymi
panel_globalny = dbc.Card(
    body=True,
    children=[
        dbc.Row(
            className="g-2",
            children=[
                dbc.Col(
                    xs=12,
                    md=3,
                    children=[
                        html.Label("Rok", className="fw-semibold"),
                        dcc.Dropdown(
                            id="rok",
                            options=[{"label": str(y), "value": y} for y in LATA],
                            value=DOMYSLNY_ROK,
                            clearable=False,
                        ),
                    ],
                ),
                dbc.Col(
                    xs=12,
                    md=9,
                    children=[
                        html.Label("Regiony", className="fw-semibold"),
                        dcc.Dropdown(
                            id="regiony",
                            options=[{"label": r, "value": r} for r in REGIONY],
                            value=REGIONY,
                            multi=True,
                        ),
                    ],
                ),
            ],
        ),
    ],
)

# Układ strony (layout)
app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H3("Szczęście na świecie (2015-2023)", className="mt-3"),
        html.Div(
            "Przegląd, zależności, trend kraju i największe zmiany w czasie.",
            className="text-secondary mb-2",
        ),
        panel_globalny,
        dbc.Row(
            className="g-3 mt-2",
            children=[
                dbc.Col(
                    xs=12,
                    lg=7,
                    children=dbc.Card(
                        body=True,
                        children=[
                            html.H5("1) Mapa: poziom szczęścia"),
                            dcc.Graph(
                                id="fig_mapa",
                                config={"displayModeBar": False},
                                style={"height": "60vh"},
                            ),
                        ],
                    ),
                ),
                dbc.Col(
                    xs=12,
                    lg=5,
                    children=dbc.Card(
                        body=True,
                        children=[
                            html.H5("2) Średnia szczęścia w regionach"),
                            dcc.Graph(
                                id="fig_regiony",
                                config={"displayModeBar": False},
                                style={"height": "60vh"},
                            ),
                        ],
                    ),
                ),
            ],
        ),
        dbc.Row(
            className="g-3 mt-1",
            children=[
                dbc.Col(
                    xs=12,
                    lg=7,
                    children=dbc.Card(
                        body=True,
                        children=[
                            html.H5("3) Zależność: szczęście a wybrany czynnik"),
                            dbc.Row(
                                className="g-2 align-items-end",
                                children=[
                                    dbc.Col(
                                        xs=12,
                                        md=6,
                                        children=[
                                            html.Label("Czynnik (os X)", className="fw-semibold"),
                                            dcc.Dropdown(
                                                id="czynnik",
                                                options=[
                                                    {"label": label, "value": col}
                                                    for col, label in CZYNNIKI.items()
                                                ],
                                                value=DOMYSLNY_CZYNNIK,
                                                clearable=False,
                                            ),
                                        ],
                                    ),
                                    dbc.Col(
                                        xs=12,
                                        md=6,
                                        children=html.Div(
                                            "Najedz na punkt, aby zobaczyć kraj.",
                                            className="text-secondary small",
                                            style={"paddingBottom": "6px"},
                                        ),
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="fig_scatter",
                                config={"displayModeBar": False},
                                style={"height": "50vh"},
                            ),
                        ],
                    ),
                ),
                dbc.Col(
                    xs=12,
                    lg=5,
                    children=dbc.Card(
                        body=True,
                        children=[
                            html.H5("4) Trend kraju (2015-2023)"),
                            html.Label("Kraj", className="fw-semibold"),
                            dcc.Dropdown(
                                id="kraj",
                                options=[{"label": c, "value": c} for c in KRAJE],
                                value=DOMYSLNY_KRAJ,
                                clearable=False,
                            ),
                            dcc.Graph(
                                id="fig_kraj",
                                config={"displayModeBar": False},
                                style={"height": "50vh"},
                            ),
                        ],
                    ),
                ),
            ],
        ),
        dbc.Row(
            className="g-3 mt-1 mb-4",
            children=[
                dbc.Col(
                    xs=12,
                    children=dbc.Card(
                        body=True,
                        children=[
                            dbc.Row(
                                className="g-2 align-items-end",
                                children=[
                                    dbc.Col(
                                        xs=12,
                                        md=4,
                                        children=[
                                            html.H5(f"5) Najwieksze zmiany (Top {TOP_N})", className="mb-0"),
                                            html.Div(
                                                "Porównanie wyniku na początku i na końcu zakresu.",
                                                className="text-secondary small",
                                            ),
                                        ],
                                    ),
                                    dbc.Col(
                                        xs=12,
                                        md=8,
                                        children=[
                                            html.Label("Zakres lat (od, do)", className="fw-semibold"),
                                            dcc.RangeSlider(
                                                id="zakres_lat",
                                                min=int(min(LATA)) if LATA else 2015,
                                                max=int(max(LATA)) if LATA else 2023,
                                                step=1,
                                                value=[
                                                    int(min(LATA)) if LATA else 2015,
                                                    int(max(LATA)) if LATA else 2023,
                                                ],
                                                marks={int(y): str(int(y)) for y in (LATA[::2] if LATA else [2015, 2023])},
                                                tooltip={"placement": "bottom"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="fig_delta",
                                config={"displayModeBar": False},
                                style={"height": "45vh"},
                            ),
                        ],
                    ),
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("fig_mapa", "figure"),
    Output("fig_regiony", "figure"),
    Output("fig_scatter", "figure"),
    Output("fig_kraj", "figure"),
    Output("fig_delta", "figure"),
    Input("rok", "value"),
    Input("regiony", "value"),
    Input("czynnik", "value"),
    Input("kraj", "value"),
    Input("zakres_lat", "value"),
)
def aktualizuj_wykresy(rok, regiony, czynnik, kraj, zakres_lat):
    # Jeśli użytkownik odznaczy wszystko, to przyjmujemy wszystkie regiony
    if not regiony:
        regiony = REGIONY

    rok = int(rok)
    od_roku, do_roku = map(int, zakres_lat)
    if od_roku > do_roku:
        od_roku, do_roku = do_roku, od_roku

    d = df[(df["year"] == rok) & (df["region"].isin(regiony))].copy()

    # 1) Mapa
    # Używamy kodów ISO-3, bo są jednoznaczne i działają stabilnie w plotly
    d_map = d.dropna(subset=["iso3"])[["iso3", "happiness_score", "country", "region"]].copy()

    fig_mapa = px.choropleth(
        d_map,
        locations="iso3",
        locationmode="ISO-3",
        color="happiness_score",
        hover_name="country",
        hover_data={"region": True, "happiness_score": ":.3f", "iso3": True},
        color_continuous_scale="Viridis",
        projection="natural earth",
        title=f"Mapa: poziom szczescia ({rok})",
    )
    fig_mapa.update_layout(margin=dict(l=10, r=10, t=50, b=10))

    # 2) Średnia regionów
    srednie = (
        d.groupby("region", as_index=False)["happiness_score"]
        .mean()
        .sort_values("happiness_score", ascending=False)
    )
    fig_regiony = px.bar(
        srednie,
        x="happiness_score",
        y="region",
        orientation="h",
        text=srednie["happiness_score"].round(3),
        title=f"Srednia szczescia w regionach ({rok})",
    )
    fig_regiony.update_traces(textposition="outside", cliponaxis=False)
    fig_regiony.update_layout(margin=dict(l=10, r=10, t=50, b=10), yaxis_title="")

    # 3) Zależność: szczęście a czynnik
    fig_scatter = px.scatter(
        d,
        x=czynnik,
        y="happiness_score",
        color="region",
        hover_name="country",
        opacity=0.85,
        title=f"Szczescie a {CZYNNIKI.get(czynnik, czynnik)} ({rok})",
    )
    fig_scatter.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    fig_scatter.update_xaxes(title=CZYNNIKI.get(czynnik, czynnik))
    fig_scatter.update_yaxes(title="happiness_score")

    # 4) Trend kraju
    d_kraj = df[df["country"] == kraj].sort_values("year")
    fig_kraj = px.line(
        d_kraj,
        x="year",
        y="happiness_score",
        markers=True,
        title=f"Trend szczescia: {kraj}",
    )
    fig_kraj.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    fig_kraj.update_xaxes(dtick=1, title="rok")
    fig_kraj.update_yaxes(title="happiness_score")

    # 5) Największe zmiany w czasie (delta)
    a = df[(df["year"] == od_roku) & (df["region"].isin(regiony))][["country", "happiness_score"]].rename(
        columns={"happiness_score": "start"}
    )
    b = df[(df["year"] == do_roku) & (df["region"].isin(regiony))][["country", "happiness_score"]].rename(
        columns={"happiness_score": "koniec"}
    )

    m = a.merge(b, on="country", how="inner")
    m["delta"] = m["koniec"] - m["start"]

    wzrosty = m.sort_values("delta", ascending=False).head(TOP_N).copy()
    spadki = m.sort_values("delta", ascending=True).head(TOP_N).copy()

    wzrosty["typ"] = "wzrosty"
    spadki["typ"] = "spadki"
    dd = pd.concat([wzrosty, spadki], ignore_index=True).sort_values(["typ", "delta"])

    fig_delta = px.bar(
        dd,
        x="delta",
        y="country",
        orientation="h",
        facet_col="typ",
        text=dd["delta"].round(3),
        title=f"Najwieksze zmiany wyniku ({od_roku} do {do_roku})",
    )
    fig_delta.update_traces(textposition="outside", cliponaxis=False)
    fig_delta.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    fig_delta.update_xaxes(title="zmiana (delta)")
    fig_delta.update_yaxes(title="")

    return fig_mapa, fig_regiony, fig_scatter, fig_kraj, fig_delta


if __name__ == "__main__":
    app.run(debug=True)
