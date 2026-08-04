from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request) -> JsonResponse:
    return JsonResponse({'status': 'ok'})
