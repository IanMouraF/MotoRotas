# 🛵 MotoRotas - Otimizador de Rotas iFood

Este repositório contém uma **Prova de Conceito (PoC)** de um sistema backend em Python que se conecta à API do iFood, coleta pedidos em tempo real e utiliza algoritmos de otimização geográfica para agrupar entregas em rotas inteligentes.

---

## 🏗️ Arquitetura do Sistema

O sistema opera com um fluxo totalmente automatizado de coleta e despacho.

```mermaid
flowchart LR
 subgraph subGraph0["Fontes Externas"]
        iFood_API["API do iFood"]
        Google_Maps_API["API do Google Maps"]
  end
 subgraph subGraph1["Nossa Aplicação"]
        Backend["Backend (Algoritmo de Rota e Atribuição)"]
        Database["Banco de Dados (Pedidos, Rotas, Motoboys)"]
        Backoffice["Painel do Gestor (Supervisão)"]
        AppMotoboy["App do Motoboy (Status e Rotas)"]
  end
 subgraph s1["Usuários"]
        Gestor["Gestor da Loja"]
        Motoboy["Motoboy"]
  end
    iFood_API -- Novo pedido --> Backend
    Backend -- Busca detalhes do pedido --> iFood_API
    Backend -- Salva pedido no BD --> Database
    Backend -- "Loop: Analisa pedidos e agrupa em pré-rotas" --> Database
    Motoboy -- Avisa 'Estou disponível' --> AppMotoboy
    AppMotoboy -- Envia status 'Disponível' para o Backend --> Backend
    Gestor -- Marca motoboy como 'Disponível' --> Backoffice
    Backoffice -- Envia status 'Disponível' para o Backend --> Backend
    Backend -- Recebe status 'Disponível' e escolhe rota prioritária --> Database
    Backend -- Atribui rota ao motoboy e gera link --> Google_Maps_API
    Google_Maps_API -- Retorna link da rota --> Backend
    Backend -- Salva rota final no BD --> Database
    Database -- Envia rota para o App do Motoboy --> AppMotoboy
    Motoboy -- Clica em 'Iniciar Navegação' --> AppMotoboy
    AppMotoboy -- Abre o link no Google Maps --> Google_Maps_API
    Database -- Exibe status das rotas e motoboys --> Backoffice
    Gestor -- Monitora painel --> Backoffice
````

-----

## ⚙️ Configuração e Instalação

### 1\. Configure as Credenciais

O sistema precisa das chaves de acesso do iFood.

1.  Renomeie o arquivo `.env.example` para `.env`.
2.  Abra o arquivo `.env` e insira suas credenciais:
    ```ini
    IFOOD_CLIENT_ID=seu_client_id
    IFOOD_CLIENT_SECRET=seu_client_secret
    ```

### 2\. Instale as Dependências

Com seu ambiente virtual ativo, instale os pacotes necessários:

```bash
pip install -r requirements.txt
```

-----

## 🚀 Como Rodar o Projeto

Para iniciar o servidor da API e os serviços de fundo (Coletor e Processador de Rotas) simultaneamente:

```bash
python run.py
```

O sistema irá:

1.  Verificar e criar o banco de dados (`motorotas.db`) automaticamente.
2.  Iniciar o **Coletor** (busca pedidos no iFood).
3.  Iniciar o **Processador** (cria rotas otimizadas).
4.  Subir a API em `http://127.0.0.1:5000`.

-----

## 🧪 Testes Automatizados

O projeto utiliza `pytest` para garantir a qualidade do código. Para rodar os testes:

```bash
python -m pytest
```

-----

## 🛠️ Ferramentas Manuais (Scripts)

Para testar o sistema localmente sem precisar de pedidos reais do iFood, utilize os scripts utilitários:

  - **Gerar Pedidos de Teste:**
    Cria pedidos aleatórios ou manuais no banco de dados.

    ```bash
    python -m scripts.create_test_order
    ```

  - **Visualizar Rotas Criadas:**
    Lista as rotas geradas e exibe os links do Google Maps.

    ```bash
    python -m scripts.view_routes
    ```

  - **Limpar Banco de Dados:**
    Reseta as rotas ou apaga todos os dados para novos testes.

    ```bash
    python -m scripts.clear_database
    ```