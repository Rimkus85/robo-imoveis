#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Oportunidades Imobiliárias Nacionais
Visualização expandida para monitoramento de múltiplas cidades
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)

def get_db_connection():
    """Conecta ao banco de dados"""
    conn = sqlite3.connect('oportunidades_nacionais.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Dashboard principal"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/oportunidades')
def api_oportunidades():
    """API para obter oportunidades"""
    conn = get_db_connection()
    
    # Oportunidades por categoria de potencial
    oportunidades = conn.execute('''
        SELECT cidade, estado, titulo, preco, area, preco_m2, score, 
               potencial_categoria, portal, data_encontrado
        FROM oportunidades 
        ORDER BY 
            CASE 
                WHEN cidade = 'Lucas do Rio Verde' THEN 1
                WHEN cidade = 'Rio Verde' THEN 2
                WHEN cidade = 'Sinop' THEN 3
                WHEN cidade = 'Barreiras' THEN 4
                WHEN cidade = 'Palmas' THEN 5
                ELSE 6
            END,
            score DESC
        LIMIT 50
    ''').fetchall()
    
    conn.close()
    
    return jsonify([dict(row) for row in oportunidades])

@app.route('/api/estatisticas')
def api_estatisticas():
    """API para estatísticas gerais"""
    conn = get_db_connection()
    
    # Estatísticas por cidade
    stats_cidade = conn.execute('''
        SELECT cidade, estado, COUNT(*) as total, 
               AVG(score) as score_medio,
               AVG(preco_m2) as preco_m2_medio,
               MIN(preco_m2) as menor_preco_m2,
               MAX(preco_m2) as maior_preco_m2
        FROM oportunidades 
        GROUP BY cidade, estado
        ORDER BY 
            CASE 
                WHEN cidade = 'Lucas do Rio Verde' THEN 1
                WHEN cidade = 'Rio Verde' THEN 2
                WHEN cidade = 'Sinop' THEN 3
                WHEN cidade = 'Barreiras' THEN 4
                WHEN cidade = 'Palmas' THEN 5
                ELSE 6
            END
    ''').fetchall()
    
    # Histórico de varreduras
    historico = conn.execute('''
        SELECT cidade, estado, portal, oportunidades_encontradas, 
               tempo_execucao, status, data_varredura
        FROM historico_varreduras 
        ORDER BY data_varredura DESC
        LIMIT 20
    ''').fetchall()
    
    # Total geral
    total_geral = conn.execute('SELECT COUNT(*) as total FROM oportunidades').fetchone()
    
    conn.close()
    
    return jsonify({
        'stats_cidade': [dict(row) for row in stats_cidade],
        'historico': [dict(row) for row in historico],
        'total_geral': dict(total_geral)
    })

@app.route('/api/melhores/<cidade>')
def api_melhores_cidade(cidade):
    """API para melhores oportunidades de uma cidade específica"""
    conn = get_db_connection()
    
    oportunidades = conn.execute('''
        SELECT * FROM oportunidades 
        WHERE cidade = ?
        ORDER BY score DESC
        LIMIT 10
    ''', (cidade,)).fetchall()
    
    conn.close()
    
    return jsonify([dict(row) for row in oportunidades])

