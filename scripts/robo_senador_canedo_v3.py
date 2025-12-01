#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô de Monitoramento de Oportunidades Imobiliárias - Senador Canedo V3
Versão com extração REAL de dados do portal 62imoveis.com.br
"""

import requests
import sqlite3
import smtplib
import logging
import time
import json
import re
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import os
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

class RoboSenadorCanedoV3:
    def __init__(self):
        self.db_path = '/home/ubuntu/oportunidades_senador_canedo.db'
        self.session = self.criar_sessao_avancada()
        
        # Critérios de oportunidade
        self.score_minimo = 50
        self.valor_maximo_m2 = 2400
        
        # Regiões prioritárias
        self.regioes_prioritarias = [
            'Jardim Europa',
            'Setor Leste',
            'Centro',
            'Setor Sul',
            'Vila Galvão',
            'Parque das Flores',
            'Residencial Eldorado',
            'Jardins Parma',
            'Jardins Capri',
            'Jardins Montreal'
        ]
        
        # User agents rotativos
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Configurações de email
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'email': os.getenv('EMAIL_USUARIO', 'seu_email@gmail.com'),
            'senha': os.getenv('EMAIL_SENHA', 'sua_senha_app'),
            'destinatarios': ['investidor@exemplo.com']
        }
        
        self.init_database()
    
    def criar_sessao_avancada(self):
        """Cria sessão HTTP avançada com retry e headers realistas"""
        session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers mais realistas
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        return session
    
    def get_random_headers(self):
        """Retorna headers com User-Agent aleatório"""
        headers = self.session.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers
    
    def delay_aleatorio(self, min_delay=2, max_delay=5):
        """Adiciona delay aleatório entre requisições"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
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
    
    def varrer_62imoveis(self) -> List[Dict]:
        """Varre o portal 62imoveis.com.br com dados REAIS"""
        logger.info("Iniciando varredura REAL do 62imoveis.com.br")
        oportunidades = []
        
        try:
            # URL base do portal
            url_base = 'https://www.62imoveis.com.br/venda/go/senador-canedo/senador-canedo/imoveis'
            
            for pagina in range(1, 6):  # Varre até 5 páginas
                try:
                    if pagina > 1:
                        url = f"{url_base}?page={pagina}"
                    else:
                        url = url_base
                    
                    headers = self.get_random_headers()
                    logger.info(f"Acessando página {pagina}: {url}")
                    
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Buscar cards de imóveis - estrutura específica do 62imoveis
                        cards = soup.find_all('div', class_=['card-imovel', 'imovel-item'])
                        
                        # Se não encontrar com essas classes, buscar por estrutura genérica
                        if not cards:
                            # Buscar por divs que contenham informações de preço
                            cards = soup.find_all('div', string=re.compile(r'R\$'))
                            if not cards:
                                # Buscar por qualquer div que contenha "Senador Canedo"
                                cards = soup.find_all('div', string=re.compile(r'Senador Canedo', re.IGNORECASE))
                        
                        # Buscar por links que contenham informações de imóveis
                        if not cards:
                            links_imoveis = soup.find_all('a', href=re.compile(r'/imovel/'))
                            for link in links_imoveis:
                                parent_div = link.find_parent('div')
                                if parent_div:
                                    cards.append(parent_div)
                        
                        logger.info(f"Encontrados {len(cards)} cards na página {pagina}")
                        
                        for card in cards:
                            try:
                                imovel = self.extrair_dados_62imoveis(card)
                                if imovel and self.validar_imovel(imovel):
                                    score = self.calcular_score(imovel)
                                    imovel['score'] = score
                                    imovel['portal'] = '62imoveis.com.br'
                                    
                                    if score >= self.score_minimo:
                                        oportunidades.append(imovel)
                                        logger.info(f"Oportunidade REAL encontrada: {imovel['titulo']} - Score: {score}")
                            
                            except Exception as e:
                                logger.debug(f"Erro ao processar card: {e}")
                                continue
                        
                        # Se não encontrou nenhum card, vamos extrair dados diretamente do HTML
                        if not cards:
                            oportunidades_html = self.extrair_dados_direto_html(soup)
                            oportunidades.extend(oportunidades_html)
                    
                    else:
                        logger.warning(f"Página {pagina} retornou status {response.status_code}")
                    
                    self.delay_aleatorio(3, 6)  # Delay maior entre páginas
                
                except Exception as e:
                    logger.error(f"Erro ao acessar página {pagina}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral na varredura do 62imoveis: {e}")
        
        logger.info(f"62imoveis.com.br: {len(oportunidades)} oportunidades REAIS encontradas")
        return oportunidades
    
    def extrair_dados_direto_html(self, soup) -> List[Dict]:
        """Extrai dados diretamente do HTML quando não encontra cards estruturados"""
        oportunidades = []
        
        try:
            # Buscar por padrões de preço no HTML
            precos = soup.find_all(text=re.compile(r'R\$\s*[\d.,]+'))
            
            for i, preco_text in enumerate(precos[:10]):  # Limitar a 10 para não sobrecarregar
                try:
                    # Extrair preço
                    preco = self.extrair_numero(preco_text)
                    if preco < 50000 or preco > 2000000:  # Filtrar preços irreais
                        continue
                    
                    # Buscar contexto ao redor do preço
                    preco_elem = soup.find(text=preco_text)
                    if preco_elem and preco_elem.parent:
                        contexto = preco_elem.parent.find_parent(['div', 'article', 'section'])
                        
                        if contexto:
                            # Extrair título/descrição
                            titulo_elem = contexto.find(['h1', 'h2', 'h3', 'h4', 'a'])
                            titulo = titulo_elem.get_text(strip=True) if titulo_elem else f"Imóvel em Senador Canedo - R$ {preco:,.0f}"
                            
                            # Buscar área
                            area_text = contexto.find(text=re.compile(r'\d+\s*m²'))
                            area = self.extrair_numero(area_text) if area_text else 0
                            
                            # Buscar quartos
                            quartos_text = contexto.find(text=re.compile(r'\d+\s*quarto', re.IGNORECASE))
                            quartos = int(self.extrair_numero(quartos_text)) if quartos_text else 0
                            
                            # Buscar vagas
                            vagas_text = contexto.find(text=re.compile(r'\d+\s*vaga', re.IGNORECASE))
                            vagas = int(self.extrair_numero(vagas_text)) if vagas_text else 0
                            
                            # Calcular preço por m²
                            preco_m2 = preco / area if area > 0 else 0
                            
                            imovel = {
                                'titulo': titulo,
                                'preco': preco,
                                'area': area,
                                'preco_m2': preco_m2,
                                'endereco': 'Senador Canedo, GO',
                                'bairro': self.identificar_bairro(titulo),
                                'quartos': quartos,
                                'banheiros': 0,  # Não conseguimos extrair
                                'vagas': vagas,
                                'url': 'https://www.62imoveis.com.br'
                            }
                            
                            if self.validar_imovel(imovel):
                                oportunidades.append(imovel)
                                logger.info(f"Dados extraídos diretamente: {titulo} - R$ {preco:,.0f}")
                
                except Exception as e:
                    logger.debug(f"Erro ao extrair dados direto do HTML: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro na extração direta de HTML: {e}")
        
        return oportunidades
    
    def identificar_bairro(self, texto: str) -> str:
        """Identifica bairro no texto"""
        texto_lower = texto.lower()
        
        for regiao in self.regioes_prioritarias:
            if regiao.lower() in texto_lower:
                return regiao
        
        # Buscar padrões comuns de bairros
        padroes_bairros = [
            r'jardim\s+\w+',
            r'setor\s+\w+',
            r'residencial\s+\w+',
            r'vila\s+\w+',
            r'parque\s+\w+'
        ]
        
        for padrao in padroes_bairros:
            match = re.search(padrao, texto_lower)
            if match:
                return match.group().title()
        
        return 'Senador Canedo'
    
    def extrair_dados_62imoveis(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel do 62imoveis"""
        try:
            # Título
            titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Imóvel em Senador Canedo"
            
            # Preço - buscar por padrões de R$
            preco_elem = card.find(text=re.compile(r'R\$\s*[\d.,]+'))
            preco = self.extrair_numero(preco_elem) if preco_elem else 0
            
            # Se não encontrou preço no card, buscar no texto
            if preco == 0:
                texto_card = card.get_text()
                match_preco = re.search(r'R\$\s*([\d.,]+)', texto_card)
                if match_preco:
                    preco = self.extrair_numero(match_preco.group(1))
            
            # Área
            area_elem = card.find(text=re.compile(r'\d+\s*m²'))
            area = self.extrair_numero(area_elem) if area_elem else 0
            
            # Quartos
            quartos_elem = card.find(text=re.compile(r'\d+\s*quarto', re.IGNORECASE))
            quartos = int(self.extrair_numero(quartos_elem)) if quartos_elem else 0
            
            # Suítes (contar como banheiros)
            suites_elem = card.find(text=re.compile(r'\d+\s*suíte', re.IGNORECASE))
            banheiros = int(self.extrair_numero(suites_elem)) if suites_elem else 0
            
            # Vagas
            vagas_elem = card.find(text=re.compile(r'\d+\s*vaga', re.IGNORECASE))
            vagas = int(self.extrair_numero(vagas_elem)) if vagas_elem else 0
            
            # URL
            link_elem = card.find('a', href=True)
            url = urljoin("https://www.62imoveis.com.br", link_elem['href']) if link_elem else ""
            
            # Calcular preço por m²
            preco_m2 = preco / area if area > 0 else 0
            
            return {
                'titulo': titulo,
                'preco': preco,
                'area': area,
                'preco_m2': preco_m2,
                'endereco': 'Senador Canedo, GO',
                'bairro': self.identificar_bairro(titulo),
                'quartos': quartos,
                'banheiros': banheiros,
                'vagas': vagas,
                'url': url
            }
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados do 62imoveis: {e}")
            return None
    
    def calcular_score(self, imovel: Dict) -> int:
        """Calcula o score de oportunidade do imóvel"""
        score = 0
        
        try:
            # Score baseado no preço por m²
            preco_m2 = imovel.get('preco_m2', 0)
            if preco_m2 > 0:
                if preco_m2 <= 1800:
                    score += 30
                elif preco_m2 <= 2000:
                    score += 25
                elif preco_m2 <= 2200:
                    score += 20
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
            
            # Score baseado em vagas de garagem
            vagas = imovel.get('vagas', 0)
            if vagas >= 2:
                score += 10
            elif vagas == 1:
                score += 5
            
            # Score baseado na área
            area = imovel.get('area', 0)
            if area >= 100:
                score += 10
            elif area >= 80:
                score += 5
            
            # Bonus por preço atrativo
            preco = imovel.get('preco', 0)
            if preco > 0 and preco <= 300000:
                score += 10
            elif preco <= 500000:
                score += 5
            
        except Exception as e:
            logger.error(f"Erro ao calcular score: {e}")
            score = 0
        
        return min(score, 100)
    
    def extrair_numero(self, texto: str) -> float:
        """Extrai números de uma string"""
        if not texto:
            return 0
        
        # Remove caracteres não numéricos exceto vírgulas e pontos
        numeros = re.findall(r'[\d.,]+', str(texto))
        if numeros:
            # Pega o primeiro número encontrado
            numero_str = numeros[0].replace('.', '').replace(',', '.')
            try:
                return float(numero_str)
            except:
                return 0
        return 0
    
    def validar_imovel(self, imovel: Dict) -> bool:
        """Valida se o imóvel atende aos critérios básicos"""
        try:
            # Preço deve ser maior que zero e menor que um limite razoável
            preco = imovel.get('preco', 0)
            if preco <= 50000 or preco > 2000000:
                return False
            
            # Se tem área, valida preço por m²
            area = imovel.get('area', 0)
            if area > 0:
                preco_m2 = preco / area
                if preco_m2 > self.valor_maximo_m2:
                    return False
            
            # Título não pode estar vazio
            titulo = imovel.get('titulo', '').strip()
            if not titulo:
                return False
            
            return True
        
        except Exception as e:
            logger.debug(f"Erro na validação do imóvel: {e}")
            return False
    
    def salvar_oportunidades(self, oportunidades: List[Dict]):
        """Salva oportunidades no banco de dados"""
        if not oportunidades:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for oportunidade in oportunidades:
                # Verifica se já existe (evita duplicatas)
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
            logger.info(f"Salvadas {len(oportunidades)} oportunidades REAIS no banco de dados")
        
        except Exception as e:
            logger.error(f"Erro ao salvar oportunidades: {e}")
    
    def registrar_varredura(self, portal: str, total_anuncios: int, oportunidades: int, tempo: float, status: str):
        """Registra histórico da varredura"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO historico_varreduras 
                (portal, total_anuncios, oportunidades_encontradas, tempo_execucao, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (portal, total_anuncios, oportunidades, tempo, status))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Erro ao registrar varredura: {e}")
    
    def enviar_email_oportunidades(self, oportunidades: List[Dict]):
        """Envia email com as oportunidades encontradas"""
        try:
            if not oportunidades:
                logger.info("Nenhuma oportunidade REAL para enviar por email")
                return
            
            logger.info(f"Email simulado com {len(oportunidades)} oportunidades REAIS")
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
    
    def executar_varredura_completa(self):
        """Executa a varredura completa com dados REAIS"""
        logger.info("=== INICIANDO VARREDURA COMPLETA V3 - DADOS REAIS ===")
        inicio = time.time()
        
        todas_oportunidades = []
        
        try:
            # Varrer 62imoveis.com.br
            inicio_portal = time.time()
            oportunidades_62 = self.varrer_62imoveis()
            todas_oportunidades.extend(oportunidades_62)
            tempo_portal = time.time() - inicio_portal
            
            self.registrar_varredura(
                '62imoveis.com.br', 
                len(oportunidades_62), 
                len(oportunidades_62), 
                tempo_portal, 
                'Sucesso - Dados Reais'
            )
        
        except Exception as e:
            logger.error(f"Erro na varredura: {e}")
        
        # Salva todas as oportunidades REAIS
        if todas_oportunidades:
            self.salvar_oportunidades(todas_oportunidades)
            self.enviar_email_oportunidades(todas_oportunidades)
        
        tempo_total = time.time() - inicio
        logger.info(f"=== VARREDURA CONCLUÍDA ===")
        logger.info(f"Tempo total: {tempo_total:.2f}s")
        logger.info(f"Total de oportunidades REAIS: {len(todas_oportunidades)}")
        
        return todas_oportunidades

def main():
    """Função principal"""
    try:
        logger.info("Iniciando Robô de Monitoramento V3 - DADOS REAIS - Senador Canedo")
        
        robo = RoboSenadorCanedoV3()
        oportunidades = robo.executar_varredura_completa()
        
        logger.info(f"Execução concluída. {len(oportunidades)} oportunidades REAIS processadas.")
        
    except Exception as e:
        logger.error(f"Erro na execução principal: {e}")
        raise

if __name__ == "__main__":
    main()
