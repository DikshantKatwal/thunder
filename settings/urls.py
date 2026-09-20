from django.urls import include, path

urlpatterns = [
    path('room-settings/', include("settings.room_type.urls")),
]
