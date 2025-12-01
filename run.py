import threading
from app import create_app
from app.collector import start_collector_loop
from app.routing.processor import start_processor_loop

app = create_app()

if __name__ == "__main__":
    # Inicia threads (mesma lógica que você já tinha)
    print("Iniciando serviços de fundo...")
    threading.Thread(target=start_collector_loop, daemon=True).start()
    threading.Thread(target=start_processor_loop, daemon=True).start()
    
app.run(host='0.0.0.0', debug=True, port=5000, use_reloader=False)