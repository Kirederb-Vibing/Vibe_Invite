from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Redirect users with must_change_password=True to the password change page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.must_change_password
        ):
            allowed = (
                reverse('force_password_change'),
                reverse('logout'),
            )
            if request.path not in allowed:
                return redirect('force_password_change')

        return self.get_response(request)
