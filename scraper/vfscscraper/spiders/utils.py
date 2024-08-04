def abort_request(request):
    return request.resource_type in ["image", "media", "font"]
