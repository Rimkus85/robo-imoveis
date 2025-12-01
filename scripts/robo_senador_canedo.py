#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô de Monitoramento de Oportunidades Imobiliárias - Senador Canedo
Desenvolvido para varrer portais imobiliários e identificar oportunidades de investimento
"""

import requests
import sqlite3
import smtplib
import logging
import time
import json
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
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

class RoboSenadorCanedo:
    def __init__(self):
        self.db_path = '/home/ubuntu/oportunidades_senador_canedo.db'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
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
        
        # Configurações de email
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'email': os.getenv('EMAIL_USUARIO', 'seu_email@gmail.com'),
            'senha': os.getenv('EMAIL_SENHA', 'sua_senha_app'),
            'destinatarios': ['investidor@exemplo.com']  # Lista de destinatários
        }
        
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
        
        return min(score, 100)  # Score máximo de 100
    
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
    
    def varrer_zap_imoveis(self) -> List[Dict]:
        """Varre o portal ZAP Imóveis"""
        logger.info("Iniciando varredura do ZAP Imóveis")
        oportunidades = []
        
        try:
            # URL de busca para Senador Canedo - apartamentos e casas para venda
            url_base = "https://www.zapimoveis.com.br/venda/imoveis/go+senador-canedo/"
            
            for pagina in range(1, 6):  # Varre até 5 páginas
                url = f"{url_base}?pagina={pagina}"
                
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Busca por cards de imóveis (estrutura pode variar)
                    cards = soup.find_all(['div', 'article'], class_=re.compile(r'card|listing|result'))
                    
                    for card in cards:
                        try:
                            imovel = self.extrair_dados_imovel_zap(card)
                            if imovel and self.validar_imovel(imovel):
                                score = self.calcular_score(imovel)
                                imovel['score'] = score
                                imovel['portal'] = 'ZAP Imóveis'
                                
                                if score >= self.score_minimo:
                                    oportunidades.append(imovel)
                                    logger.info(f"Oportunidade encontrada no ZAP: {imovel['titulo']} - Score: {score}")
                        
                        except Exception as e:
                            logger.debug(f"Erro ao processar card do ZAP: {e}")
                            continue
                    
                    time.sleep(2)  # Pausa entre páginas
                
                except Exception as e:
                    logger.error(f"Erro ao acessar página {pagina} do ZAP: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral na varredura do ZAP Imóveis: {e}")
        
        logger.info(f"ZAP Imóveis: {len(oportunidades)} oportunidades encontradas")
        return oportunidades
    
    def extrair_dados_imovel_zap(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel do ZAP Imóveis"""
        try:
            # Título
            titulo_elem = card.find(['h2', 'h3', 'a'], class_=re.compile(r'title|name'))
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Título não encontrado"
            
            # Preço
            preco_elem = card.find(['span', 'div'], class_=re.compile(r'price|valor'))
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "0"
            preco = self.extrair_numero(preco_texto)
            
            # Área
            area_elem = card.find(text=re.compile(r'm²|m2'))
            area = 0
            if area_elem:
                area = self.extrair_numero(area_elem.parent.get_text() if area_elem.parent else area_elem)
            
            # Endereço/Bairro
            endereco_elem = card.find(['span', 'div'], class_=re.compile(r'address|location|endereco'))
            endereco = endereco_elem.get_text(strip=True) if endereco_elem else ""
            
            # Quartos, banheiros, vagas
            quartos = self.extrair_caracteristica(card, r'quarto|bedroom|dorm')
            banheiros = self.extrair_caracteristica(card, r'banheiro|bathroom|wc')
            vagas = self.extrair_caracteristica(card, r'vaga|garage|garagem')
            
            # URL
            link_elem = card.find('a', href=True)
            url = urljoin("https://www.zapimoveis.com.br", link_elem['href']) if link_elem else ""
            
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
            logger.debug(f"Erro ao extrair dados do imóvel ZAP: {e}")
            return None
    
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
    
    def varrer_viva_real(self) -> List[Dict]:
        """Varre o portal Viva Real"""
        logger.info("Iniciando varredura do Viva Real")
        oportunidades = []
        
        try:
            # Implementação similar ao ZAP, adaptada para Viva Real
            url_base = "https://www.vivareal.com.br/venda/goias/senador-canedo/"
            
            for pagina in range(1, 4):  # Varre até 3 páginas
                url = f"{url_base}?pagina={pagina}"
                
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    cards = soup.find_all(['div', 'article'], class_=re.compile(r'property|listing|card'))
                    
                    for card in cards:
                        try:
                            imovel = self.extrair_dados_imovel_viva_real(card)
                            if imovel and self.validar_imovel(imovel):
                                score = self.calcular_score(imovel)
                                imovel['score'] = score
                                imovel['portal'] = 'Viva Real'
                                
                                if score >= self.score_minimo:
                                    oportunidades.append(imovel)
                                    logger.info(f"Oportunidade encontrada no Viva Real: {imovel['titulo']} - Score: {score}")
                        
                        except Exception as e:
                            logger.debug(f"Erro ao processar card do Viva Real: {e}")
                            continue
                    
                    time.sleep(2)
                
                except Exception as e:
                    logger.error(f"Erro ao acessar página {pagina} do Viva Real: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral na varredura do Viva Real: {e}")
        
        logger.info(f"Viva Real: {len(oportunidades)} oportunidades encontradas")
        return oportunidades
    
    def extrair_dados_imovel_viva_real(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel do Viva Real"""
        # Implementação similar ao ZAP, adaptada para estrutura do Viva Real
        try:
            titulo_elem = card.find(['h2', 'h3'], class_=re.compile(r'property-card__title'))
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Título não encontrado"
            
            preco_elem = card.find(['span'], class_=re.compile(r'property-card__price'))
            preco_texto = preco_elem.get_text(strip=True) if preco_elem else "0"
            preco = self.extrair_numero(preco_texto)
            
            # Continua com lógica similar...
            return {
                'titulo': titulo,
                'preco': preco,
                'area': 0,  # Implementar extração
                'preco_m2': 0,
                'endereco': "",
                'bairro': "",
                'quartos': 0,
                'banheiros': 0,
                'vagas': 0,
                'url': ""
            }
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados do Viva Real: {e}")
            return None
    
    def varrer_olx(self) -> List[Dict]:
        """Varre o portal OLX"""
        logger.info("Iniciando varredura da OLX")
        oportunidades = []
        
        try:
            # URL de busca para Senador Canedo na OLX
            url_base = "https://go.olx.com.br/regiao-metropolitana-de-goiania/senador-canedo/imoveis/venda"
            
            for pagina in range(1, 4):
                url = f"{url_base}?o={pagina}"
                
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    cards = soup.find_all(['div'], class_=re.compile(r'ad-card|listing'))
                    
                    for card in cards:
                        try:
                            imovel = self.extrair_dados_imovel_olx(card)
                            if imovel and self.validar_imovel(imovel):
                                score = self.calcular_score(imovel)
                                imovel['score'] = score
                                imovel['portal'] = 'OLX'
                                
                                if score >= self.score_minimo:
                                    oportunidades.append(imovel)
                                    logger.info(f"Oportunidade encontrada na OLX: {imovel['titulo']} - Score: {score}")
                        
                        except Exception as e:
                            logger.debug(f"Erro ao processar card da OLX: {e}")
                            continue
                    
                    time.sleep(2)
                
                except Exception as e:
                    logger.error(f"Erro ao acessar página {pagina} da OLX: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral na varredura da OLX: {e}")
        
        logger.info(f"OLX: {len(oportunidades)} oportunidades encontradas")
        return oportunidades
    
    def extrair_dados_imovel_olx(self, card) -> Optional[Dict]:
        """Extrai dados de um imóvel da OLX"""
        # Implementação similar, adaptada para OLX
        try:
            titulo_elem = card.find(['h2', 'h3'], class_=re.compile(r'title'))
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Título não encontrado"
            
            preco_elem = card.find(['span'], class_=re.compile(r'price'))
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
            logger.debug(f"Erro ao extrair dados da OLX: {e}")
            return None
    
    def validar_imovel(self, imovel: Dict) -> bool:
        """Valida se o imóvel atende aos critérios básicos"""
        try:
            # Preço deve ser maior que zero e menor que um limite razoável
            preco = imovel.get('preco', 0)
            if preco <= 0 or preco > 2000000:  # Máximo 2 milhões
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
                self.enviar_email_relatorio_vazio()
                return
            
            # Prepara o conteúdo do email
            html_content = self.gerar_html_oportunidades(oportunidades)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🏠 {len(oportunidades)} Oportunidades Imobiliárias - Senador Canedo'
            msg['From'] = self.email_config['email']
            msg['To'] = ', '.join(self.email_config['destinatarios'])
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Envia o email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email'], self.email_config['senha'])
                server.send_message(msg)
            
            # Marca como enviado no banco
            self.marcar_emails_enviados(oportunidades)
            
            logger.info(f"Email enviado com {len(oportunidades)} oportunidades")
        
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
                    {f'<p><a href="{oportunidade["url"]}" target="_blank">Ver anúncio completo</a></p>' if oportunidade['url'] else ''}
                </div>
            </div>
            """
        
        html += """
            <div style="margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px;">
                <h3>Critérios de Seleção:</h3>
                <ul>
                    <li>Score mínimo: 50 pontos</li>
                    <li>Valor máximo: R$ 2.400/m²</li>
                    <li>Regiões prioritárias: Jardim Europa, Setor Leste, Centro, Setor Sul, Vila Galvão, Parque das Flores, Residencial Eldorado</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def enviar_email_relatorio_vazio(self):
        """Envia email quando não há oportunidades"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = '📊 Relatório de Varredura - Senador Canedo'
            msg['From'] = self.email_config['email']
            msg['To'] = ', '.join(self.email_config['destinatarios'])
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <div style="background-color: #34495e; color: white; padding: 20px; text-align: center;">
                    <h1>📊 Relatório de Varredura</h1>
                    <p>Senador Canedo - {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                <div style="padding: 20px;">
                    <p>A varredura foi concluída, mas não foram encontradas novas oportunidades que atendam aos critérios estabelecidos.</p>
                    <h3>Critérios utilizados:</h3>
                    <ul>
                        <li>Score mínimo: {self.score_minimo} pontos</li>
                        <li>Valor máximo: R$ {self.valor_maximo_m2}/m²</li>
                        <li>Portais verificados: ZAP Imóveis, Viva Real, OLX</li>
                    </ul>
                    <p>O sistema continuará monitorando e enviará alertas quando novas oportunidades forem identificadas.</p>
                </div>
            </body>
            </html>
            """
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email'], self.email_config['senha'])
                server.send_message(msg)
            
            logger.info("Email de relatório vazio enviado")
        
        except Exception as e:
            logger.error(f"Erro ao enviar email de relatório: {e}")
    
    def marcar_emails_enviados(self, oportunidades: List[Dict]):
        """Marca oportunidades como enviadas por email"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for oportunidade in oportunidades:
                cursor.execute('''
                    UPDATE oportunidades 
                    SET enviado_email = TRUE 
                    WHERE titulo = ? AND preco = ? AND portal = ?
                ''', (oportunidade['titulo'], oportunidade['preco'], oportunidade['portal']))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Erro ao marcar emails como enviados: {e}")
    
    def executar_varredura_completa(self):
        """Executa a varredura completa em todos os portais"""
        logger.info("=== INICIANDO VARREDURA COMPLETA ===")
        inicio = time.time()
        
        todas_oportunidades = []
        
        # Varre cada portal
        portais = [
            ('ZAP Imóveis', self.varrer_zap_imoveis),
            ('Viva Real', self.varrer_viva_real),
            ('OLX', self.varrer_olx)
        ]
        
        for nome_portal, funcao_varredura in portais:
            try:
                inicio_portal = time.time()
                logger.info(f"Iniciando varredura do {nome_portal}")
                
                oportunidades_portal = funcao_varredura()
                todas_oportunidades.extend(oportunidades_portal)
                
                tempo_portal = time.time() - inicio_portal
                self.registrar_varredura(
                    nome_portal, 
                    len(oportunidades_portal), 
                    len(oportunidades_portal), 
                    tempo_portal, 
                    'Sucesso'
                )
                
                logger.info(f"{nome_portal} concluído em {tempo_portal:.2f}s - {len(oportunidades_portal)} oportunidades")
                
            except Exception as e:
                logger.error(f"Erro na varredura do {nome_portal}: {e}")
                self.registrar_varredura(nome_portal, 0, 0, 0, f'Erro: {str(e)}')
        
        # Salva todas as oportunidades
        if todas_oportunidades:
            self.salvar_oportunidades(todas_oportunidades)
            self.enviar_email_oportunidades(todas_oportunidades)
        else:
            self.enviar_email_relatorio_vazio()
        
        tempo_total = time.time() - inicio
        logger.info(f"=== VARREDURA CONCLUÍDA ===")
        logger.info(f"Tempo total: {tempo_total:.2f}s")
        logger.info(f"Total de oportunidades: {len(todas_oportunidades)}")
        
        return todas_oportunidades

def main():
    """Função principal"""
    try:
        logger.info("Iniciando Robô de Monitoramento - Senador Canedo")
        
        robo = RoboSenadorCanedo()
        oportunidades = robo.executar_varredura_completa()
        
        logger.info(f"Execução concluída. {len(oportunidades)} oportunidades processadas.")
        
    except Exception as e:
        logger.error(f"Erro na execução principal: {e}")
        raise

if __name__ == "__main__":
    main()
