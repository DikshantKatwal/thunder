from django.urls import path

from staff import views

urlpatterns =[
    path("invite-staff/", views.InviteStaffViewSet.as_view(), name="Invite Staff"),
    path("accept-invite/", views.AcceptInviteLink.as_view(), name="Accept Invite Staff"),
    path("use-invite/", views.CreateInvitedUserStaff.as_view(), name="Use Invite Staff"),

]
