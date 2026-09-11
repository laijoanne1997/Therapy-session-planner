from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("children/new/", views.ChildIntakeView.as_view(), name="child-intake"),
    path("children/<int:pk>/", views.ChildDetailView.as_view(), name="child-detail"),
    path("children/<int:pk>/delete/", views.ChildDeleteView.as_view(), name="child-delete"),
    path("children/<int:child_pk>/goals/new/", views.GoalCreateForChildView.as_view(), name="goal-create"),
    path("goals/<int:pk>/refine/", views.GoalRefineView.as_view(), name="goal-refine"),
    path("goals/<int:pk>/suggest/", views.GoalSuggestView.as_view(), name="goal-suggest"),
    path("goals/<int:goal_pk>/options/", views.OptionPointListView.as_view(), name="option-point-list"),
    path("goals/<int:goal_pk>/options/new/", views.OptionPointCreateView.as_view(), name="option-point-create"),
    path("options/<int:pk>/edit/", views.OptionPointUpdateView.as_view(), name="option-point-edit"),
    path("options/<int:pk>/delete/", views.OptionPointDeleteView.as_view(), name="option-point-delete"),
    path("goals/<int:goal_pk>/plan/", views.SessionPlanSetupView.as_view(), name="session-plan-setup"),
    path("plans/<int:pk>/", views.SessionPlanDetailView.as_view(), name="session-plan-detail"),
    path("plans/<int:plan_pk>/suggest/", views.SessionPlanSuggestView.as_view(), name="session-plan-suggest"),
    path("plans/<int:plan_pk>/suggest/review/", views.SessionPlanSuggestReviewView.as_view(), name="session-plan-suggest-review"),
    path("plans/<int:plan_pk>/suggest/refresh/<int:index>/", views.SessionPlanSuggestRefreshView.as_view(), name="session-plan-suggest-refresh"),
    path("plans/<int:plan_pk>/blocks/new/", views.ActivityBlockCreateView.as_view(), name="activity-block-create"),
    path("blocks/<int:pk>/edit/", views.ActivityBlockUpdateView.as_view(), name="activity-block-edit"),
    path("blocks/<int:pk>/delete/", views.ActivityBlockDeleteView.as_view(), name="activity-block-delete"),
    path("plans/<int:plan_pk>/home-program/", views.HomeProgramEditView.as_view(), name="home-program-edit"),
    path("plans/<int:pk>/export/", views.SessionPlanExportView.as_view(), name="session-plan-export"),
]
