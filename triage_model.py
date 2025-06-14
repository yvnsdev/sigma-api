import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb
import joblib
from sklearn.metrics import classification_report, accuracy_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

# Configuración reproducible
np.random.seed(42)

# Generar datos sintéticos
def generate_synthetic_data(n_samples=10000):
    data = {
        'edad': np.random.randint(0, 100, n_samples),
        'sexo': np.random.choice(['M', 'F'], n_samples),
        'presion_sistolica': np.random.normal(120, 30, n_samples).astype(int),
        'presion_diastolica': np.random.normal(80, 20, n_samples).astype(int),
        'frecuencia_cardiaca': np.random.normal(75, 20, n_samples).astype(int),
        'temperatura': np.random.normal(36.5, 2, n_samples),
        'saturacion_o2': np.random.normal(95, 10, n_samples),
        'nivel_conciencia': np.random.choice(['A', 'V', 'P', 'U'], n_samples, p=[0.85, 0.1, 0.03, 0.02]),
        'tiempo_evolucion_horas': np.random.exponential(24, n_samples).astype(int),
        'dolor_toracico': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'disnea': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        'fiebre': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        'trauma_reciente': np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
        'sangrado_activo': np.random.choice([0, 1], n_samples, p=[0.95, 0.05]),
        'antecedentes_cronicos': np.random.choice([0, 1], n_samples, p=[0.5, 0.5]),
    }
    
    df = pd.DataFrame(data)
    
    # Calcular nivel de triage basado en criterios chilenos (simplificado)
    conditions = [
        # Triage 1 (Rojo - Reanimación)
        ((df['presion_sistolica'] < 90) & (df['presion_diastolica'] < 60)) |
        (df['saturacion_o2'] < 85) |
        (df['nivel_conciencia'].isin(['P', 'U'])) |
        (df['sangrado_activo'] == 1),
        
        # Triage 2 (Naranja - Emergencia)
        ((df['presion_sistolica'] < 100) & (df['presion_diastolica'] < 70)) |
        (df['saturacion_o2'] < 90) |
        (df['nivel_conciencia'] == 'V') |
        (df['dolor_toracico'] == 1) |
        (df['disnea'] == 1) |
        (df['trauma_reciente'] == 1),
        
        # Triage 3 (Amarillo - Urgencia)
        ((df['presion_sistolica'] < 110) & (df['presion_diastolica'] < 80)) |
        (df['saturacion_o2'] < 93) |
        (df['fiebre'] == 1) |
        (df['edad'] > 70) |
        (df['antecedentes_cronicos'] == 1),
        
        # Triage 4 (Verde - Urgencia menor)
        ((df['presion_sistolica'] < 120) & (df['presion_diastolica'] < 85)) |
        (df['saturacion_o2'] < 95),
        
        # Triage 5 (Azul - No urgente)
        True
    ]
    
    choices = [1, 2, 3, 4, 5]
    df['nivel_triage'] = np.select(conditions, choices, default=5)
    
    # Calcular riesgo de mortalidad (simulado)
    mortality_risk = (
        0.1 * (df['nivel_triage'] == 1) +
        0.05 * (df['nivel_triage'] == 2) +
        0.02 * (df['nivel_triage'] == 3) +
        0.005 * (df['nivel_triage'] == 4) +
        0.001 * (df['nivel_triage'] == 5) +
        (100 - df['edad']) / 500 +
        (df['nivel_conciencia'] == 'U') * 0.3 +
        (df['nivel_conciencia'] == 'P') * 0.15 +
        (df['saturacion_o2'] < 85) * 0.25 +
        (df['saturacion_o2'] < 90) * 0.1 +
        np.random.normal(0, 0.01, n_samples)
    )
    
    df['riesgo_mortalidad'] = np.clip(mortality_risk, 0, 1)
    
    return df

# Generar y preparar datos
df = generate_synthetic_data(10000)

# Codificar variables categóricas
le = LabelEncoder()
df['sexo'] = le.fit_transform(df['sexo'])
df['nivel_conciencia'] = le.fit_transform(df['nivel_conciencia'])

# Dividir datos
X = df.drop(['nivel_triage', 'riesgo_mortalidad', 'sexo'], axis=1)
y_triage = df['nivel_triage']
y_mortality = df['riesgo_mortalidad']

X_train, X_test, y_triage_train, y_triage_test, y_mortality_train, y_mortality_test = train_test_split(
    X, y_triage, y_mortality, test_size=0.2, random_state=42
)

# Ajustar etiquetas para XGBoost (convertir 1-5 a 0-4)
y_triage_train_adj = y_triage_train - 1
y_triage_test_adj = y_triage_test - 1

# Entrenar modelo para triage
model_triage = xgb.XGBClassifier(
    objective='multi:softmax',
    num_class=5,
    base_score=0.5,
    random_state=42
)
model_triage.fit(X_train, y_triage_train_adj)

# Función para convertir predicciones de vuelta a 1-5
def adjust_predictions(y_pred):
    return y_pred + 1

# Evaluar modelo de triage
triage_pred_adj = model_triage.predict(X_test)
triage_pred = adjust_predictions(triage_pred_adj)

print("\n=== Evaluación del Modelo de Triage ===")
print("Accuracy Triage:", accuracy_score(y_triage_test, triage_pred))
print("\nReporte de Clasificación:")
print(classification_report(y_triage_test, triage_pred))

# Entrenar modelo para mortalidad
model_mortality = xgb.XGBRegressor(
    objective='reg:squarederror',
    base_score=0.5,
    random_state=42
)
model_mortality.fit(X_train, y_mortality_train)

# Evaluar modelo de mortalidad
mortality_pred = model_mortality.predict(X_test)

print("\n=== Evaluación del Modelo de Mortalidad ===")
print("MSE (Error Cuadrático Medio):", mean_squared_error(y_mortality_test, mortality_pred))
print("MAE (Error Absoluto Medio):", mean_absolute_error(y_mortality_test, mortality_pred))
print("\nEstadísticas de Riesgo:")
print("  - Promedio real:", f"{np.mean(y_mortality_test):.4f}")
print("  - Promedio predicho:", f"{np.mean(mortality_pred):.4f}")
print("  - Diferencia:", f"{np.abs(np.mean(y_mortality_test) - np.mean(mortality_pred)):.4f}")

# Guardar modelos
joblib.dump(model_triage, 'model_triage.pkl')
joblib.dump(model_mortality, 'model_mortality.pkl')
joblib.dump(le, 'label_encoder.pkl')
joblib.dump({'adjust_predictions': adjust_predictions}, 'adjust_functions.pkl')

print("\nModelos entrenados y guardados correctamente!")
print("Archivos generados:")
print("- model_triage.pkl (Modelo de clasificación de triage)")
print("- model_mortality.pkl (Modelo de regresión de mortalidad)")
print("- label_encoder.pkl (Encoder para variables categóricas)")
print("- adjust_functions.pkl (Funciones auxiliares)")