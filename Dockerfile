FROM mcr.microsoft.com/playwright/python:v1.45.0-noble

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código do projeto
COPY . .

# Criar pastas necessárias
RUN mkdir -p data workspace_output screenshots

CMD ["python", "-u", "run.py", "--telegram"]
