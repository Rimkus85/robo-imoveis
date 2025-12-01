#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard do Robô de Monitoramento de Oportunidades Imobiliárias - Senador Canedo
Interface web para visualização dos dados coletados
"""

from flask import Flask, render_template_string, jsonify, request
import sqlite3
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

class DashboardRobo:
    def __init__(self):
        self.db_path = '/home/ubuntu/oportunidades_senador_canedo.db'
    
    def get_connection(self):
        """Retorna conexão com o banco de dados"""
        return sqlite3.connect(self.db_path)
    
    def get_oportunidades_recentes(self, dias=7):
        """Busca oportunidades dos últimos N dias"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            data_limite = datetime.now() - timedelta(days=dias)
            
            cursor.execute('''
                SELECT * FROM oportunidades 
                WHERE data_encontrado >= ? 
                ORDER BY score DESC, data_encontrado DESC
            ''', (data_limite.strftime('%Y-%m-%d %H:%M:%S'),))
            
            colunas = [desc[0] for desc in cursor.description]
            oportunidades = [dict(zip(colunas, row)) for row in cursor.fetchall()]
            
            conn.close()
            return oportunidades
        
        except Exception as e:
            print(f"Erro ao buscar oportunidades: {e}")
            return []
    
    def get_estatisticas(self):
        """Retorna estatísticas gerais"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total de oportunidades
            cursor.execute('SELECT COUNT(*) FROM oportunidades')
            total_oportunidades = cursor.fetchone()[0]
            
            # Oportunidades por portal
            cursor.execute('''
                SELECT portal, COUNT(*) as total 
                FROM oportunidades 
                GROUP BY portal
            ''')
            por_portal = dict(cursor.fetchall())
            
            # Oportunidades por bairro
            cursor.execute('''
                SELECT bairro, COUNT(*) as total 
                FROM oportunidades 
                WHERE bairro != "" 
                GROUP BY bairro 
                ORDER BY total DESC 
                LIMIT 10
            ''')
            por_bairro = dict(cursor.fetchall())
            
            # Média de score
            cursor.execute('SELECT AVG(score) FROM oportunidades WHERE score > 0')
            media_score = cursor.fetchone()[0] or 0
            
            # Preço médio por m²
            cursor.execute('SELECT AVG(preco_m2) FROM oportunidades WHERE preco_m2 > 0')
            preco_medio_m2 = cursor.fetchone()[0] or 0
            
            # Últimas varreduras
            cursor.execute('''
                SELECT * FROM historico_varreduras 
                ORDER BY data_varredura DESC 
                LIMIT 10
            ''')
            colunas = [desc[0] for desc in cursor.description]
            ultimas_varreduras = [dict(zip(colunas, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'total_oportunidades': total_oportunidades,
                'por_portal': por_portal,
                'por_bairro': por_bairro,
                'media_score': round(media_score, 1),
                'preco_medio_m2': round(preco_medio_m2, 2),
                'ultimas_varreduras': ultimas_varreduras
            }
        
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
            return {}

dashboard = DashboardRobo()

# Template HTML do dashboard
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Robô Senador Canedo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f6fa;
            color: #2c3e50;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            font-size: 1rem;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .section {
            background: white;
            margin-bottom: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .section-header {
            background: #34495e;
            color: white;
            padding: 1rem 1.5rem;
            font-size: 1.2rem;
            font-weight: bold;
        }
        
        .section-content {
            padding: 1.5rem;
        }
        
        .oportunidade {
            border: 1px solid #ecf0f1;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        
        .oportunidade:hover {
            border-color: #667eea;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
        }
        
        .oportunidade-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }
        
        .oportunidade-titulo {
            font-size: 1.2rem;
            font-weight: bold;
            color: #2c3e50;
            flex: 1;
            margin-right: 1rem;
        }
        
        .score-badge {
            background: linear-gradient(135deg, #00b894, #00cec9);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
        }
        
        .portal-badge {
            background: #667eea;
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
            display: inline-block;
        }
        
        .preco {
            font-size: 1.5rem;
            font-weight: bold;
            color: #e74c3c;
            margin: 0.5rem 0;
        }
        
        .detalhes {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .detalhe-item {
            display: flex;
            align-items: center;
            color: #7f8c8d;
        }
        
        .detalhe-label {
            font-weight: bold;
            margin-right: 0.5rem;
        }
        
        .chart-container {
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #7f8c8d;
        }
        
        .no-data {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            padding: 2rem;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 25px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 2rem;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .table th,
        .table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .table th {
            background: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .status-success {
            color: #00b894;
            font-weight: bold;
        }
        
        .status-error {
            color: #e74c3c;
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .oportunidade-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .score-badge {
                margin-top: 0.5rem;
            }
            
            .detalhes {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 Dashboard Robô Senador Canedo</h1>
        <p>Monitoramento de Oportunidades Imobiliárias</p>
        <p>Última atualização: {{ datetime.now().strftime('%d/%m/%Y %H:%M:%S') }}</p>
    </div>
    
    <div class="container">
        <button class="refresh-btn" onclick="location.reload()">🔄 Atualizar Dashboard</button>
        
        <!-- Estatísticas Gerais -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_oportunidades }}</div>
                <div class="stat-label">Total de Oportunidades</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.media_score }}</div>
                <div class="stat-label">Score Médio</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">R$ {{ "{:,.0f}".format(stats.preco_medio_m2).replace(',', '.') }}</div>
                <div class="stat-label">Preço Médio/m²</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.por_portal|length }}</div>
                <div class="stat-label">Portais Monitorados</div>
            </div>
        </div>
        
        <!-- Oportunidades por Portal -->
        <div class="section">
            <div class="section-header">📊 Oportunidades por Portal</div>
            <div class="section-content">
                {% if stats.por_portal %}
                    <div class="detalhes">
                        {% for portal, total in stats.por_portal.items() %}
                        <div class="detalhe-item">
                            <span class="detalhe-label">{{ portal }}:</span>
                            <span>{{ total }} oportunidades</span>
                        </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="no-data">Nenhum dado disponível</div>
                {% endif %}
            </div>
        </div>
        
        <!-- Top Bairros -->
        <div class="section">
            <div class="section-header">🏘️ Top Bairros</div>
            <div class="section-content">
                {% if stats.por_bairro %}
                    <div class="detalhes">
                        {% for bairro, total in stats.por_bairro.items() %}
                        <div class="detalhe-item">
                            <span class="detalhe-label">{{ bairro }}:</span>
                            <span>{{ total }} oportunidades</span>
                        </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="no-data">Nenhum dado disponível</div>
                {% endif %}
            </div>
        </div>
        
        <!-- Oportunidades Recentes -->
        <div class="section">
            <div class="section-header">🔥 Oportunidades Recentes (Últimos 7 dias)</div>
            <div class="section-content">
                {% if oportunidades %}
                    {% for oportunidade in oportunidades %}
                    <div class="oportunidade">
                        <div class="portal-badge">{{ oportunidade.portal }}</div>
                        <div class="oportunidade-header">
                            <div class="oportunidade-titulo">{{ oportunidade.titulo }}</div>
                            <div class="score-badge">Score: {{ oportunidade.score }}/100</div>
                        </div>
                        <div class="preco">
                            R$ {{ "{:,.2f}".format(oportunidade.preco).replace(',', 'X').replace('.', ',').replace('X', '.') }}
                        </div>
                        <div class="detalhes">
                            <div class="detalhe-item">
                                <span class="detalhe-label">Endereço:</span>
                                <span>{{ oportunidade.endereco or 'N/A' }}</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Bairro:</span>
                                <span>{{ oportunidade.bairro or 'N/A' }}</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Área:</span>
                                <span>{{ oportunidade.area or 'N/A' }} m²</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Preço/m²:</span>
                                <span>
                                    {% if oportunidade.preco_m2 > 0 %}
                                        R$ {{ "{:,.2f}".format(oportunidade.preco_m2).replace(',', 'X').replace('.', ',').replace('X', '.') }}/m²
                                    {% else %}
                                        N/A
                                    {% endif %}
                                </span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Quartos:</span>
                                <span>{{ oportunidade.quartos or 'N/A' }}</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Banheiros:</span>
                                <span>{{ oportunidade.banheiros or 'N/A' }}</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Vagas:</span>
                                <span>{{ oportunidade.vagas or 'N/A' }}</span>
                            </div>
                            <div class="detalhe-item">
                                <span class="detalhe-label">Encontrado em:</span>
                                <span>{{ oportunidade.data_encontrado }}</span>
                            </div>
                        </div>
                        {% if oportunidade.url %}
                        <div style="margin-top: 1rem;">
                            <a href="{{ oportunidade.url }}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: bold;">
                                🔗 Ver anúncio completo
                            </a>
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-data">Nenhuma oportunidade encontrada nos últimos 7 dias</div>
                {% endif %}
            </div>
        </div>
        
        <!-- Histórico de Varreduras -->
        <div class="section">
            <div class="section-header">📈 Histórico de Varreduras</div>
            <div class="section-content">
                {% if stats.ultimas_varreduras %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Data/Hora</th>
                                <th>Portal</th>
                                <th>Anúncios</th>
                                <th>Oportunidades</th>
                                <th>Tempo (s)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for varredura in stats.ultimas_varreduras %}
                            <tr>
                                <td>{{ varredura.data_varredura }}</td>
                                <td>{{ varredura.portal }}</td>
                                <td>{{ varredura.total_anuncios }}</td>
                                <td>{{ varredura.oportunidades_encontradas }}</td>
                                <td>{{ "{:.1f}".format(varredura.tempo_execucao) }}</td>
                                <td class="{% if 'Sucesso' in varredura.status %}status-success{% else %}status-error{% endif %}">
                                    {{ varredura.status }}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <div class="no-data">Nenhuma varredura registrada</div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def dashboard_home():
    """Página principal do dashboard"""
    try:
        stats = dashboard.get_estatisticas()
        oportunidades = dashboard.get_oportunidades_recentes(7)
        
        return render_template_string(
            DASHBOARD_TEMPLATE,
            stats=stats,
            oportunidades=oportunidades,
            datetime=datetime
        )
    
    except Exception as e:
        return f"Erro ao carregar dashboard: {e}", 500

@app.route('/api/oportunidades')
def api_oportunidades():
    """API para buscar oportunidades"""
    try:
        dias = request.args.get('dias', 7, type=int)
        oportunidades = dashboard.get_oportunidades_recentes(dias)
        return jsonify(oportunidades)
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/estatisticas')
def api_estatisticas():
    """API para buscar estatísticas"""
    try:
        stats = dashboard.get_estatisticas()
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Iniciando Dashboard do Robô Senador Canedo")
    print("📊 Acesse: http://localhost:5000")
    print("🔄 Para parar: Ctrl+C")
    
    # Verifica se o banco existe
    if not os.path.exists('/home/ubuntu/oportunidades_senador_canedo.db'):
        print("⚠️  Banco de dados não encontrado. Execute primeiro o robô principal")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
