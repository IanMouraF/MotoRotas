Otimizador de Rotas iFood - Prova de Conceito (Python)
Este repositório contém o código inicial em Python para se conectar e autenticar com a API do iFood.

Passos para Configuração
Pré-requisitos:

Você precisa ter o Python (versão 3.8 ou superior) instalado.

Um editor de código como o VS Code com a extensão Python.

Crie a Pasta do Projeto:

No seu computador, crie uma pasta para o projeto. Ex: otimizador-ifood-python.

Adicione os Arquivos:

Copie os arquivos requirements.txt, .gitignore, .env.example e main.py para dentro da sua pasta.

Crie e Ative um Ambiente Virtual (Recomendado):

Abra o terminal na pasta do projeto e execute os comandos:

# Criar o ambiente virtual
python -m venv venv

# Ativar no Windows
.\venv\Scripts\activate

# Ativar no macOS/Linux
source venv/bin/activate

Crie o Arquivo de Credenciais:

Renomeie o arquivo .env.example para .env.

Abra o arquivo .env e cole suas credenciais do iFood.

Instale as Dependências:

Com o ambiente virtual ativo, execute no terminal:

pip install -r requirements.txt

Execute o Teste:

Ainda no terminal, execute o comando:

python main.py

Resultado Esperado:

Se tudo der certo, você verá o accessToken e outras informações no seu console, confirmando a conexão com a API do iFood!