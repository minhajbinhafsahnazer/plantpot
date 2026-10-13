class VercelPathMiddleware:
    """
    Normalizes Vercel serverless request path so Django routing matches correctly.
    Handles /api/index.py rewrites and extracts original request URI.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        target_path = None

        # 1. Explicit __path__ parameter from vercel.json rewrite
        if '__path__' in request.GET:
            target_path = request.GET['__path__']

        # 2. Check if current path_info points to index.py
        elif 'index.py' in request.path_info:
            for header in ('HTTP_X_FORWARDED_URI', 'HTTP_RAW_URI', 'HTTP_REQUEST_URI', 'HTTP_X_MATCHED_PATH'):
                val = request.META.get(header)
                if val and 'index.py' not in val:
                    target_path = val.split('?')[0]
                    break
            if not target_path:
                target_path = '/'

        if target_path:
            if not target_path.startswith('/'):
                target_path = '/' + target_path
            request.path_info = target_path
            request.path = target_path

        return self.get_response(request)
