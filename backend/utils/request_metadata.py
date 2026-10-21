"""Bounded request metadata without URL parameters or query credentials."""


def safe_request_route(request):
    route = request.scope.get("route")
    return getattr(route, "path", None) or "/unmatched"
