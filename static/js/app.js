// static/js/app.js
document.addEventListener('DOMContentLoaded', function() {
    // Variables globales
    let triageChart, mortalityChart;
    
    // Inicializar la aplicación
    init();
    
    // Event listeners
    document.getElementById('pacienteForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('refreshBtn').addEventListener('click', refreshRanking);
    document.getElementById('exportCSV').addEventListener('click', exportToCSV);
    
    // Inicializar gráficos
    function initCharts() {
        const triageCtx = document.getElementById('triageChart').getContext('2d');
        const mortalityCtx = document.getElementById('mortalityChart').getContext('2d');
        
        triageChart = new Chart(triageCtx, {
            type: 'pie',
            data: {
                labels: ['Rojo (1)', 'Naranjo (2)', 'Amarillo (3)', 'Verde (4)', 'Azul (5)'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#dc3545',
                        '#fd7e14',
                        '#ffc107',
                        '#28a745',
                        '#17a2b8'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Distribución de Triage'
                    }
                }
            }
        });
        
        mortalityChart = new Chart(mortalityCtx, {
            type: 'bar',
            data: {
                labels: ['Rojo (1)', 'Naranjo (2)', 'Amarillo (3)', 'Verde (4)', 'Azul (5)'],
                datasets: [{
                    label: 'Riesgo de Mortalidad Promedio',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(54, 162, 235, 0.7)'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Riesgo por Nivel de Triage'
                    }
                }
            }
        });
    }
    
    // Inicializar la aplicación
    function init() {
        initCharts();
        refreshRanking();
    }
    
    // Manejar envío del formulario
    function handleFormSubmit(e) {
        e.preventDefault();
        
        // Validar formulario
        if (!validateForm()) {
            return;
        }
        
        // Obtener datos del formulario
        const formData = {
            edad: parseInt(document.getElementById('edad').value),
            sexo: document.getElementById('sexo').value,
            presion_sistolica: parseInt(document.getElementById('presion_sistolica').value),
            presion_diastolica: parseInt(document.getElementById('presion_diastolica').value),
            frecuencia_cardiaca: parseInt(document.getElementById('frecuencia_cardiaca').value),
            temperatura: parseFloat(document.getElementById('temperatura').value),
            saturacion_o2: parseFloat(document.getElementById('saturacion_o2').value),
            nivel_conciencia: document.getElementById('nivel_conciencia').value,
            tiempo_evolucion_horas: parseInt(document.getElementById('tiempo_evolucion_horas').value) || 0,
            dolor_toracico: document.getElementById('dolor_toracico').checked ? 1 : 0,
            disnea: document.getElementById('disnea').checked ? 1 : 0,
            fiebre: document.getElementById('fiebre').checked ? 1 : 0,
            trauma_reciente: document.getElementById('trauma_reciente').checked ? 1 : 0,
            sangrado_activo: document.getElementById('sangrado_activo').checked ? 1 : 0,
            antecedentes_cronicos: document.getElementById('antecedentes_cronicos').checked ? 1 : 0
        };
        
        // Enviar datos al servidor
        fetch('http://localhost:5000/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            console.log('Respuesta del servidor:', data); // <-- Agrega esto
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                return;
            }
            
            // Mostrar resultados
            showTriageResult(data);
            refreshRanking();
        })
        .catch(error => {
            showAlert('Error al conectar con el servidor: ' + error, 'danger');
        });
    }
    
    // Validar formulario
    function validateForm() {
        const requiredFields = [
            'edad', 'sexo', 'presion_sistolica', 'presion_diastolica',
            'frecuencia_cardiaca', 'temperatura', 'saturacion_o2', 'nivel_conciencia'
        ];
        
        let isValid = true;
        
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (!field.value) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        // Validar rangos
        const satO2 = parseFloat(document.getElementById('saturacion_o2').value);
        if (satO2 < 50 || satO2 > 100) {
            document.getElementById('saturacion_o2').classList.add('is-invalid');
            isValid = false;
        }
        
        const temp = parseFloat(document.getElementById('temperatura').value);
        if (temp < 30 || temp > 45) {
            document.getElementById('temperatura').classList.add('is-invalid');
            isValid = false;
        }
        
        if (!isValid) {
            showAlert('Por favor complete todos los campos requeridos con valores válidos.', 'warning');
        }
        
        return isValid;
    }
    
    // Mostrar resultado del triage
    function showTriageResult(data) {
        const resultadoCard = document.getElementById('resultadoCard');
        const triageResult = document.getElementById('triageResult');
        
        resultadoCard.classList.remove('d-none');
        
        let html = `
            <div class="alert alert-${getTriageClass(data.nivel_triage)} mb-3">
                <h4 class="alert-heading">Nivel de Triage: ${data.nivel_triage} - ${data.color_triage}</h4>
                <p>El paciente ha sido clasificado como <strong>${data.color_triage}</strong> según el sistema de Triage chileno.</p>
            </div>
            
            <div class="mb-3">
                <h5>Riesgo de Mortalidad</h5>
                <div class="progress">
                    <div class="progress-bar bg-danger" role="progressbar" 
                         style="width: ${data.riesgo_mortalidad * 100}%" 
                         aria-valuenow="${data.riesgo_mortalidad * 100}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${(data.riesgo_mortalidad * 100).toFixed(1)}%
                    </div>
                </div>
            </div>
            
            <div class="alert alert-info">
                <p><strong>Posición en ranking:</strong> ${data.ranking} de ${data.total_pacientes}</p>
                <p><strong>ID de paciente:</strong> ${data.id}</p>
            </div>
        `;
        
        triageResult.innerHTML = html;
    }
    
    // Actualizar ranking
    function refreshRanking() {
        fetch('http://localhost:5000/ranking')
        .then(response => response.json())
        .then(data => {
            console.log('Respuesta del servidor:', data); // <-- Agrega esto
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                return;
            }
            
            updateRankingTable(data.ranking);
            updateCharts(data.stats);
        })
        .catch(error => {
            showAlert('Error al obtener ranking: ' + error, 'danger');
        });
    }
    
    // Actualizar tabla de ranking
    function updateRankingTable(rankingData) {
        const tableBody = document.getElementById('rankingTable');
        tableBody.innerHTML = '';
        
        rankingData.forEach(paciente => {
            const row = document.createElement('tr');
            if (paciente.atendido) {
                row.classList.add('table-secondary');
            }
            
            row.innerHTML = `
                <td class="text-center">${paciente.posicion}</td>
                <td>${paciente.id}</td>
                <td><span class="badge badge-triage-${paciente.nivel_triage}">${paciente.nivel_triage} - ${paciente.color_triage}</span></td>
                <td class="text-center">${paciente.edad}</td>
                <td>${paciente.sexo === 'M' ? 'Masculino' : 'Femenino'}</td>
                <td>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar bg-danger" role="progressbar" 
                            style="width: ${paciente.riesgo_mortalidad * 100}%" 
                            aria-valuenow="${paciente.riesgo_mortalidad * 100}" 
                            aria-valuemin="0" 
                            aria-valuemax="100">
                            ${(paciente.riesgo_mortalidad * 100).toFixed(1)}%
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${paciente.atendido ? 'bg-success' : 'bg-warning text-dark'}">
                        ${paciente.atendido ? 'Atendido' : 'En espera'}
                    </span>
                </td>
                <td class="text-center">
                    ${!paciente.atendido ? 
                        `<button class="btn btn-sm btn-success btn-action" 
                                onclick="markAsAttended(${paciente.id})">
                            <i class="bi bi-check-circle"></i>
                        </button>` : 
                        '<span class="text-success"><i class="bi bi-check2-circle"></i></span>'}
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    // Actualizar gráficos
    function updateCharts(stats) {
        // Actualizar gráfico de distribución de triage
        const triageCounts = [0, 0, 0, 0, 0];
        for (const [nivel, count] of Object.entries(stats.por_triage)) {
            triageCounts[nivel-1] = count;
        }
        
        triageChart.data.datasets[0].data = triageCounts;
        triageChart.update();
        
        // Actualizar gráfico de riesgo de mortalidad (simulado)
        const mortalityRisks = [0.1, 0.05, 0.02, 0.005, 0.001]; // Valores de ejemplo
        mortalityChart.data.datasets[0].data = mortalityRisks;
        mortalityChart.update();
    }
    
    // Marcar paciente como atendido
    window.markAsAttended = function(pacienteId) {
        fetch(`http://localhost:5000/marcar_atendido/${pacienteId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            console.log('Respuesta del servidor:', data); // <-- Agrega esto
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
            } else {
                showAlert('Paciente marcado como atendido', 'success');
                refreshRanking();
            }
        })
        .catch(error => {
            showAlert('Error: ' + error, 'danger');
        });
    };
    
    // Exportar a CSV
    function exportToCSV() {
        fetch('http://localhost:5000/ranking')
        .then(response => response.json())
        .then(data => {
            console.log('Respuesta del servidor:', data); // <-- Agrega esto
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                return;
            }
            
            let csvContent = "data:text/csv;charset=utf-8,";
            
            // Encabezados
            csvContent += "Posición,ID,Triage,Color,Edad,Sexo,Riesgo Mortalidad,Estado\n";
            
            // Datos
            data.ranking.forEach(paciente => {
                csvContent += [
                    paciente.posicion,
                    paciente.id,
                    paciente.nivel_triage,
                    paciente.color_triage,
                    paciente.edad,
                    paciente.sexo === 'M' ? 'Masculino' : 'Femenino',
                    paciente.riesgo_mortalidad,
                    paciente.atendido ? 'Atendido' : 'En espera'
                ].join(',') + "\n";
            });
            
            // Descargar archivo
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "ranking_triage.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        })
        .catch(error => {
            showAlert('Error al exportar: ' + error, 'danger');
        });
    }
    
    // Mostrar alerta
    function showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container-fluid');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto cerrar después de 5 segundos
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
    
    // Obtener clase CSS para el nivel de triage
    function getTriageClass(nivel) {
        switch(nivel) {
            case 1: return 'danger';
            case 2: return 'warning';
            case 3: return 'info';
            case 4: return 'success';
            case 5: return 'primary';
            default: return 'secondary';
        }
    }
});