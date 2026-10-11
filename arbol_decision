import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RNG = np.random.default_rng(42)
RUTA_CSV = "data/demanda_estaciones.csv"


def generar_dataset(n=5000):
    """Genera una muestra sintética de registros de afluencia por estación."""
    estaciones = {"Portal Norte": 1.3, "Calle 72": 1.0, "Av. Jiménez": 1.1,
                  "Museo del Oro": 0.8, "Portal Sur": 1.4, "Alcalá": 0.6}
    nombres = list(estaciones)
    df = pd.DataFrame({
        "estacion": RNG.choice(nombres, n),
        "hora": RNG.integers(5, 23, n),
        "dia_semana": RNG.integers(0, 7, n),          # 0 = lunes
        "lluvia": RNG.choice([0, 1], n, p=[0.7, 0.3]),
        "festivo": RNG.choice([0, 1], n, p=[0.93, 0.07]),
        "evento_cercano": RNG.choice([0, 1], n, p=[0.92, 0.08]),
        "buses_disponibles": RNG.integers(10, 41, n),
    })
    hora_pico = df["hora"].isin([6, 7, 8, 17, 18, 19]).astype(int)
    laboral = (df["dia_semana"] < 5).astype(int)
    peso = df["estacion"].map(estaciones)
    score = (40 * hora_pico * laboral + 8 * peso * 5
             + 12 * df["lluvia"] + 25 * df["evento_cercano"]
             - 30 * df["festivo"] - 0.6 * df["buses_disponibles"]
             + RNG.normal(0, 8, n))
    df["pasajeros_estimados"] = np.clip(score * 10 + 200, 30, None).round().astype(int)
    df["demanda"] = pd.cut(score, bins=[-np.inf, 45, 75, np.inf],
                           labels=["BAJA", "MEDIA", "ALTA"])
    return df


def main():
    df = generar_dataset()
    df.to_csv(RUTA_CSV, index=False)
    print("Dataset:", df.shape)
    print(df["demanda"].value_counts(), "\n")

    X = pd.get_dummies(df.drop(columns=["demanda", "pasajeros_estimados"]),
                       columns=["estacion"])
    y = df["demanda"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)

    arbol = DecisionTreeClassifier(max_depth=5, min_samples_leaf=20, random_state=42)
    arbol.fit(X_tr, y_tr)
    pred = arbol.predict(X_te)
    print("== Árbol de decisión ==")
    print("Exactitud:", round(accuracy_score(y_te, pred), 3))
    print("CV (5 folds):", cross_val_score(arbol, X, y, cv=5).round(3))
    print(classification_report(y_te, pred))
    print("Matriz de confusión:\n", confusion_matrix(y_te, pred, labels=["BAJA", "MEDIA", "ALTA"]))

    print("\nReglas aprendidas:\n", export_text(arbol, feature_names=list(X.columns), max_depth=3))

    bosque = RandomForestClassifier(n_estimators=200, random_state=42).fit(X_tr, y_tr)
    print("== Random Forest ==")
    print("Exactitud:", round(accuracy_score(y_te, bosque.predict(X_te)), 3))

    imp = pd.Series(arbol.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\nImportancia de variables (árbol):\n", imp.head(6).round(3))

    plt.figure(figsize=(22, 10))
    plot_tree(arbol, feature_names=list(X.columns), class_names=arbol.classes_,
              filled=True, max_depth=3, fontsize=8)
    plt.savefig("arbol_decision.png", dpi=120, bbox_inches="tight")

    # Prueba puntual
    caso = pd.DataFrame([{c: 0 for c in X.columns}])
    caso.loc[0, ["hora", "dia_semana", "lluvia", "buses_disponibles", "estacion_Portal Norte"]] = [7, 1, 1, 15, 1]
    print("\nPredicción caso (Portal Norte, martes 7am, lluvia, 15 buses):", arbol.predict(caso)[0])


if __name__ == "__main__":
    main()
