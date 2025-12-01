#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô de Monitoramento de Oportunidades Imobiliárias - Senador Canedo V4
Versão com extração REAL baseada na estrutura HTML observada do 62imoveis.com.br
"""

import requests
import sqlite3
import logging
import time
import re
import random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from typing import List, Dict, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/robo_senador_canedo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RoboSenadorCanedoV4:
    def __init__(self):
        self.db_path = '/home/ubuntu/oportunidades_senador_canedo.db'
        self.session = requests.Session()
        
        # Headers realistas
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Critérios de oportunidade
        self.score_minimo = 50
        self.valor_maximo_m2 = 2400
        
        # Regiões prioritárias
        self.regioes_prioritarias = [
            'Jardim Europa', 'Setor Leste', 'Centro', 'Setor Sul', 'Vila Galvão',
            'Parque das Flores', 'Residencial Eldorado', 'Jardins Parma',
            'Jardins Capri', 'Jardins Montreal', 'Villa Verde', 'Terras Alpha'
        ]
        
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS oportunidades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal TEXT NOT NULL,
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
                    url TEXT,
                    data_encontrado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    enviado_email BOOLEAN DEFAULT FALSE,
                    observacoes TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historico_varreduras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_varredura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    portal TEXT,
                    total_anuncios INTEGER,
                    oportunidades_encontradas INTEGER,
                    tempo_execucao REAL,
                    status TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Banco de dados inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
    
    def extrair_numero(self, texto: str) -> float:
        """Extrai números de uma string"""
        if not texto:
            return 0
        
        # Remove tudo exceto dígitos, vírgulas e pontos
        numeros = re.findall(r'[\d.,]+', str(texto))
        if numeros:
            numero_str = numeros[0].replace('.', '').replace(',', '.')
            try:
                return float(numero_str)
            except:
                return 0
        return 0
    
    def identificar_bairro(self, texto: str) -> str:
        """Identifica bairro no texto"""
        if not texto:
            return 'Senador Canedo'
            
        texto_lower = texto.lower()
        
        # Buscar regiões prioritárias
        for regiao in self.regioes_prioritarias:
            if regiao.lower() in texto_lower:
                return regiao
        
        # Buscar padrões comuns
        padroes = [
            r'jardim\s+[\w\s]+',
            r'jardins\s+[\w\s]+',
            r'setor\s+[\w\s]+',
            r'residencial\s+[\w\s]+',
            r'condomínio\s+[\w\s]+',
            r'vila\s+[\w\s]+',
            r'parque\s+[\w\s]+'
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto_lower)
            if match:
                bairro = match.group().strip().title()
                if len(bairro) < 50:  # Evitar textos muito longos
                    return bairro
        
        return 'Senador Canedo'
    
    def calcular_score(self, imovel: Dict) -> int:
        """Calcula o score de oportunidade do imóvel"""
        score = 0
        
        try:
            # Score baseado no preço por m²
            preco_m2 = imovel.get('preco_m2', 0)
            if preco_m2 > 0:
                if preco_m2 <= 1000:
                    score += 35
                elif preco_m2 <= 1500:
                    score += 30
                elif preco_m2 <= 2000:
                    score += 25
                elif preco_m2 <= 2400:
                    score += 15
            
            # Score baseado na região
            bairro = imovel.get('bairro', '').lower()
            for regiao in self.regioes_prioritarias:
                if regiao.lower() in bairro:
                    score += 20
                    break
            
            # Score baseado no número de quartos
            quartos = imovel.get('quartos', 0)
            if quartos >= 3:
                score += 15
            elif quartos == 2:
                score += 10
            elif quartos == 1:
                score += 5
            
            # Score baseado em vagas de garagem
            vagas = imovel.get('vagas', 0)
            if vagas >= 2:
                score += 10
            elif vagas == 1:
                score += 5
            
            # Score baseado na área
            area = imovel.get('area', 0)
            if area >= 200:
                score += 15
            elif area >= 100:
                score += 10
            elif area >= 50:
                score += 5
            
            # Bonus por preço atrativo
            preco = imovel.get('preco', 0)
            if 100000 <= preco <= 400000:
                score += 10
            elif preco <= 600000:
                score += 5
            
        except Exception as e:
            logger.error(f"Erro ao calcular score: {e}")
            score = 0
        
        return min(score, 100)
    
    def validar_imovel(self, imovel: Dict) -> bool:
        """Valida se o imóvel atende aos critérios básicos"""
        try:
            preco = imovel.get('preco', 0)
            if preco < 50000 or preco > 3000000:
                return False
            
            titulo = imovel.get('titulo', '').strip()
            if not titulo or len(titulo) < 10:
                return False
            
            # Se tem área, valida preço por m²
            area = imovel.get('area', 0)
            if area > 0:
                preco_m2 = preco / area
                if preco_m2 > self.valor_maximo_m2:
                    return False
            
            return True
        
        except Exception as e:
            logger.debug(f"Erro na validação: {e}")
            return False
    
    def varrer_62imoveis_real(self) -> List[Dict]:
        """Varre o 62imoveis.com.br com base na estrutura HTML real observada"""
        logger.info("Iniciando varredura REAL do 62imoveis.com.br")
        oportunidades = []
        
        try:
            url = 'https://www.62imoveis.com.br/venda/go/senador-canedo/senador-canedo/imoveis'
            
            for pagina in range(1, 4):  # 3 páginas para teste
                try:
                    if pagina > 1:
                        url_pagina = f"{url}?page={pagina}"
                    else:
                        url_pagina = url
                    
                    logger.info(f"Acessando página {pagina}: {url_pagina}")
                    
                    response = self.session.get(url_pagina, timeout=30)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Método 1: Buscar por padrões de preço no HTML
                        html_text = soup.get_text()
                        precos_encontrados = re.findall(r'R\$\s*([\d.,]+)', html_text)
                        
                        logger.info(f"Encontrados {len(precos_encontrados)} preços na página {pagina}")
                        
                        # Método 2: Buscar elementos que contêm "R$" e extrair contexto
                        elementos_preco = soup.find_all(string=re.compile(r'R\$\s*[\d.,]+'))
                        
                        for i, preco_text in enumerate(elementos_preco):
                            try:
                                # Extrair preço
                                preco = self.extrair_numero(preco_text)
                                if preco < 50000 or preco > 3000000:
                                    continue
                                
                                # Buscar elemento pai que contém mais informações
                                elemento_pai = None
                                current = preco_text.parent if hasattr(preco_text, 'parent') else None
                                
                                # Subir na árvore DOM até encontrar um container com mais informações
                                for _ in range(5):  # Máximo 5 níveis
                                    if current and current.name:
                                        texto_container = current.get_text()
                                        if len(texto_container) > 100:  # Container com informações suficientes
                                            elemento_pai = current
                                            break
                                        current = current.parent
                                    else:
                                        break
                                
                                if not elemento_pai:
                                    continue
                                
                                texto_completo = elemento_pai.get_text()
                                
                                # Extrair informações do texto
                                titulo = self.extrair_titulo(texto_completo, preco)
                                area = self.extrair_area(texto_completo)
                                quartos = self.extrair_quartos(texto_completo)
                                vagas = self.extrair_vagas(texto_completo)
                                bairro = self.identificar_bairro(texto_completo)
                                
                                # Calcular preço por m²
                                preco_m2 = preco / area if area > 0 else 0
                                
                                # Buscar URL do imóvel
                                link_elem = elemento_pai.find('a', href=True)
                                url_imovel = urljoin("https://www.62imoveis.com.br", link_elem['href']) if link_elem else ""
                                
                                imovel = {
                                    'titulo': titulo,
                                    'preco': preco,
                                    'area': area,
                                    'preco_m2': preco_m2,
                                    'endereco': f"{bairro}, Senador Canedo, GO",
                                    'bairro': bairro,
                                    'quartos': quartos,
                                    'banheiros': 0,  # Não conseguimos extrair facilmente
                                    'vagas': vagas,
                                    'url': url_imovel,
                                    'portal': '62imoveis.com.br'
                                }
                                
                                if self.validar_imovel(imovel):
                                    score = self.calcular_score(imovel)
                                    imovel['score'] = score
                                    
                                    if score >= self.score_minimo:
                                        oportunidades.append(imovel)
                                        logger.info(f"Oportunidade REAL encontrada: {titulo} - R$ {preco:,.0f} - Score: {score}")
                            
                            except Exception as e:
                                logger.debug(f"Erro ao processar preço {i}: {e}")
                                continue
                    
                    else:
                        logger.warning(f"Página {pagina} retornou status {response.status_code}")
                    
                    time.sleep(random.uniform(2, 4))  # Delay entre páginas
                
                except Exception as e:
                    logger.error(f"Erro ao acessar página {pagina}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral na varredura: {e}")
        
        logger.info(f"Total de oportunidades REAIS encontradas: {len(oportunidades)}")
        return oportunidades
    
    def extrair_titulo(self, texto: str, preco: float) -> str:
        """Extrai ou gera título baseado no contexto"""
        linhas = texto.split('\n')
        
        # Buscar linha que parece ser título (não muito longa, não só números)
        for linha in linhas:
            linha = linha.strip()
            if (10 < len(linha) < 100 and 
                not linha.replace(' ', '').isdigit() and
                'R$' not in linha and
                any(palavra in linha.lower() for palavra in ['casa', 'apartamento', 'terreno', 'lote', 'condomínio'])):
                return linha
        
        # Se não encontrou, gerar título baseado no contexto
        if 'terreno' in texto.lower() or 'lote' in texto.lower():
            return f"Terreno em Senador Canedo - R$ {preco:,.0f}"
        elif 'casa' in texto.lower():
            return f"Casa em Senador Canedo - R$ {preco:,.0f}"
        elif 'apartamento' in texto.lower():
            return f"Apartamento em Senador Canedo - R$ {preco:,.0f}"
        else:
            return f"Imóvel em Senador Canedo - R$ {preco:,.0f}"
    
    def extrair_area(self, texto: str) -> float:
        """Extrai área do texto"""
        # Buscar padrões como "100 m²", "100m²", "100 m2"
        matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*m[²2]', texto, re.IGNORECASE)
        if matches:
            return self.extrair_numero(matches[0])
        return 0
    
    def extrair_quartos(self, texto: str) -> int:
        """Extrai número de quartos"""
        matches = re.findall(r'(\d+)\s*quarto', texto, re.IGNORECASE)
        if matches:
            return int(matches[0])
        
        # Buscar por "2Q", "3Q", etc.
        matches = re.findall(r'(\d+)Q', texto, re.IGNORECASE)
        if matches:
            return int(matches[0])
        
        return 0
    
    def extrair_vagas(self, texto: str) -> int:
        """Extrai número de vagas"""
        matches = re.findall(r'(\d+)\s*vaga', texto, re.IGNORECASE)
        if matches:
            return int(matches[0])
        return 0
    
    def salvar_oportunidades(self, oportunidades: List[Dict]):
        """Salva oportunidades no banco de dados"""
        if not oportunidades:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for oportunidade in oportunidades:
                # Verifica duplicatas
                cursor.execute('''
                    SELECT id FROM oportunidades 
                    WHERE titulo = ? AND preco = ? AND portal = ?
                ''', (oportunidade['titulo'], oportunidade['preco'], oportunidade['portal']))
                
                if cursor.fetchone() is None:
                    cursor.execute('''
                        INSERT INTO oportunidades 
                        (portal, titulo, preco, area, preco_m2, endereco, bairro, 
                         quartos, banheiros, vagas, score, url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        oportunidade['portal'],
                        oportunidade['titulo'],
                        oportunidade['preco'],
                        oportunidade['area'],
                        oportunidade['preco_m2'],
                        oportunidade['endereco'],
                        oportunidade['bairro'],
                        oportunidade['quartos'],
                        oportunidade['banheiros'],
                        oportunidade['vagas'],
                        oportunidade['score'],
                        oportunidade['url']
                    ))
            
            conn.commit()
            conn.close()
            logger.info(f"Salvadas {len(oportunidades)} oportunidades REAIS no banco")
        
        except Exception as e:
            logger.error(f"Erro ao salvar oportunidades: {e}")
    
    def registrar_varredura(self, portal: str, total: int, oportunidades: int, tempo: float, status: str):
        """Registra histórico da varredura"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO historico_varreduras 
                (portal, total_anuncios, oportunidades_encontradas, tempo_execucao, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (portal, total, oportunidades, tempo, status))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erro ao registrar varredura: {e}")
    
    def executar_varredura_completa(self):
        """Executa varredura completa com dados REAIS"""
        logger.info("=== INICIANDO VARREDURA V4 - DADOS REAIS ===")
        inicio = time.time()
        
        try:
            inicio_portal = time.time()
            oportunidades = self.varrer_62imoveis_real()
            tempo_portal = time.time() - inicio_portal
            
            self.registrar_varredura(
                '62imoveis.com.br V4',
                len(oportunidades),
                len(oportunidades),
                tempo_portal,
                'Sucesso - Dados Reais'
            )
            
            if oportunidades:
                self.salvar_oportunidades(oportunidades)
                logger.info(f"Email simulado com {len(oportunidades)} oportunidades REAIS")
            
            tempo_total = time.time() - inicio
            logger.info(f"=== VARREDURA CONCLUÍDA ===")
            logger.info(f"Tempo total: {tempo_total:.2f}s")
            logger.info(f"Oportunidades REAIS encontradas: {len(oportunidades)}")
            
            return oportunidades
        
        except Exception as e:
            logger.error(f"Erro na execução: {e}")
            return []

def main():
    """Função principal"""
    try:
        logger.info("Iniciando Robô V4 - EXTRAÇÃO REAL DE DADOS")
        
        robo = RoboSenadorCanedoV4()
        oportunidades = robo.executar_varredura_completa()
        
        logger.info(f"Execução concluída. {len(oportunidades)} oportunidades REAIS processadas.")
        
        # Mostrar resumo das oportunidades
        if oportunidades:
            logger.info("\n=== RESUMO DAS OPORTUNIDADES REAIS ===")
            for i, op in enumerate(oportunidades[:5], 1):
                logger.info(f"{i}. {op['titulo']} - R$ {op['preco']:,.0f} - Score: {op['score']}")
        
    except Exception as e:
        logger.error(f"Erro na execução principal: {e}")
        raise

if __name__ == "__main__":
    main()
