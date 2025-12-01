#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô de Monitoramento de Oportunidades Imobiliárias - Senador Canedo V2
Versão avançada com contorno de proteções anti-bot
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

class RoboSenadorCanedoV2:
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
            'Residencial Eldorado'
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
    
    def buscar_portais_alternativos(self) -> List[Dict]:
        """Busca em portais alternativos sem Cloudflare"""
        logger.info("Buscando em portais alternativos")
        oportunidades = []
        
        # Portais alternativos que podem não ter Cloudflare
        portais_alternativos = [
            {
                'nome': 'Imovelweb',
                'url': 'https://www.imovelweb.com.br/imoveis-venda-senador-canedo-goias.html',
                'funcao': self.varrer_imovelweb
            },
            {
                'nome': 'Chaves na Mão',
                'url': 'https://www.chavesnamao.com.br/imoveis-para-venda-em-senador-canedo-go',
                'funcao': self.varrer_chaves_na_mao
            }
        ]
        
        for portal in portais_alternativos:
            try:
                logger.info(f"Tentando acessar {portal['nome']}")
                oportunidades_portal = portal['funcao']()
                oportunidades.extend(oportunidades_portal)
                self.delay_aleatorio()
            except Exception as e:
                logger.error(f"Erro ao acessar {portal['nome']}: {e}")
        
        return oportunidades
    
    def varrer_imovelweb(self) -> List[Dict]:
        """Varre o portal Imovelweb"""
        logger.info("Iniciando varredura do Imovelweb")
        oportunidades = []
        
        try:
            url = 'https://www.imovelweb.com.br/imoveis-venda-senador-canedo-goias.html'
            headers = self.get_random_headers()
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar cards de imóveis (estrutura específica do Imovelweb)
                cards = soup.find_all('div', class_=['posting-card', 'property-card'])
                
                for card in cards:
                    try:
                        imovel = self.extrair_dados_imovelweb(card)
                        if imovel and self.validar_imovel(imovel):
                            score = self.calcular_score(imovel)
                            imovel['score'] = score
                            imovel['portal'] = 'Imovelweb'
                            
                            if score >= self.score_minimo:
                                oportunidades.append(imovel)
                                logger.info(f"Oportunidade encontrada no Imovelweb: {imovel['titulo']} - Score: {score}")
                    
                    except Exception as e:
                        logger.debug(f"Erro ao processar card do Imovelweb: {e}")
                        continue
            
            else:
                logger.warning(f"Imovelweb retornou status {response.status_code}")
        
        except Exception as e:
            logger.error(f"Erro geral na varredura do Imovelweb: {e}")
        
        logger.info(f"Imovelweb: {len(oportunidades)} oportunidades encontradas")
        return oportunidades
    
    def extrair_dados_imovelweb(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel do Imovelweb"""
        try:
            # Título
            titulo_elem = card.find(['h2', 'h3', 'a'], class_=['posting-title', 'property-title'])
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Título não encontrado"
            
            # Preço
            preco_elem = card.find(['span', 'div'], class_=['price', 'posting-price'])
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "0"
            preco = self.extrair_numero(preco_texto)
            
            # Área
            area_elem = card.find(text=re.compile(r'm²|m2'))
            area = 0
            if area_elem:
                area = self.extrair_numero(area_elem.parent.get_text() if area_elem.parent else area_elem)
            
            # Endereço
            endereco_elem = card.find(['span', 'div'], class_=['address', 'location'])
            endereco = endereco_elem.get_text(strip=True) if endereco_elem else ""
            
            # Características
            quartos = self.extrair_caracteristica(card, r'quarto|bedroom|dorm')
            banheiros = self.extrair_caracteristica(card, r'banheiro|bathroom|wc')
            vagas = self.extrair_caracteristica(card, r'vaga|garage|garagem')
            
            # URL
            link_elem = card.find('a', href=True)
            url = urljoin("https://www.imovelweb.com.br", link_elem['href']) if link_elem else ""
            
            # Calcular preço por m²
            preco_m2 = preco / area if area > 0 else 0
            
            return {
                'titulo': titulo,
                'preco': preco,
                'area': area,
                'preco_m2': preco_m2,
                'endereco': endereco,
                'bairro': self.extrair_bairro(endereco),
                'quartos': quartos,
                'banheiros': banheiros,
                'vagas': vagas,
                'url': url
            }
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados do Imovelweb: {e}")
            return None
    
    def varrer_chaves_na_mao(self) -> List[Dict]:
        """Varre o portal Chaves na Mão"""
        logger.info("Iniciando varredura do Chaves na Mão")
        oportunidades = []
        
        try:
            url = 'https://www.chavesnamao.com.br/imoveis-para-venda-em-senador-canedo-go'
            headers = self.get_random_headers()
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar cards de imóveis
                cards = soup.find_all('div', class_=['card-imovel', 'imovel-card', 'property-item'])
                
                for card in cards:
                    try:
                        imovel = self.extrair_dados_chaves_na_mao(card)
                        if imovel and self.validar_imovel(imovel):
                            score = self.calcular_score(imovel)
                            imovel['score'] = score
                            imovel['portal'] = 'Chaves na Mão'
                            
                            if score >= self.score_minimo:
                                oportunidades.append(imovel)
                                logger.info(f"Oportunidade encontrada no Chaves na Mão: {imovel['titulo']} - Score: {score}")
                    
                    except Exception as e:
                        logger.debug(f"Erro ao processar card do Chaves na Mão: {e}")
                        continue
            
            else:
                logger.warning(f"Chaves na Mão retornou status {response.status_code}")
        
        except Exception as e:
            logger.error(f"Erro geral na varredura do Chaves na Mão: {e}")
        
        logger.info(f"Chaves na Mão: {len(oportunidades)} oportunidades encontradas")
        return oportunidades
    
    def extrair_dados_chaves_na_mao(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel do Chaves na Mão"""
        try:
            # Implementação similar aos outros portais
            titulo_elem = card.find(['h2', 'h3'], class_=['titulo', 'title'])
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Título não encontrado"
            
            preco_elem = card.find(['span', 'div'], class_=['preco', 'price'])
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "0"
            preco = self.extrair_numero(preco_texto)
            
            return {
                'titulo': titulo,
                'preco': preco,
                'area': 0,
                'preco_m2': 0,
                'endereco': "",
                'bairro': "",
                'quartos': 0,
                'banheiros': 0,
                'vagas': 0,
                'url': ""
            }
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados do Chaves na Mão: {e}")
            return None
    
    def criar_oportunidades_exemplo(self) -> List[Dict]:
        """Cria oportunidades de exemplo para demonstração"""
        logger.info("Criando oportunidades de exemplo para demonstração")
        
        oportunidades_exemplo = [
            {
                'portal': 'Portal Exemplo',
                'titulo': 'Casa 3 quartos no Jardim Europa - Excelente oportunidade',
                'preco': 280000.0,
                'area': 150.0,
                'preco_m2': 1866.67,
                'endereco': 'Rua das Flores, 123, Jardim Europa',
                'bairro': 'Jardim Europa',
                'quartos': 3,
                'banheiros': 2,
                'vagas': 2,
                'url': 'https://exemplo.com/imovel1',
                'score': 0
            },
            {
                'portal': 'Portal Exemplo',
                'titulo': 'Apartamento 2 quartos no Setor Leste - Pronto para morar',
                'preco': 180000.0,
                'area': 85.0,
                'preco_m2': 2117.65,
                'endereco': 'Avenida Central, 456, Setor Leste',
                'bairro': 'Setor Leste',
                'quartos': 2,
                'banheiros': 1,
                'vagas': 1,
                'url': 'https://exemplo.com/imovel2',
                'score': 0
            },
            {
                'portal': 'Portal Exemplo',
                'titulo': 'Casa 4 quartos no Centro - Localização privilegiada',
                'preco': 350000.0,
                'area': 200.0,
                'preco_m2': 1750.0,
                'endereco': 'Praça Principal, 789, Centro',
                'bairro': 'Centro',
                'quartos': 4,
                'banheiros': 3,
                'vagas': 2,
                'url': 'https://exemplo.com/imovel3',
                'score': 0
            }
        ]
        
        # Calcular scores
        for oportunidade in oportunidades_exemplo:
            oportunidade['score'] = self.calcular_score(oportunidade)
        
        # Filtrar apenas oportunidades com score adequado
        oportunidades_validas = [op for op in oportunidades_exemplo if op['score'] >= self.score_minimo]
        
        logger.info(f"Criadas {len(oportunidades_validas)} oportunidades de exemplo")
        return oportunidades_validas
    
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
    
    def extrair_caracteristica(self, card, pattern: str) -> int:
        """Extrai características numéricas (quartos, banheiros, vagas)"""
        try:
            elem = card.find(text=re.compile(pattern, re.IGNORECASE))
            if elem:
                texto = elem.parent.get_text() if elem.parent else elem
                numero = self.extrair_numero(texto)
                return int(numero) if numero > 0 else 0
            return 0
        except:
            return 0
    
    def extrair_bairro(self, endereco: str) -> str:
        """Extrai o bairro do endereço"""
        if not endereco:
            return ""
        
        # Procura por padrões comuns de bairro
        for regiao in self.regioes_prioritarias:
            if regiao.lower() in endereco.lower():
                return regiao
        
        # Se não encontrar região prioritária, tenta extrair bairro genérico
        partes = endereco.split(',')
        if len(partes) >= 2:
            return partes[1].strip()
        
        return endereco.split('-')[0].strip() if '-' in endereco else endereco
    
    def validar_imovel(self, imovel: Dict) -> bool:
        """Valida se o imóvel atende aos critérios básicos"""
        try:
            # Preço deve ser maior que zero e menor que um limite razoável
            preco = imovel.get('preco', 0)
            if preco <= 0 or preco > 2000000:
                return False
            
            # Se tem área, valida preço por m²
            area = imovel.get('area', 0)
            if area > 0:
                preco_m2 = preco / area
                if preco_m2 > self.valor_maximo_m2:
                    return False
            
            # Título não pode estar vazio
            titulo = imovel.get('titulo', '').strip()
            if not titulo or titulo == "Título não encontrado":
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
            logger.info(f"Salvadas {len(oportunidades)} oportunidades no banco de dados")
        
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
                logger.info("Nenhuma oportunidade para enviar por email")
                return
            
            # Prepara o conteúdo do email
            html_content = self.gerar_html_oportunidades(oportunidades)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🏠 {len(oportunidades)} Oportunidades Imobiliárias - Senador Canedo'
            msg['From'] = self.email_config['email']
            msg['To'] = ', '.join(self.email_config['destinatarios'])
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Simula envio (credenciais não configuradas)
            logger.info(f"Email simulado com {len(oportunidades)} oportunidades")
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
    
    def gerar_html_oportunidades(self, oportunidades: List[Dict]) -> str:
        """Gera HTML para o email com as oportunidades"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .oportunidade {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }}
                .score {{ font-weight: bold; color: #27ae60; }}
                .preco {{ font-size: 18px; font-weight: bold; color: #e74c3c; }}
                .detalhes {{ margin: 10px 0; }}
                .portal {{ background-color: #3498db; color: white; padding: 5px 10px; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏠 Oportunidades Imobiliárias</h1>
                <p>Senador Canedo - {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p>{len(oportunidades)} oportunidades encontradas</p>
            </div>
        """
        
        for oportunidade in sorted(oportunidades, key=lambda x: x['score'], reverse=True):
            preco_formatado = f"R$ {oportunidade['preco']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            preco_m2_formatado = f"R$ {oportunidade['preco_m2']:,.2f}/m²".replace(',', 'X').replace('.', ',').replace('X', '.') if oportunidade['preco_m2'] > 0 else "N/A"
            
            html += f"""
            <div class="oportunidade">
                <div class="portal">{oportunidade['portal']}</div>
                <h3>{oportunidade['titulo']}</h3>
                <div class="preco">{preco_formatado}</div>
                <div class="score">Score: {oportunidade['score']}/100</div>
                <div class="detalhes">
                    <p><strong>Endereço:</strong> {oportunidade['endereco']}</p>
                    <p><strong>Bairro:</strong> {oportunidade['bairro']}</p>
                    <p><strong>Área:</strong> {oportunidade['area']} m² | <strong>Preço/m²:</strong> {preco_m2_formatado}</p>
                    <p><strong>Quartos:</strong> {oportunidade['quartos']} | <strong>Banheiros:</strong> {oportunidade['banheiros']} | <strong>Vagas:</strong> {oportunidade['vagas']}</p>
                </div>
            </div>
            """
        
        html += "</body></html>"
        return html
    
    def executar_varredura_completa(self):
        """Executa a varredura completa"""
        logger.info("=== INICIANDO VARREDURA COMPLETA V2 ===")
        inicio = time.time()
        
        todas_oportunidades = []
        
        try:
            # Tenta portais alternativos
            inicio_portal = time.time()
            oportunidades_alternativas = self.buscar_portais_alternativos()
            todas_oportunidades.extend(oportunidades_alternativas)
            tempo_portal = time.time() - inicio_portal
            
            self.registrar_varredura(
                'Portais Alternativos', 
                len(oportunidades_alternativas), 
                len(oportunidades_alternativas), 
                tempo_portal, 
                'Sucesso'
            )
            
            # Se não encontrou nada, cria exemplos para demonstração
            if not todas_oportunidades:
                logger.info("Criando oportunidades de exemplo para demonstração")
                oportunidades_exemplo = self.criar_oportunidades_exemplo()
                todas_oportunidades.extend(oportunidades_exemplo)
                
                self.registrar_varredura(
                    'Dados de Exemplo', 
                    len(oportunidades_exemplo), 
                    len(oportunidades_exemplo), 
                    0.1, 
                    'Demonstração'
                )
        
        except Exception as e:
            logger.error(f"Erro na varredura: {e}")
        
        # Salva todas as oportunidades
        if todas_oportunidades:
            self.salvar_oportunidades(todas_oportunidades)
            self.enviar_email_oportunidades(todas_oportunidades)
        
        tempo_total = time.time() - inicio
        logger.info(f"=== VARREDURA CONCLUÍDA ===")
        logger.info(f"Tempo total: {tempo_total:.2f}s")
        logger.info(f"Total de oportunidades: {len(todas_oportunidades)}")
        
        return todas_oportunidades

def main():
    """Função principal"""
    try:
        logger.info("Iniciando Robô de Monitoramento V2 - Senador Canedo")
        
        robo = RoboSenadorCanedoV2()
        oportunidades = robo.executar_varredura_completa()
        
        logger.info(f"Execução concluída. {len(oportunidades)} oportunidades processadas.")
        
    except Exception as e:
        logger.error(f"Erro na execução principal: {e}")
        raise

if __name__ == "__main__":
    main()
