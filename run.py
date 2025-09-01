from app import create_app
from app.routes_root import init_root_routes  # registra la ruta "/"

app = create_app()
init_root_routes(app)

if __name__ == "__main__":
    app.run(debug=True)
