import serverless_wsgi

def handler(event, context):
    return serverless_wsgi.handle_request(event, context)