from . import sef

FLOWS = {
    "sef": sef
}

def get_flow_handler(producto):
    return FLOWS.get(producto)
