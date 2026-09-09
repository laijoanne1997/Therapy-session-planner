from django.contrib import admin

from .models import (
    ActivityBlock,
    Child,
    Domain,
    Goal,
    GradingLever,
    HomeProgram,
    Interest,
    OptionPoint,
    Proforma,
    ProformaDomainImplication,
    Resource,
    SessionPlan,
    SubSkill,
)


class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 1


class GradingLeverInline(admin.TabularInline):
    model = GradingLever
    extra = 1


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "parent_domain")
    list_filter = ("parent_domain",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubSkillInline, GradingLeverInline]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class ProformaDomainImplicationInline(admin.TabularInline):
    model = ProformaDomainImplication
    extra = 1


@admin.register(Proforma)
class ProformaAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
    search_fields = ("name", "brief_description")
    filter_horizontal = ("related_proformas",)
    inlines = [ProformaDomainImplicationInline]


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "cost_type", "cost_amount", "review_status")
    list_filter = ("resource_type", "cost_type", "review_status", "domains")
    search_fields = ("name", "platform")
    filter_horizontal = ("domains", "sub_skills", "grading_levers", "interests")


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("initial_or_name", "age_years", "age_months", "default_environment", "created_at")
    list_filter = ("default_environment", "proformas")
    search_fields = ("initial_or_name",)
    filter_horizontal = ("interests", "proformas")


class OptionPointInline(admin.TabularInline):
    model = OptionPoint
    extra = 0


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("__str__", "child", "domain", "created_at")
    list_filter = ("domain",)
    search_fields = ("raw_goal_text", "interim_goal_text", "outcome_goal_text")
    inlines = [OptionPointInline]


class ActivityBlockInline(admin.TabularInline):
    model = ActivityBlock
    extra = 0


@admin.register(SessionPlan)
class SessionPlanAdmin(admin.ModelAdmin):
    list_display = ("__str__", "goal", "session_length_minutes", "environment", "created_at")
    list_filter = ("environment",)
    inlines = [ActivityBlockInline]


@admin.register(HomeProgram)
class HomeProgramAdmin(admin.ModelAdmin):
    list_display = ("__str__", "frequency")
    filter_horizontal = ("home_resources",)