# Template HTML expandido
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Oportunidades Imobiliárias Nacionais</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .cidade-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .potencial-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .potencial-ouro { background: #FFD700; color: #B8860B; }
        .potencial-prata { background: #C0C0C0; color: #696969; }
        .potencial-bronze { background: #CD7F32; color: #8B4513; }
        .potencial-regional { background: #87CEEB; color: #4682B4; }
        .potencial-estavel { background: #98FB98; color: #228B22; }
        .potencial-consolidado { background: #DDA0DD; color: #8B008B; }
        
        .oportunidades-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .oportunidade-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }
        
        .oportunidade-header {
            display: flex;
            justify-content: between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        
        .score-badge {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 8px 15px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 0.9em;
        }
        
        .preco-destaque {
            font-size: 1.4em;
            font-weight: bold;
            color: #2E8B57;
            margin: 10px 0;
        }
        
        .detalhes-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        
        .detalhe-item {
            display: flex;
            align-items: center;
            font-size: 0.9em;
            color: #666;
        }
        
        .loading {
            text-align: center;
            color: white;
            font-size: 1.2em;
            margin: 50px 0;
        }
        
        .refresh-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 20px auto;
            display: block;
            transition: transform 0.3s ease;
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        
        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .oportunidades-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Oportunidades Imobiliárias Nacionais</h1>
            <p>Monitoramento inteligente de mercados emergentes em todo o Brasil</p>
            <p id="ultima-atualizacao"></p>
        </div>
        
        <button class="refresh-btn" onclick="carregarDados()">🔄 Atualizar Dados</button>
        
        <div id="loading" class="loading">
            Carregando oportunidades...
        </div>
        
        <div id="estatisticas" class="stats-grid" style="display: none;">
        </div>
        
        <div class="chart-container" style="display: none;" id="chart-container">
            <h3>📊 Distribuição de Oportunidades por Cidade</h3>
            <canvas id="cidadesChart" width="400" height="200"></canvas>
        </div>
        
        <div id="oportunidades" class="oportunidades-grid" style="display: none;">
        </div>
    </div>

    <script>
        let chartInstance = null;
        
        async function carregarDados() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('estatisticas').style.display = 'none';
            document.getElementById('oportunidades').style.display = 'none';
            document.getElementById('chart-container').style.display = 'none';
            
            try {
                const [oportunidades, estatisticas] = await Promise.all([
                    fetch('/api/oportunidades').then(r => r.json()),
                    fetch('/api/estatisticas').then(r => r.json())
                ]);
                
                exibirEstatisticas(estatisticas);
                exibirOportunidades(oportunidades);
                criarGrafico(estatisticas.stats_cidade);
                
                document.getElementById('ultima-atualizacao').textContent = 
                    `Última atualização: ${new Date().toLocaleString('pt-BR')}`;
                
            } catch (error) {
                console.error('Erro ao carregar dados:', error);
                document.getElementById('loading').innerHTML = 
                    '❌ Erro ao carregar dados. Tente novamente.';
            }
        }
        
        function exibirEstatisticas(stats) {
            const container = document.getElementById('estatisticas');
            
            let html = `
                <div class="stat-card">
                    <h3>📊 Resumo Geral</h3>
                    <p><strong>Total de Oportunidades:</strong> ${stats.total_geral.total}</p>
                    <p><strong>Cidades Monitoradas:</strong> ${stats.stats_cidade.length}</p>
                    <p><strong>Última Varredura:</strong> ${new Date().toLocaleString('pt-BR')}</p>
                </div>
            `;
            
            stats.stats_cidade.forEach(cidade => {
                const potencial = getPotencialClass(cidade.cidade);
                const badge = getPotencialBadge(cidade.cidade);
                
                html += `
                    <div class="stat-card">
                        <div class="cidade-header">
                            <h3>📍 ${cidade.cidade}/${cidade.estado}</h3>
                            <span class="potencial-badge ${potencial}">${badge}</span>
                        </div>
                        <p><strong>Oportunidades:</strong> ${cidade.total}</p>
                        <p><strong>Score Médio:</strong> ${cidade.score_medio.toFixed(1)}/100</p>
                        <p><strong>Preço/m² Médio:</strong> R$ ${cidade.preco_m2_medio.toFixed(2)}</p>
                        <p><strong>Faixa de Preços:</strong> R$ ${cidade.menor_preco_m2.toFixed(2)} - R$ ${cidade.maior_preco_m2.toFixed(2)}/m²</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            container.style.display = 'grid';
        }
        
        function exibirOportunidades(oportunidades) {
            const container = document.getElementById('oportunidades');
            
            let html = '';
            
            oportunidades.forEach((op, index) => {
                const potencial = getPotencialClass(op.cidade);
                
                html += `
                    <div class="oportunidade-card">
                        <div class="oportunidade-header">
                            <div>
                                <h4>🏠 ${op.titulo}</h4>
                                <p><strong>📍 ${op.cidade}/${op.estado}</strong></p>
                            </div>
                            <div class="score-badge">
                                ${op.score}/100
                            </div>
                        </div>
                        
                        <div class="preco-destaque">
                            💰 R$ ${op.preco.toLocaleString('pt-BR')}
                        </div>
                        
                        <div class="detalhes-grid">
                            <div class="detalhe-item">
                                📐 <strong>${op.area.toFixed(0)} m²</strong>
                            </div>
                            <div class="detalhe-item">
                                💲 <strong>R$ ${op.preco_m2.toFixed(2)}/m²</strong>
                            </div>
                            <div class="detalhe-item">
                                🎯 <strong>${op.potencial_categoria}</strong>
                            </div>
                            <div class="detalhe-item">
                                🌐 <strong>${op.portal}</strong>
                            </div>
                        </div>
                        
                        <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            📅 Encontrado em: ${new Date(op.data_encontrado).toLocaleDateString('pt-BR')}
                        </p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            container.style.display = 'grid';
            document.getElementById('loading').style.display = 'none';
        }
        
        function criarGrafico(statsCidade) {
            const ctx = document.getElementById('cidadesChart').getContext('2d');
            
            if (chartInstance) {
                chartInstance.destroy();
            }
            
            const labels = statsCidade.map(c => `${c.cidade}/${c.estado}`);
            const data = statsCidade.map(c => c.total);
            const cores = ['#FFD700', '#C0C0C0', '#CD7F32', '#87CEEB', '#98FB98', '#DDA0DD'];
            
            chartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: cores,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
            
            document.getElementById('chart-container').style.display = 'block';
        }
        
        function getPotencialClass(cidade) {
            const classes = {
                'Lucas do Rio Verde': 'potencial-ouro',
                'Rio Verde': 'potencial-prata',
                'Sinop': 'potencial-bronze',
                'Barreiras': 'potencial-regional',
                'Palmas': 'potencial-estavel',
                'Senador Canedo': 'potencial-consolidado'
            };
            return classes[cidade] || 'potencial-estavel';
        }
        
        function getPotencialBadge(cidade) {
            const badges = {
                'Lucas do Rio Verde': '🥇 OURO',
                'Rio Verde': '🥈 PRATA',
                'Sinop': '🥉 BRONZE',
                'Barreiras': '🌎 REGIONAL',
                'Palmas': '📈 ESTÁVEL',
                'Senador Canedo': '✅ CONSOLIDADO'
            };
            return badges[cidade] || '📊 PADRÃO';
        }
        
        // Carrega dados ao inicializar
        document.addEventListener('DOMContentLoaded', carregarDados);
        
        // Auto-refresh a cada 5 minutos
        setInterval(carregarDados, 300000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
