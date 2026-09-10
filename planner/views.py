from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    ActivityBlockForm,
    ChildIntakeForm,
    GoalIntakeForm,
    GoalRefineForm,
    HomeProgramForm,
    OptionPointForm,
    SessionPlanSetupForm,
)
from .models import ActivityBlock, Child, Goal, OptionPoint, SessionPlan


class DashboardView(LoginRequiredMixin, ListView):
    model = Child
    context_object_name = "children"
    template_name = "planner/dashboard.html"
    ordering = ["-created_at"]


class ChildIntakeView(LoginRequiredMixin, View):
    template_name = "planner/child_intake.html"

    def get(self, request):
        return render(request, self.template_name, {
            "child_form": ChildIntakeForm(),
            "goal_form": GoalIntakeForm(),
        })

    def post(self, request):
        child_form = ChildIntakeForm(request.POST)
        goal_form = GoalIntakeForm(request.POST)
        if child_form.is_valid() and goal_form.is_valid():
            with transaction.atomic():
                child = child_form.save()
                goal = goal_form.save(commit=False)
                goal.child = child
                goal.save()
            return redirect("goal-refine", pk=goal.pk)
        return render(request, self.template_name, {
            "child_form": child_form,
            "goal_form": goal_form,
        })


class ChildDetailView(LoginRequiredMixin, DetailView):
    model = Child
    context_object_name = "child"
    template_name = "planner/child_detail.html"


class GoalCreateForChildView(LoginRequiredMixin, View):
    template_name = "planner/goal_create.html"

    def get(self, request, child_pk):
        child = get_object_or_404(Child, pk=child_pk)
        return render(request, self.template_name, {"child": child, "goal_form": GoalIntakeForm()})

    def post(self, request, child_pk):
        child = get_object_or_404(Child, pk=child_pk)
        goal_form = GoalIntakeForm(request.POST)
        if goal_form.is_valid():
            goal = goal_form.save(commit=False)
            goal.child = child
            goal.save()
            return redirect("goal-refine", pk=goal.pk)
        return render(request, self.template_name, {"child": child, "goal_form": goal_form})


class GoalRefineView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalRefineForm
    template_name = "planner/goal_refine.html"
    context_object_name = "goal"

    def get_success_url(self):
        return reverse("option-point-list", kwargs={"goal_pk": self.object.pk})


class OptionPointListView(LoginRequiredMixin, View):
    template_name = "planner/option_point_list.html"

    def get(self, request, goal_pk):
        goal = get_object_or_404(Goal, pk=goal_pk)
        return render(request, self.template_name, {
            "goal": goal, "option_points": goal.option_points.all(),
        })


class OptionPointCreateView(LoginRequiredMixin, CreateView):
    model = OptionPoint
    form_class = OptionPointForm
    template_name = "planner/option_point_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["goal"] = get_object_or_404(Goal, pk=self.kwargs["goal_pk"])
        return context

    def form_valid(self, form):
        form.instance.goal = get_object_or_404(Goal, pk=self.kwargs["goal_pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("option-point-list", kwargs={"goal_pk": self.kwargs["goal_pk"]})


class OptionPointUpdateView(LoginRequiredMixin, UpdateView):
    model = OptionPoint
    form_class = OptionPointForm
    template_name = "planner/option_point_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["goal"] = self.object.goal
        return context

    def get_success_url(self):
        return reverse("option-point-list", kwargs={"goal_pk": self.object.goal_id})


class OptionPointDeleteView(LoginRequiredMixin, DeleteView):
    model = OptionPoint
    template_name = "planner/confirm_delete.html"

    def get_success_url(self):
        return reverse("option-point-list", kwargs={"goal_pk": self.object.goal_id})


class SessionPlanSetupView(LoginRequiredMixin, View):
    template_name = "planner/session_plan_setup.html"

    def get(self, request, goal_pk):
        goal = get_object_or_404(Goal, pk=goal_pk)
        existing = goal.session_plans.first()
        if existing:
            return redirect("session-plan-detail", pk=existing.pk)
        form = SessionPlanSetupForm(initial={
            "session_length_minutes": 45,
            "environment": goal.child.default_environment,
        })
        return render(request, self.template_name, {"goal": goal, "form": form})

    def post(self, request, goal_pk):
        goal = get_object_or_404(Goal, pk=goal_pk)
        form = SessionPlanSetupForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.goal = goal
            plan.save()
            return redirect("session-plan-detail", pk=plan.pk)
        return render(request, self.template_name, {"goal": goal, "form": form})


class SessionPlanDetailView(LoginRequiredMixin, DetailView):
    model = SessionPlan
    context_object_name = "plan"
    template_name = "planner/session_plan_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blocks = self.object.blocks.all()
        context["blocks"] = blocks
        context["total_minutes"] = sum(b.duration_minutes for b in blocks)
        context["home_program"] = getattr(self.object, "home_program", None)
        return context


class ActivityBlockCreateView(LoginRequiredMixin, CreateView):
    model = ActivityBlock
    form_class = ActivityBlockForm
    template_name = "planner/activity_block_form.html"

    def get_plan(self):
        return get_object_or_404(SessionPlan, pk=self.kwargs["plan_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["domain"] = self.get_plan().goal.domain
        return kwargs

    def get_initial(self):
        plan = self.get_plan()
        last_order = plan.blocks.count()
        return {"order": last_order + 1, "duration_minutes": 5}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plan"] = self.get_plan()
        return context

    def form_valid(self, form):
        form.instance.session_plan = self.get_plan()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("session-plan-detail", kwargs={"pk": self.kwargs["plan_pk"]})


class ActivityBlockUpdateView(LoginRequiredMixin, UpdateView):
    model = ActivityBlock
    form_class = ActivityBlockForm
    template_name = "planner/activity_block_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["domain"] = self.object.session_plan.goal.domain
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plan"] = self.object.session_plan
        return context

    def get_success_url(self):
        return reverse("session-plan-detail", kwargs={"pk": self.object.session_plan_id})


class ActivityBlockDeleteView(LoginRequiredMixin, DeleteView):
    model = ActivityBlock
    template_name = "planner/confirm_delete.html"

    def get_success_url(self):
        return reverse("session-plan-detail", kwargs={"pk": self.object.session_plan_id})


class HomeProgramEditView(LoginRequiredMixin, View):
    template_name = "planner/home_program_form.html"

    def get(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        form = HomeProgramForm(instance=getattr(plan, "home_program", None))
        return render(request, self.template_name, {"plan": plan, "form": form})

    def post(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        form = HomeProgramForm(request.POST, instance=getattr(plan, "home_program", None))
        if form.is_valid():
            home_program = form.save(commit=False)
            home_program.session_plan = plan
            home_program.save()
            form.save_m2m()
            return redirect("session-plan-detail", pk=plan.pk)
        return render(request, self.template_name, {"plan": plan, "form": form})


class SessionPlanExportView(LoginRequiredMixin, DetailView):
    model = SessionPlan
    context_object_name = "plan"
    template_name = "planner/session_plan_export.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blocks = self.object.blocks.all()
        context["blocks"] = blocks
        context["total_minutes"] = sum(b.duration_minutes for b in blocks)
        context["home_program"] = getattr(self.object, "home_program", None)
        context["family_friendly"] = self.request.GET.get("family") == "1"
        return context
