from django.urls import include, path

urlpatterns = [
    path('account/', include("user.urls")),
    path('branch/', include("branch.urls")),
    path('staff/', include("staff.urls")),
]
