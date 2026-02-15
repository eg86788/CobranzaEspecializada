from app import create_app
from app.routes_root import init_root_routes  # registra la ruta "/"

import logging

# Configuración de logging
# logging.basicConfig(
#     level=logging.DEBUG,  # Cambia a INFO en producción
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
# )

app = create_app()
init_root_routes(app)

if __name__ == "__main__":
    app.run(debug=True)
