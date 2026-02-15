from . import sef_flow

FLOWS = {
    "sef": sef_flow
}

def get_flow_handler(producto):
    return FLOWS.get(producto)
