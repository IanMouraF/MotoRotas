# Usa uma imagem leve do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os requisitos primeiro (para aproveitar o cache do Docker)
COPY requirements.txt .

# Instala as dependências
# O --no-cache-dir deixa a imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do projeto para dentro do container
COPY . .

# Expõe a porta 5000 (a mesma do Flask)
EXPOSE 5000

# Comando para rodar o app quando o container iniciar
CMD ["python", "run.py"]