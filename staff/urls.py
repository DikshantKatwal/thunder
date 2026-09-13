from django.urls import path
from rest_framework.routers import DefaultRouter

from staff import views
router = DefaultRouter()
router.register("", views.StaffViewSet, basename="Staff")

urlpatterns =[
    path("invite-staff/", views.InviteStaffViewSet.as_view(), name="Invite Staff"),
    path("accept-invite/", views.AcceptInviteLink.as_view(), name="Accept Invite Staff"),
    path("use-invite/", views.CreateInvitedUserStaff.as_view(), name="Use Invite Staff"),
]+router.urls



