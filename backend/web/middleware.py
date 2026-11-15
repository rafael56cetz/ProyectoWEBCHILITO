class SecurityHeaders:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['X-Frame-Options']='DENY'
        if request.path.startswith(('/api/','/_allauth/')):
            response['Cache-Control']='no-store'
            response['Vary']='Cookie'
        return response
