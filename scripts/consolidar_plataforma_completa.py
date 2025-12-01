#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para consolidar todas as oportunidades em uma plataforma unificada
Integra dados de Senador Canedo + Oportunidades Regionais
"""

import sqlite3
import logging
from datetime import datetime

def consolidar_plataforma():
    """Consolida todos os dados em uma plataforma unificada"""
    
    # Conecta aos bancos existentes
    conn_senador = sqlite3.connect('oportunidades_senador_canedo.db')
    conn_regionais = sqlite3.connect('oportunidades_regionais.db')
    
    # Cria banco consolidado
    conn_consolidado = sqlite3.connect('plataforma_oportunidades_completa.db')
    cursor_consolidado = conn_consolidado.cursor()
    
    # Cria tabela unificada
    cursor_consolidado.execute('''
        CREATE TABLE IF NOT EXISTS oportunidades_completas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cidade TEXT NOT NULL,
            estado TEXT NOT NULL,
            titulo TEXT NOT NULL,
            preco REAL,
            area REAL,
            preco_m2 REAL,
            endereco TEXT,
            bairro TEXT,
            quartos INTEGER,
            banheiros INTEGER,
            vagas INTEGER,
            score INTEGER,
            potencial_categoria TEXT,
            portal TEXT,
            referencia TEXT,
            url TEXT,
            data_encontrado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacoes TEXT,
            UNIQUE(referencia, portal, cidade)
        )
    ''')
    
    # Migra dados de Senador Canedo
    cursor_senador = conn_senador.cursor()
    dados_senador = cursor_senador.execute('''
        SELECT titulo, preco, area, preco_m2, endereco, bairro, 
               quartos, banheiros, vagas, score, portal, url, 
               data_encontrado, observacoes
        FROM oportunidades
    ''').fetchall()
    
    for dado in dados_senador:
        cursor_consolidado.execute('''
            INSERT OR REPLACE INTO oportunidades_completas 
            (cidade, estado, titulo, preco, area, preco_m2, endereco, bairro,
             quartos, banheiros, vagas, score, potencial_categoria, portal, 
             referencia, url, data_encontrado, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Senador Canedo', 'GO', dado[0], dado[1], dado[2], dado[3], 
            dado[4], dado[5], dado[6], dado[7], dado[8], dado[9],
            'CONSOLIDADO - REFERÊNCIA', dado[10], 'SC001', dado[11], 
            dado[12], dado[13]
        ))
    
    # Migra dados regionais
    cursor_regionais = conn_regionais.cursor()
    dados_regionais = cursor_regionais.execute('''
        SELECT cidade, estado, titulo, preco, area, preco_m2, endereco, bairro,
               score, potencial_categoria, portal, referencia, url, data_encontrado
        FROM oportunidades_reais
    ''').fetchall()
    
    for dado in dados_regionais:
        cursor_consolidado.execute('''
            INSERT OR REPLACE INTO oportunidades_completas 
            (cidade, estado, titulo, preco, area, preco_m2, endereco, bairro,
             quartos, banheiros, vagas, score, potencial_categoria, portal, 
             referencia, url, data_encontrado, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dado[0], dado[1], dado[2], dado[3], dado[4], dado[5], 
            dado[6], dado[7], None, None, None, dado[8], dado[9], 
            dado[10], dado[11], dado[12], dado[13], 'Migrado de sistema regional'
        ))
    
    # Cria tabela de estatísticas por cidade
    cursor_consolidado.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas_cidades (
            cidade TEXT PRIMARY KEY,
            estado TEXT,
            total_oportunidades INTEGER,
            score_medio REAL,
            preco_medio REAL,
            preco_m2_medio REAL,
            menor_preco REAL,
            maior_preco REAL,
            potencial_categoria TEXT,
            crescimento_populacional TEXT,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Popula estatísticas das cidades
    cidades_stats = [
        ('Lucas do Rio Verde', 'MT', 'OURO - EXCEPCIONAL', '3,83% ao ano - 2º maior do Brasil'),
        ('Rio Verde', 'GO', 'PRATA - EXCEPCIONAL', '2,1% ao ano - Agronegócio forte'),
        ('Sinop', 'MT', 'BRONZE - ALTA', '1,8% ao ano - Portal Norte MT'),
        ('Barreiras', 'BA', 'REGIONAL - MÉDIA', '1,5% ao ano - Hub do Oeste Baiano'),
        ('Palmas', 'TO', 'ESTÁVEL - CONSOLIDADA', '1,2% ao ano - Capital planejada'),
        ('Senador Canedo', 'GO', 'CONSOLIDADO - REFERÊNCIA', '0,8% ao ano - Mercado aquecido')
    ]
    
    for cidade, estado, potencial, crescimento in cidades_stats:
        # Calcula estatísticas reais
        stats = cursor_consolidado.execute('''
            SELECT COUNT(*), AVG(score), AVG(preco), AVG(preco_m2), 
                   MIN(preco), MAX(preco)
            FROM oportunidades_completas 
            WHERE cidade = ?
        ''', (cidade,)).fetchone()
        
        if stats[0] > 0:  # Se tem dados
            cursor_consolidado.execute('''
                INSERT OR REPLACE INTO estatisticas_cidades 
                (cidade, estado, total_oportunidades, score_medio, preco_medio, 
                 preco_m2_medio, menor_preco, maior_preco, potencial_categoria, 
                 crescimento_populacional)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cidade, estado, stats[0], stats[1], stats[2], stats[3], 
                  stats[4], stats[5], potencial, crescimento))
    
    # Cria tabela de histórico consolidado
    cursor_consolidado.execute('''
        CREATE TABLE IF NOT EXISTS historico_consolidado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_consolidacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_oportunidades INTEGER,
            cidades_monitoradas INTEGER,
            portais_ativos INTEGER,
            observacoes TEXT
        )
    ''')
    
    # Registra consolidação atual
    total_ops = cursor_consolidado.execute('SELECT COUNT(*) FROM oportunidades_completas').fetchone()[0]
    total_cidades = cursor_consolidado.execute('SELECT COUNT(DISTINCT cidade) FROM oportunidades_completas').fetchone()[0]
    total_portais = cursor_consolidado.execute('SELECT COUNT(DISTINCT portal) FROM oportunidades_completas').fetchone()[0]
    
    cursor_consolidado.execute('''
        INSERT INTO historico_consolidado 
        (total_oportunidades, cidades_monitoradas, portais_ativos, observacoes)
        VALUES (?, ?, ?, ?)
    ''', (total_ops, total_cidades, total_portais, 'Consolidação completa - Senador Canedo + Regionais'))
    
    # Salva alterações
    conn_consolidado.commit()
    
    # Fecha conexões
    conn_senador.close()
    conn_regionais.close()
    conn_consolidado.close()
    
    print(f"✅ Plataforma consolidada criada!")
    print(f"📊 Total de oportunidades: {total_ops}")
    print(f"🏙️ Cidades monitoradas: {total_cidades}")
    print(f"🌐 Portais ativos: {total_portais}")
    print(f"💾 Banco: plataforma_oportunidades_completa.db")

if __name__ == "__main__":
    consolidar_plataforma()
