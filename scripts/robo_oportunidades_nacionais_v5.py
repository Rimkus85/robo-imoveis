#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô de Monitoramento de Oportunidades Imobiliárias Nacionais V5
Expandido para incluir cidades emergentes de alto potencial
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import time
import random
from datetime import datetime
import re
import os

class RoboOportunidadesNacionais:
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        
        # Configurações expandidas para oportunidades nacionais
        self.cidades_alvo = {
            # Oportunidades Consolidadas (Senador Canedo já valorizado)
            'senador-canedo': {
                'estado': 'GO',
                'nome': 'Senador Canedo',
                'score_minimo': 50,
                'valor_max_m2': 2400,
                'regioes_prioritarias': [
                    'Jardins Europa', 'Setor Leste', 'Centro', 'Setor Sul',
                    'Vila Galvão', 'Parque das Flores', 'Residencial Eldorado',
                    'Jardins Capri', 'Recanto dos Sonhos'
                ]
            },
            
            # 🥇 OPORTUNIDADE MÁXIMA - Lucas do Rio Verde
            'lucas-do-rio-verde': {
                'estado': 'MT',
                'nome': 'Lucas do Rio Verde',
                'score_minimo': 40,  # Critério mais flexível para capturar oportunidades
                'valor_max_m2': 800,  # Preços ainda baixos
                'regioes_prioritarias': [
                    'Centro', 'Setor Industrial', 'Jardim das Américas',
                    'Cidade Nova', 'Parque das Emas', 'Tessele Júnior',
                    'Bandeirantes', 'Novo Horizonte'
                ]
            },
            
            # 🥈 ALTA OPORTUNIDADE - Rio Verde
            'rio-verde': {
                'estado': 'GO',
                'nome': 'Rio Verde',
                'score_minimo': 45,
                'valor_max_m2': 1200,
                'regioes_prioritarias': [
                    'Centro', 'Setor Universitário', 'Jardim América',
                    'Setor Aeroporto', 'Residencial Oliveira', 'Vila Rocha',
                    'Setor Industrial', 'Parque Eldorado'
                ]
            },
            
            # 🥉 BOA OPORTUNIDADE - Sinop
            'sinop': {
                'estado': 'MT',
                'nome': 'Sinop',
                'score_minimo': 45,
                'valor_max_m2': 1500,
                'regioes_prioritarias': [
                    'Centro', 'Setor Comercial', 'Jardim Botânico',
                    'Residencial Florença', 'Setor Industrial',
                    'Jardim das Violetas', 'Setor Norte'
                ]
            },
            
            # OPORTUNIDADE REGIONAL - Barreiras
            'barreiras': {
                'estado': 'BA',
                'nome': 'Barreiras',
                'score_minimo': 40,
                'valor_max_m2': 1000,
                'regioes_prioritarias': [
                    'Centro', 'Setor Universitário', 'Vila Presidente Vargas',
                    'Morada Nobre', 'Jardim Guanabara', 'Setor Norte',
                    'Renato Gonçalves'
                ]
            },
            
            # OPORTUNIDADE ESTÁVEL - Palmas
            'palmas': {
                'estado': 'TO',
                'nome': 'Palmas',
                'score_minimo': 50,
                'valor_max_m2': 2000,
                'regioes_prioritarias': [
                    'Plano Diretor Norte', 'Plano Diretor Sul', 'Centro',
                    'Setor Universitário', 'Jardins Aureny', 'Taquaralto',
                    'Setor Morada do Sol'
                ]
            }
        }
        
        # Portais expandidos para cobertura nacional
        self.portais = {
            '62imoveis.com.br': {
                'base_url': 'https://www.62imoveis.com.br/venda/{estado}/{cidade}/{cidade}/imoveis',
                'cobertura': ['GO', 'MT', 'BA', 'TO'],
                'seletores': {
                    'cards': 'div[class*="card"], article[class*="listing"]',
                    'titulo': 'h2, h3, a[class*="title"]',
                    'preco': 'span[class*="price"], div[class*="valor"]',
                    'area': 'span[class*="area"], div[class*="m2"]',
                    'endereco': 'span[class*="address"], div[class*="endereco"]'
                }
            },
            
            'vivareal.com.br': {
                'base_url': 'https://www.vivareal.com.br/venda/{estado}/{cidade}/',
                'cobertura': ['GO', 'MT', 'BA', 'TO'],
                'seletores': {
                    'cards': 'article[class*="property"], div[class*="result"]',
                    'titulo': 'h2[class*="property"], span[class*="title"]',
                    'preco': 'div[class*="price"], span[class*="value"]',
                    'area': 'span[class*="area"], li[class*="feature"]',
                    'endereco': 'span[class*="neighborhood"], div[class*="address"]'
                }
            },
            
            'imovelweb.com.br': {
                'base_url': 'https://www.imovelweb.com.br/imoveis-venda-{cidade}-{estado}.html',
                'cobertura': ['MT', 'GO', 'BA', 'TO'],
                'seletores': {
                    'cards': 'div[class*="posting"], article[class*="property"]',
                    'titulo': 'h2[class*="title"], h3[class*="name"]',
                    'preco': 'span[class*="price"], div[class*="amount"]',
                    'area': 'span[class*="surface"], div[class*="area"]',
                    'endereco': 'div[class*="location"], span[class*="address"]'
                }
            }
        }
        
        # Headers mais sofisticados para evitar bloqueios
        self.headers_pool = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        ]

    def setup_logging(self):
        """Configura sistema de logs"""
        logging.basicConfig(
            filename='robo_oportunidades_nacionais.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Configura banco de dados expandido"""
        self.conn = sqlite3.connect('oportunidades_nacionais.db')
        cursor = self.conn.cursor()
        
        # Tabela de oportunidades expandida
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oportunidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidade TEXT NOT NULL,
                estado TEXT NOT NULL,
                titulo TEXT NOT NULL,
                preco REAL,
                area REAL,
                preco_m2 REAL,
                endereco TEXT,
                bairro TEXT,
                score INTEGER,
                portal TEXT,
                url TEXT,
                data_encontrado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                potencial_categoria TEXT,
                UNIQUE(titulo, preco, portal, cidade)
            )
        ''')
        
        # Tabela de histórico de varreduras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_varreduras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidade TEXT NOT NULL,
                estado TEXT NOT NULL,
                portal TEXT NOT NULL,
                total_anuncios INTEGER,
                oportunidades_encontradas INTEGER,
                tempo_execucao REAL,
                data_varredura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        ''')
        
        self.conn.commit()

    def calcular_score_expandido(self, preco_m2, area, bairro, cidade_config):
        """Sistema de pontuação expandido para diferentes mercados"""
        score = 0
        
        # Pontuação base por preço/m² (adaptada por cidade)
        valor_max = cidade_config['valor_max_m2']
        
        if preco_m2 <= valor_max * 0.6:  # Muito abaixo do máximo
            score += 30
        elif preco_m2 <= valor_max * 0.8:  # Abaixo do máximo
            score += 20
        elif preco_m2 <= valor_max:  # Dentro do limite
            score += 10
        
        # Pontuação por região prioritária
        if any(regiao.lower() in bairro.lower() for regiao in cidade_config['regioes_prioritarias']):
            score += 25
        
        # Pontuação por área
        if area >= 300:
            score += 15
        elif area >= 200:
            score += 10
        elif area >= 150:
            score += 5
        
        # Bônus por oportunidade (preço muito atrativo)
        if preco_m2 <= valor_max * 0.5:
            score += 15
        
        # Bônus por potencial da cidade
        potencial_bonus = {
            'Lucas do Rio Verde': 20,  # Máximo potencial
            'Rio Verde': 15,
            'Sinop': 10,
            'Barreiras': 8,
            'Palmas': 5,
            'Senador Canedo': 0  # Já valorizado
        }
        
        cidade_nome = cidade_config['nome']
        score += potencial_bonus.get(cidade_nome, 0)
        
        return min(score, 100)  # Máximo 100 pontos

    def varrer_portal_cidade(self, portal_nome, portal_config, cidade_slug, cidade_config):
        """Varre um portal específico para uma cidade"""
        estado = cidade_config['estado'].lower()
        cidade = cidade_slug
        
        # Verifica se o portal cobre este estado
        if estado.upper() not in portal_config['cobertura']:
            return []
        
        try:
            # Constrói URL
            url = portal_config['base_url'].format(
                estado=estado,
                cidade=cidade
            )
            
            # Headers aleatórios
            headers = random.choice(self.headers_pool)
            
            # Delay aleatório
            time.sleep(random.uniform(2, 5))
            
            self.logger.info(f"Varrendo {portal_nome} - {cidade_config['nome']}/{estado.upper()}")
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Busca cards de imóveis
            cards = soup.find_all('div', class_=re.compile(r'card|listing|result|property'))
            
            oportunidades = []
            
            for card in cards[:50]:  # Limita para evitar sobrecarga
                try:
                    # Extrai informações
                    titulo_elem = card.find(['h2', 'h3', 'a'], class_=re.compile(r'title|name|heading'))
                    titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Imóvel sem título"
                    
                    preco_elem = card.find(['span', 'div'], class_=re.compile(r'price|valor|amount'))
                    preco_text = preco_elem.get_text(strip=True) if preco_elem else "0"
                    
                    area_elem = card.find(['span', 'div'], class_=re.compile(r'area|m2|surface'))
                    area_text = area_elem.get_text(strip=True) if area_elem else "0"
                    
                    endereco_elem = card.find(['span', 'div'], class_=re.compile(r'address|endereco|location'))
                    endereco = endereco_elem.get_text(strip=True) if endereco_elem else "Endereço não informado"
                    
                    # Processa preço
                    preco_numeros = re.findall(r'[\d.,]+', preco_text.replace('.', '').replace(',', '.'))
                    preco = float(preco_numeros[0]) if preco_numeros else 0
                    
                    # Processa área
                    area_numeros = re.findall(r'[\d.,]+', area_text.replace(',', '.'))
                    area = float(area_numeros[0]) if area_numeros else 0
                    
                    # Calcula preço por m²
                    preco_m2 = preco / area if area > 0 else 0
                    
                    # Extrai bairro do endereço
                    bairro = endereco.split(',')[0] if ',' in endereco else endereco
                    
                    # Calcula score
                    score = self.calcular_score_expandido(preco_m2, area, bairro, cidade_config)
                    
                    # Verifica se atende critérios mínimos
                    if (score >= cidade_config['score_minimo'] and 
                        preco > 50000 and 
                        area > 100 and 
                        preco_m2 <= cidade_config['valor_max_m2']):
                        
                        # Determina categoria de potencial
                        potencial = self.determinar_potencial(cidade_config['nome'], score)
                        
                        oportunidade = {
                            'cidade': cidade_config['nome'],
                            'estado': cidade_config['estado'],
                            'titulo': titulo,
                            'preco': preco,
                            'area': area,
                            'preco_m2': preco_m2,
                            'endereco': endereco,
                            'bairro': bairro,
                            'score': score,
                            'portal': portal_nome,
                            'url': url,
                            'potencial_categoria': potencial
                        }
                        
                        oportunidades.append(oportunidade)
                        
                except Exception as e:
                    self.logger.warning(f"Erro ao processar card: {e}")
                    continue
            
            return oportunidades
            
        except Exception as e:
            self.logger.error(f"Erro ao varrer {portal_nome} - {cidade}: {e}")
            return []

    def determinar_potencial(self, cidade, score):
        """Determina categoria de potencial baseada na cidade e score"""
        potencial_cidades = {
            'Lucas do Rio Verde': 'OURO',
            'Rio Verde': 'PRATA', 
            'Sinop': 'BRONZE',
            'Barreiras': 'REGIONAL',
            'Palmas': 'ESTÁVEL',
            'Senador Canedo': 'CONSOLIDADO'
        }
        
        base = potencial_cidades.get(cidade, 'PADRÃO')
        
        if score >= 80:
            return f"{base} - EXCEPCIONAL"
        elif score >= 70:
            return f"{base} - ALTA"
        elif score >= 60:
            return f"{base} - MÉDIA"
        else:
            return f"{base} - BÁSICA"

    def salvar_oportunidades(self, oportunidades):
        """Salva oportunidades no banco de dados"""
        cursor = self.conn.cursor()
        
        for oportunidade in oportunidades:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO oportunidades 
                    (cidade, estado, titulo, preco, area, preco_m2, endereco, bairro, 
                     score, portal, url, potencial_categoria)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    oportunidade['cidade'],
                    oportunidade['estado'],
                    oportunidade['titulo'],
                    oportunidade['preco'],
                    oportunidade['area'],
                    oportunidade['preco_m2'],
                    oportunidade['endereco'],
                    oportunidade['bairro'],
                    oportunidade['score'],
                    oportunidade['portal'],
                    oportunidade['url'],
                    oportunidade['potencial_categoria']
                ))
            except Exception as e:
                self.logger.error(f"Erro ao salvar oportunidade: {e}")
        
        self.conn.commit()

    def executar_varredura_completa(self):
        """Executa varredura completa em todas as cidades e portais"""
        inicio = time.time()
        total_oportunidades = 0
        
        self.logger.info("=== INICIANDO VARREDURA NACIONAL DE OPORTUNIDADES ===")
        
        for cidade_slug, cidade_config in self.cidades_alvo.items():
            self.logger.info(f"Varrendo {cidade_config['nome']}/{cidade_config['estado']}")
            
            for portal_nome, portal_config in self.portais.items():
                inicio_portal = time.time()
                
                try:
                    oportunidades = self.varrer_portal_cidade(
                        portal_nome, portal_config, cidade_slug, cidade_config
                    )
                    
                    if oportunidades:
                        self.salvar_oportunidades(oportunidades)
                        total_oportunidades += len(oportunidades)
                        
                        self.logger.info(
                            f"{portal_nome} - {cidade_config['nome']}: "
                            f"{len(oportunidades)} oportunidades encontradas"
                        )
                    
                    # Registra histórico
                    tempo_portal = time.time() - inicio_portal
                    self.registrar_historico(
                        cidade_config['nome'], cidade_config['estado'],
                        portal_nome, 0, len(oportunidades), tempo_portal, "Sucesso"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Erro no portal {portal_nome}: {e}")
                    self.registrar_historico(
                        cidade_config['nome'], cidade_config['estado'],
                        portal_nome, 0, 0, 0, f"Erro: {e}"
                    )
        
        tempo_total = time.time() - inicio
        
        self.logger.info(f"=== VARREDURA CONCLUÍDA ===")
        self.logger.info(f"Total de oportunidades encontradas: {total_oportunidades}")
        self.logger.info(f"Tempo total: {tempo_total:.2f}s")
        
        # Gera relatório
        self.gerar_relatorio_oportunidades()
        
        return total_oportunidades

    def registrar_historico(self, cidade, estado, portal, total_anuncios, oportunidades, tempo, status):
        """Registra histórico da varredura"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO historico_varreduras 
            (cidade, estado, portal, total_anuncios, oportunidades_encontradas, tempo_execucao, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cidade, estado, portal, total_anuncios, oportunidades, tempo, status))
        self.conn.commit()

    def gerar_relatorio_oportunidades(self):
        """Gera relatório das melhores oportunidades por categoria"""
        cursor = self.conn.cursor()
        
        # Melhores oportunidades por potencial
        cursor.execute('''
            SELECT cidade, estado, titulo, preco, area, preco_m2, score, potencial_categoria, portal
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
            LIMIT 20
        ''')
        
        oportunidades = cursor.fetchall()
        
        # Gera relatório em arquivo
        with open('relatorio_oportunidades_nacionais.txt', 'w', encoding='utf-8') as f:
            f.write("🚀 RELATÓRIO DE OPORTUNIDADES IMOBILIÁRIAS NACIONAIS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de oportunidades: {len(oportunidades)}\n\n")
            
            for i, oportunidade in enumerate(oportunidades, 1):
                cidade, estado, titulo, preco, area, preco_m2, score, potencial, portal = oportunidade
                
                f.write(f"🏆 OPORTUNIDADE #{i}\n")
                f.write(f"📍 {cidade}/{estado}\n")
                f.write(f"🏠 {titulo}\n")
                f.write(f"💰 R$ {preco:,.2f}\n")
                f.write(f"📐 {area:.0f} m²\n")
                f.write(f"💲 R$ {preco_m2:,.2f}/m²\n")
                f.write(f"⭐ Score: {score}/100\n")
                f.write(f"🎯 Potencial: {potencial}\n")
                f.write(f"🌐 Portal: {portal}\n")
                f.write("-" * 40 + "\n\n")
        
        self.logger.info("Relatório gerado: relatorio_oportunidades_nacionais.txt")

def main():
    """Função principal"""
    try:
        robo = RoboOportunidadesNacionais()
        total_oportunidades = robo.executar_varredura_completa()
        
        print(f"✅ Varredura concluída!")
        print(f"📊 {total_oportunidades} oportunidades encontradas")
        print(f"📄 Relatório: relatorio_oportunidades_nacionais.txt")
        print(f"📋 Logs: robo_oportunidades_nacionais.log")
        
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        logging.error(f"Erro na execução principal: {e}")

if __name__ == "__main__":
    main()
