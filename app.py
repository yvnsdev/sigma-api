# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # Importa CORS
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, static_folder = 'static')
CORS(app)

# Cargar modelos y encoder
model_triage = joblib.load('model_triage.pkl')
model_mortality = joblib.load('model_mortality.pkl')
le = joblib.load('label_encoder.pkl')

# Base de datos en memoria para pacientes
pacientes_db = []
current_id = 0

# Colores de triage según sistema chileno
TRIAGE_COLORS = {
    1: 'Rojo',
    2: 'Naranjo',
    3: 'Amarillo',
    4: 'Verde',
    5: 'Azul'
}

@app.route('/')
def serve_index():
    return send_from_directory('templates', 'index.html')

@app.route('/predict', methods=['POST'])
def predict():
    global current_id
    
    try:
        data = request.get_json()
        
        # Validar datos mínimos requeridos
        required_fields = ['edad', 'sexo', 'presion_sistolica', 'presion_diastolica', 
                          'frecuencia_cardiaca', 'temperatura', 'saturacion_o2', 
                          'nivel_conciencia']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido faltante: {field}'}), 400
        
        # Preparar datos para el modelo
        input_data = {
            'edad': [int(data['edad'])],
            'presion_sistolica': [int(data['presion_sistolica'])],
            'presion_diastolica': [int(data['presion_diastolica'])],
            'frecuencia_cardiaca': [int(data['frecuencia_cardiaca'])],
            'temperatura': [float(data['temperatura'])],
            'saturacion_o2': [float(data['saturacion_o2'])],
            'nivel_conciencia': [le.transform([data['nivel_conciencia']])[0]],
            'tiempo_evolucion_horas': [int(data.get('tiempo_evolucion_horas', 0))],
            'dolor_toracico': [int(data.get('dolor_toracico', 0))],
            'disnea': [int(data.get('disnea', 0))],
            'fiebre': [int(data.get('fiebre', 0))],
            'trauma_reciente': [int(data.get('trauma_reciente', 0))],
            'sangrado_activo': [int(data.get('sangrado_activo', 0))],
            'antecedentes_cronicos': [int(data.get('antecedentes_cronicos', 0))],
        }
        
        df_input = pd.DataFrame(input_data)
        
        # Hacer predicciones
        triage_pred = int(model_triage.predict(df_input)[0])
        mortality_pred = float(model_mortality.predict(df_input)[0])
        triage_pred = int(model_triage.predict(df_input)[0]) + 1
        
        # Registrar paciente
        current_id += 1
        paciente = {
            'id': current_id,
            'fecha_ingreso': datetime.now().isoformat(),
            'datos_clinicos': data,
            'triage_pred': triage_pred,
            'mortality_pred': mortality_pred,
            'atendido': False
        }
        
        pacientes_db.append(paciente)
        
        # Obtener posición en ranking
        pacientes_ordenados = sorted(
            pacientes_db, 
            key=lambda x: (x['triage_pred'], -x['mortality_pred']), 
            reverse=False
        )
        
        ranking = next(
            (i+1 for i, p in enumerate(pacientes_ordenados) if p['id'] == current_id), 
            len(pacientes_ordenados))
        
        return jsonify({
            'id': current_id,
            'nivel_triage': triage_pred,
            'color_triage': TRIAGE_COLORS.get(triage_pred, 'Desconocido'),
            'riesgo_mortalidad': mortality_pred,
            'ranking': ranking,
            'total_pacientes': len(pacientes_db)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ranking', methods=['GET'])
def get_ranking():
    try:
        pacientes_ordenados = sorted(
            pacientes_db, 
            key=lambda x: (x['triage_pred'], -x['mortality_pred']), 
            reverse=False
        )
        
        ranking_data = []
        for i, paciente in enumerate(pacientes_ordenados):
            ranking_data.append({
                'posicion': i+1,
                'id': paciente['id'],
                'nivel_triage': paciente['triage_pred'],
                'color_triage': TRIAGE_COLORS.get(paciente['triage_pred'], 'Desconocido'),
                'riesgo_mortalidad': paciente['mortality_pred'],
                'edad': paciente['datos_clinicos']['edad'],
                'sexo': paciente['datos_clinicos']['sexo'],
                'atendido': paciente['atendido']
            })
        
        # Estadísticas básicas
        stats = {
            'total_pacientes': len(pacientes_db),
            'por_triage': defaultdict(int),
            'atendidos': sum(1 for p in pacientes_db if p['atendido']),
            'no_atendidos': sum(1 for p in pacientes_db if not p['atendido'])
        }
        
        for p in pacientes_db:
            stats['por_triage'][p['triage_pred']] += 1
        
        return jsonify({
            'ranking': ranking_data,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/marcar_atendido/<int:paciente_id>', methods=['POST'])
def marcar_atendido(paciente_id):
    try:
        for paciente in pacientes_db:
            if paciente['id'] == paciente_id:
                paciente['atendido'] = True
                return jsonify({'success': True})
        
        return jsonify({'error': 'Paciente no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)