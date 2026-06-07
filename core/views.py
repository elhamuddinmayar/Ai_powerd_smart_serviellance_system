from django.shortcuts import redirect
from django.conf import settings
from django.utils import translation

def set_language(request, lang_code):
    # Check if the language is supported in your settings.LANGUAGES
    if any(lang_code == l[0] for l in settings.LANGUAGES):
        # 1. Activate the language for the current thread
        translation.activate(lang_code)
        
        next_url = request.META.get('HTTP_REFERER', '/')
        response = redirect(next_url)
        
        # 2. Set the Cookie (This is the most important part for persistence)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
        
        # 3. Update the Session (Fixing the AttributeError)
        if hasattr(request, 'session'):
            # Django uses '_language' as the session key for translations
            request.session['_language'] = lang_code
            
        return response
        
    return redirect('home')