from .korapay import KorapayGateway

GATEWAY_REGISTRY = {
    "KORAPAY": KorapayGateway,
}


def get_gateway(name: str):
    gateway_cls = GATEWAY_REGISTRY.get(name.upper())
    if not gateway_cls:
        raise ValueError(f"Unknown gateway: {name}")
    return gateway_cls()


__all__ = ["KorapayGateway", "GATEWAY_REGISTRY", "get_gateway"]
