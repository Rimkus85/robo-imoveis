#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Plataforma Completa de Oportunidades Imobiliárias
Sistema consolidado com todas as cidades: Senador Canedo + Regionais
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)

def get_db_connection():
    """Conecta ao banco consolidado"""
    conn = sqlite3.connect('plataforma_oportunidades_completa.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Dashboard principal consolidado"""
    return render_template_string(DASHBOARD_CONSOLIDADO_TEMPLATE)

@app.route('/api/oportunidades')
def api_oportunidades():
    """API para obter todas as oportunidades"""
    conn = get_db_connection()
    
    oportunidades = conn.execute('''
        SELECT cidade, estado, titulo, preco, area, preco_m2, score, 
               potencial_categoria, portal, referencia, endereco, bairro,
               quartos, banheiros, vagas, url, data_encontrado
        FROM oportunidades_completas 
        ORDER BY 
            CASE 
                WHEN cidade = 'Lucas do Rio Verde' THEN 1
                WHEN cidade = 'Rio Verde' THEN 2
                WHEN cidade = 'Sinop' THEN 3
                WHEN cidade = 'Barreiras' THEN 4
                WHEN cidade = 'Palmas' THEN 5
                WHEN cidade = 'Senador Canedo' THEN 6
                ELSE 7
            END,
            score DESC
    ''').fetchall()
    
    conn.close()
    
    return jsonify([dict(row) for row in oportunidades])

@app.route('/api/estatisticas')
def api_estatisticas():
    """API para estatísticas consolidadas"""
    conn = get_db_connection()
    
    # Estatísticas por cidade
    stats_cidade = conn.execute('''
        SELECT c.cidade, c.estado, c.total_oportunidades, c.score_medio,
               c.preco_medio, c.preco_m2_medio, c.menor_preco, c.maior_preco,
               c.potencial_categoria, c.crescimento_populacional
        FROM estatisticas_cidades c
        ORDER BY 
            CASE 
                WHEN c.cidade = 'Lucas do Rio Verde' THEN 1
                WHEN c.cidade = 'Rio Verde' THEN 2
                WHEN c.cidade = 'Sinop' THEN 3
                WHEN c.cidade = 'Barreiras' THEN 4
                WHEN c.cidade = 'Palmas' THEN 5
                WHEN c.cidade = 'Senador Canedo' THEN 6
                ELSE 7
            END
    ''').fetchall()
    
    # Histórico consolidado
    historico = conn.execute('''
        SELECT * FROM historico_consolidado 
        ORDER BY data_consolidacao DESC
        LIMIT 10
    ''').fetchall()
    
    # Resumo geral
    resumo = conn.execute('''
        SELECT 
            COUNT(*) as total_oportunidades,
            COUNT(DISTINCT cidade) as total_cidades,
            COUNT(DISTINCT portal) as total_portais,
            AVG(score) as score_medio_geral,
            AVG(preco) as preco_medio_geral,
            MIN(preco) as menor_preco_geral,
            MAX(preco) as maior_preco_geral
        FROM oportunidades_completas
    ''').fetchone()
    
    conn.close()
    
    return jsonify({
        'stats_cidade': [dict(row) for row in stats_cidade],
        'historico': [dict(row) for row in historico],
        'resumo_geral': dict(resumo)
    })

@app.route('/api/cidade/<cidade>')
def api_cidade_detalhes(cidade):
    """API para detalhes de uma cidade específica"""
    conn = get_db_connection()
    
    oportunidades = conn.execute('''
        SELECT * FROM oportunidades_completas 
        WHERE cidade = ?
        ORDER BY score DESC
    ''', (cidade,)).fetchall()
    
    estatisticas = conn.execute('''
        SELECT * FROM estatisticas_cidades 
        WHERE cidade = ?
    ''', (cidade,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'oportunidades': [dict(row) for row in oportunidades],
        'estatisticas': dict(estatisticas) if estatisticas else None
    })

# Template HTML consolidado
DASHBOARD_CONSOLIDADO_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Plataforma Completa de Oportunidades Imobiliárias</title>
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
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.8em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.3em;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        
        .resumo-geral {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .resumo-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .resumo-item {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        
        .resumo-numero {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .resumo-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .cidades-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .cidade-card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .cidade-card:hover {
            transform: translateY(-8px);
        }
        
        .cidade-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .cidade-nome {
            font-size: 1.4em;
            font-weight: bold;
            color: #333;
        }
        
        .potencial-badge {
            padding: 8px 15px;
            border-radius: 25px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .potencial-ouro { background: linear-gradient(45deg, #FFD700, #FFA500); color: #B8860B; }
        .potencial-prata { background: linear-gradient(45deg, #C0C0C0, #A0A0A0); color: #696969; }
        .potencial-bronze { background: linear-gradient(45deg, #CD7F32, #8B4513); color: white; }
        .potencial-regional { background: linear-gradient(45deg, #87CEEB, #4682B4); color: white; }
        .potencial-estavel { background: linear-gradient(45deg, #98FB98, #228B22); color: #006400; }
        .potencial-consolidado { background: linear-gradient(45deg, #DDA0DD, #8B008B); color: white; }
        
        .cidade-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .stat-numero {
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
        
        .crescimento-info {
            background: linear-gradient(45deg, #e3f2fd, #bbdefb);
            padding: 12px;
            border-radius: 10px;
            font-size: 0.9em;
            color: #1565c0;
            text-align: center;
            margin-top: 10px;
        }
        
        .oportunidades-section {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-top: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
        
        .oportunidades-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 25px;
            margin-top: 25px;
        }
        
        .oportunidade-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 25px;
            border-left: 6px solid #667eea;
            transition: transform 0.3s ease;
            cursor: pointer;
            position: relative;
            perspective: 1000px;
            min-height: 320px;
        }
        
        .oportunidade-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .card-inner {
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.6s;
            transform-style: preserve-3d;
        }
        
        .oportunidade-card.flipped .card-inner {
            transform: rotateY(180deg);
        }
        
        .card-front, .card-back {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 15px;
        }
        
        .card-back {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transform: rotateY(180deg);
            padding: 25px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .contato-header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255,255,255,0.3);
        }
        
        .contato-titulo {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .contato-preco {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .contato-info {
            text-align: left;
            margin-bottom: 15px;
        }
        
        .contato-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            padding: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        
        .contato-icon {
            margin-right: 10px;
            font-size: 1.2em;
        }
        
        .contato-link {
            color: #FFD700;
            text-decoration: none;
            font-weight: bold;
        }
        
        .contato-link:hover {
            text-decoration: underline;
        }
        
        .voltar-btn {
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.5);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 15px;
        }
        
        .voltar-btn:hover {
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.8);
        }
        
        .click-hint {
            position: absolute;
            top: 10px;
            right: 15px;
            background: rgba(102, 126, 234, 0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        
        .oportunidade-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        
        .oportunidade-titulo {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        
        .oportunidade-local {
            color: #666;
            font-size: 0.9em;
        }
        
        .score-badge {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 10px 18px;
            border-radius: 30px;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .preco-destaque {
            font-size: 1.6em;
            font-weight: bold;
            color: #2E8B57;
            margin: 15px 0;
            text-align: center;
        }
        
        .detalhes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        
        .detalhe-item {
            text-align: center;
            padding: 8px;
            background: white;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .detalhe-valor {
            font-weight: bold;
            color: #667eea;
        }
        
        .detalhe-label {
            color: #666;
            font-size: 0.8em;
        }
        
        .portal-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }
        
        .loading {
            text-align: center;
            color: white;
            font-size: 1.3em;
            margin: 50px 0;
        }
        
        .refresh-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 1.1em;
            margin: 20px auto;
            display: block;
            transition: transform 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        
        .charts-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }
        
        .chart-container {
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2.2em;
            }
            
            .cidades-grid {
                grid-template-columns: 1fr;
            }
            
            .oportunidades-grid {
                grid-template-columns: 1fr;
            }
            
            .charts-section {
                grid-template-columns: 1fr;
            }
            
            .resumo-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Plataforma Completa de Oportunidades</h1>
            <p>Monitoramento Nacional de Mercados Imobiliários Emergentes</p>
            <p>Senador Canedo + Lucas do Rio Verde + Rio Verde + Sinop + Barreiras + Palmas</p>
            <p id="ultima-atualizacao"></p>
        </div>
        
        <button class="refresh-btn" onclick="carregarDados()">🔄 Atualizar Plataforma</button>
        
        <div id="loading" class="loading">
            Carregando plataforma completa...
        </div>
        
        <div id="resumo-geral" class="resumo-geral" style="display: none;">
            <h2>📊 Resumo Geral da Plataforma</h2>
            <div class="resumo-grid" id="resumo-grid">
            </div>
        </div>
        
        <div id="cidades-stats" class="cidades-grid" style="display: none;">
        </div>
        
        <div class="charts-section" style="display: none;" id="charts-section">
            <div class="chart-container">
                <div class="chart-title">📊 Oportunidades por Cidade</div>
                <canvas id="cidadesChart" width="400" height="300"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">💰 Distribuição de Preços</div>
                <canvas id="precosChart" width="400" height="300"></canvas>
            </div>
        </div>
        
        <div id="oportunidades-section" class="oportunidades-section" style="display: none;">
            <h2>🏆 Todas as Oportunidades Encontradas</h2>
            <div id="oportunidades-grid" class="oportunidades-grid">
            </div>
        </div>
    </div>

    <script>
        let chartInstances = [];
        
        async function carregarDados() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('resumo-geral').style.display = 'none';
            document.getElementById('cidades-stats').style.display = 'none';
            document.getElementById('charts-section').style.display = 'none';
            document.getElementById('oportunidades-section').style.display = 'none';
            
            try {
                const [oportunidades, estatisticas] = await Promise.all([
                    fetch('/api/oportunidades').then(r => r.json()),
                    fetch('/api/estatisticas').then(r => r.json())
                ]);
                
                exibirResumoGeral(estatisticas.resumo_geral);
                exibirEstatisticasCidades(estatisticas.stats_cidade);
                exibirOportunidades(oportunidades);
                criarGraficos(estatisticas.stats_cidade, oportunidades);
                
                document.getElementById('ultima-atualizacao').textContent = 
                    `Última atualização: ${new Date().toLocaleString('pt-BR')}`;
                
            } catch (error) {
                console.error('Erro ao carregar dados:', error);
                document.getElementById('loading').innerHTML = 
                    '❌ Erro ao carregar plataforma. Tente novamente.';
            }
        }
        
        function exibirResumoGeral(resumo) {
            const container = document.getElementById('resumo-grid');
            
            container.innerHTML = `
                <div class="resumo-item">
                    <div class="resumo-numero">${resumo.total_oportunidades}</div>
                    <div class="resumo-label">Oportunidades</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-numero">${resumo.total_cidades}</div>
                    <div class="resumo-label">Cidades</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-numero">${resumo.total_portais}</div>
                    <div class="resumo-label">Portais</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-numero">${resumo.score_medio_geral.toFixed(1)}</div>
                    <div class="resumo-label">Score Médio</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-numero">R$ ${(resumo.preco_medio_geral/1000).toFixed(0)}k</div>
                    <div class="resumo-label">Preço Médio</div>
                </div>
                <div class="resumo-item">
                    <div class="resumo-numero">R$ ${(resumo.menor_preco/1000).toFixed(0)}k-${(resumo.maior_preco/1000).toFixed(0)}k</div>
                    <div class="resumo-label">Faixa de Preços</div>
                </div>
            `;
            
            document.getElementById('resumo-geral').style.display = 'block';
        }
        
        function exibirEstatisticasCidades(cidades) {
            const container = document.getElementById('cidades-stats');
            
            let html = '';
            
            cidades.forEach(cidade => {
                const potencialClass = getPotencialClass(cidade.potencial_categoria);
                
                html += `
                    <div class="cidade-card">
                        <div class="cidade-header">
                            <div class="cidade-nome">📍 ${cidade.cidade}/${cidade.estado}</div>
                            <div class="potencial-badge ${potencialClass}">
                                ${cidade.potencial_categoria.split(' - ')[0]}
                            </div>
                        </div>
                        
                        <div class="cidade-stats">
                            <div class="stat-item">
                                <div class="stat-numero">${cidade.total_oportunidades}</div>
                                <div class="stat-label">Oportunidades</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-numero">${cidade.score_medio.toFixed(1)}</div>
                                <div class="stat-label">Score Médio</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-numero">R$ ${(cidade.preco_medio/1000).toFixed(0)}k</div>
                                <div class="stat-label">Preço Médio</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-numero">R$ ${cidade.preco_m2_medio.toFixed(0)}</div>
                                <div class="stat-label">Preço/m²</div>
                            </div>
                        </div>
                        
                        <div class="crescimento-info">
                            📈 ${cidade.crescimento_populacional}
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            container.style.display = 'grid';
        }
        
        function exibirOportunidades(oportunidades) {
            const container = document.getElementById('oportunidades-grid');
            
            let html = '';
            
            oportunidades.forEach((op, index) => {
                const contatoInfo = getContatoInfo(op);
                
                html += `
                    <div class="oportunidade-card" onclick="flipCard(this)">
                        <div class="click-hint">👆 Clique para contato</div>
                        <div class="card-inner">
                            <div class="card-front">
                                <div class="oportunidade-header">
                                    <div>
                                        <div class="oportunidade-titulo">🏠 ${op.titulo}</div>
                                        <div class="oportunidade-local">📍 ${op.endereco}</div>
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
                                        <div class="detalhe-valor">${op.area.toFixed(0)} m²</div>
                                        <div class="detalhe-label">Área</div>
                                    </div>
                                    <div class="detalhe-item">
                                        <div class="detalhe-valor">R$ ${op.preco_m2.toFixed(0)}</div>
                                        <div class="detalhe-label">Preço/m²</div>
                                    </div>
                                    ${op.quartos ? `
                                    <div class="detalhe-item">
                                        <div class="detalhe-valor">${op.quartos}</div>
                                        <div class="detalhe-label">Quartos</div>
                                    </div>
                                    ` : ''}
                                    ${op.banheiros ? `
                                    <div class="detalhe-item">
                                        <div class="detalhe-valor">${op.banheiros}</div>
                                        <div class="detalhe-label">Banheiros</div>
                                    </div>
                                    ` : ''}
                                </div>
                                
                                <div class="portal-info">
                                    <span>🌐 ${op.portal}</span>
                                    <span>🎯 ${op.potencial_categoria}</span>
                                </div>
                            </div>
                            
                            <div class="card-back">
                                <div class="contato-header">
                                    <div class="contato-titulo">${op.cidade}/${op.estado}</div>
                                    <div class="contato-preco">R$ ${op.preco.toLocaleString('pt-BR')}</div>
                                </div>
                                
                                <div class="contato-info">
                                    ${contatoInfo}
                                </div>
                                
                                <button class="voltar-btn" onclick="event.stopPropagation(); flipCard(this.closest('.oportunidade-card'))">
                                    ← Voltar aos Detalhes
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            document.getElementById('oportunidades-section').style.display = 'block';
            document.getElementById('loading').style.display = 'none';
        }
        
        function getContatoInfo(oportunidade) {
            const cidade = oportunidade.cidade;
            const portal = oportunidade.portal;
            const referencia = oportunidade.referencia;
            
            if (cidade === 'Lucas do Rio Verde') {
                return `
                    <div class="contato-item">
                        <span class="contato-icon">🌐</span>
                        <div>
                            <strong>Portal:</strong> Keller Imóveis<br>
                            <a href="https://kellerimob.com.br/" target="_blank" class="contato-link">kellerimob.com.br</a>
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">🏷️</span>
                        <div><strong>Referência:</strong> ${referencia}</div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">📞</span>
                        <div><strong>Contato:</strong> Consulte no site</div>
                    </div>
                `;
            }
            
            if (cidade === 'Rio Verde') {
                return `
                    <div class="contato-item">
                        <span class="contato-icon">🌐</span>
                        <div>
                            <strong>Portal:</strong> Realize Imóveis RV<br>
                            <a href="https://www.realizeimoveisrv.com.br/" target="_blank" class="contato-link">realizeimoveisrv.com.br</a>
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">🏷️</span>
                        <div><strong>Referência:</strong> ${referencia}</div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">📞</span>
                        <div><strong>Contato:</strong> Consulte no site</div>
                    </div>
                `;
            }
            
            if (cidade === 'Senador Canedo') {
                return `
                    <div class="contato-item">
                        <span class="contato-icon">👩‍💼</span>
                        <div>
                            <strong>Corretor:</strong> Luciana Gurgel<br>
                            <strong>CRECI:</strong> 34.468
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">📱</span>
                        <div>
                            <strong>WhatsApp:</strong><br>
                            <a href="https://wa.me/5562983460400" target="_blank" class="contato-link">(62) 98346-0400</a>
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">🌐</span>
                        <div>
                            <strong>Portal:</strong> 62imoveis.com.br<br>
                            <strong>Ref:</strong> luciana041
                        </div>
                    </div>
                `;
            }
            
            if (cidade === 'Sinop') {
                return `
                    <div class="contato-item">
                        <span class="contato-icon">🌐</span>
                        <div>
                            <strong>Portal:</strong> Keller Imóveis<br>
                            <a href="https://kellerimob.com.br/" target="_blank" class="contato-link">kellerimob.com.br</a>
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">🏷️</span>
                        <div><strong>Referência:</strong> ${referencia}</div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">📞</span>
                        <div><strong>Contato:</strong> Consulte no site</div>
                    </div>
                `;
            }
            
            if (cidade === 'Barreiras') {
                return `
                    <div class="contato-item">
                        <span class="contato-icon">🌐</span>
                        <div>
                            <strong>Portal:</strong> OLX Regional<br>
                            <a href="https://www.olx.com.br/imoveis/estado-ba/regiao-de-vitoria-da-conquista-e-barreiras/barreiras" target="_blank" class="contato-link">OLX Barreiras</a>
                        </div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">🏷️</span>
                        <div><strong>Referência:</strong> ${referencia}</div>
                    </div>
                    <div class="contato-item">
                        <span class="contato-icon">📞</span>
                        <div><strong>Contato:</strong> Consulte no portal</div>
                    </div>
                `;
            }
            
            // Default
            return `
                <div class="contato-item">
                    <span class="contato-icon">🌐</span>
                    <div><strong>Portal:</strong> ${portal}</div>
                </div>
                <div class="contato-item">
                    <span class="contato-icon">🏷️</span>
                    <div><strong>Referência:</strong> ${referencia}</div>
                </div>
            `;
        }
        
        function flipCard(card) {
            card.classList.toggle('flipped');
        }
        
        function criarGraficos(cidades, oportunidades) {
            // Limpa gráficos anteriores
            chartInstances.forEach(chart => chart.destroy());
            chartInstances = [];
            
            // Gráfico de cidades
            const ctxCidades = document.getElementById('cidadesChart').getContext('2d');
            const chartCidades = new Chart(ctxCidades, {
                type: 'doughnut',
                data: {
                    labels: cidades.map(c => c.cidade),
                    datasets: [{
                        data: cidades.map(c => c.total_oportunidades),
                        backgroundColor: [
                            '#FFD700', '#C0C0C0', '#CD7F32', 
                            '#87CEEB', '#98FB98', '#DDA0DD'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            
            // Gráfico de preços
            const ctxPrecos = document.getElementById('precosChart').getContext('2d');
            const chartPrecos = new Chart(ctxPrecos, {
                type: 'bar',
                data: {
                    labels: oportunidades.map(o => `${o.cidade.substring(0,8)}...`),
                    datasets: [{
                        label: 'Preço (R$ mil)',
                        data: oportunidades.map(o => o.preco / 1000),
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            chartInstances.push(chartCidades, chartPrecos);
            document.getElementById('charts-section').style.display = 'grid';
        }
        
        function getPotencialClass(potencial) {
            if (potencial.includes('OURO')) return 'potencial-ouro';
            if (potencial.includes('PRATA')) return 'potencial-prata';
            if (potencial.includes('BRONZE')) return 'potencial-bronze';
            if (potencial.includes('REGIONAL')) return 'potencial-regional';
            if (potencial.includes('ESTÁVEL')) return 'potencial-estavel';
            if (potencial.includes('CONSOLIDADO')) return 'potencial-consolidado';
            return 'potencial-estavel';
        }
        
        // Carrega dados ao inicializar
        document.addEventListener('DOMContentLoaded', carregarDados);
        
        // Auto-refresh a cada 10 minutos
        setInterval(carregarDados, 600000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
