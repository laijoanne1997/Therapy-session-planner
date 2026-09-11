from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from . import ai
from .forms import (
    ActivityBlockForm,
    ChildIntakeForm,
    GoalIntakeForm,
    GoalRefineForm,
    HomeProgramForm,
    OptionPointForm,
    SessionPlanSetupForm,
)
from .models import ActivityBlock, Child, Goal, OptionPoint, Resource, SessionPlan


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


class ChildDeleteView(LoginRequiredMixin, DeleteView):
    model = Child
    template_name = "planner/confirm_delete.html"
    success_url = reverse_lazy("dashboard")


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


class GoalSuggestView(LoginRequiredMixin, View):
    """POST-only: calls the AI, then re-renders the refine form pre-filled
    with the suggestion (not saved) for the therapist to review and edit."""

    def post(self, request, pk):
        goal = get_object_or_404(Goal, pk=pk)
        try:
            suggestion = ai.suggest_goal_refinement(goal)
        except ai.AIGenerationError as exc:
            messages.error(request, f"AI suggestion failed: {exc}")
            return redirect("goal-refine", pk=goal.pk)
        form = GoalRefineForm(instance=goal, initial=suggestion)
        return render(request, "planner/goal_refine.html", {
            "goal": goal, "form": form, "ai_suggested": True,
        })


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

    def get(self, request, *args, **kwargs):
        ai_error = request.GET.get("ai_error")
        if ai_error:
            messages.error(request, f"AI suggestion failed: {ai_error}")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blocks = self.object.blocks.all()
        context["blocks"] = blocks
        context["total_minutes"] = sum(b.duration_minutes for b in blocks)
        context["home_program"] = getattr(self.object, "home_program", None)
        return context


def _session_key(plan_pk):
    return f"ai_suggested_blocks_{plan_pk}"


def _serialize_block(block):
    resources = block["resources"]
    return {
        **{k: v for k, v in block.items() if k != "resources"},
        "resource_ids": [r.pk for r in resources],
        "resource_names": [r.name for r in resources],
    }


class SessionPlanSuggestView(LoginRequiredMixin, View):
    """GET renders an instant loading screen (no AI call yet — that's what
    makes it possible to show a custom spinner/quotes while the real,
    slow call happens). Its JS then POSTs here to actually run the AI and
    store the result in the session, before redirecting to the review page."""

    template_name = "planner/session_plan_suggest_loading.html"

    def get(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        return render(request, self.template_name, {"plan": plan})

    def post(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        try:
            blocks = ai.suggest_activity_blocks(plan)
        except ai.AIGenerationError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)

        request.session[_session_key(plan.pk)] = [_serialize_block(b) for b in blocks]
        return JsonResponse({"ok": True})


class SessionPlanSuggestReviewView(LoginRequiredMixin, View):
    """GET reads the suggestion already stored in the session (no AI call)
    and shows a checkbox preview. POST creates ActivityBlocks only for the
    ones the therapist selected — nothing is saved until this point."""

    template_name = "planner/session_plan_suggest.html"

    def get(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        blocks = request.session.get(_session_key(plan.pk))
        if blocks is None:
            messages.error(request, "No AI suggestions to review yet — try generating again.")
            return redirect("session-plan-detail", pk=plan.pk)
        return render(request, self.template_name, {"plan": plan, "blocks": blocks})

    def post(self, request, plan_pk):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        blocks = request.session.get(_session_key(plan.pk), [])
        selected = {int(i) for i in request.POST.getlist("include")}

        next_order = plan.blocks.count() + 1
        created = 0
        for i, block in enumerate(blocks):
            if i not in selected:
                continue
            activity_block = ActivityBlock.objects.create(
                session_plan=plan,
                block_type=block["block_type"],
                order=next_order,
                duration_minutes=block["duration_minutes"],
                title=block["title"],
                activity_description=block["activity_description"],
                clinical_reasoning=block["clinical_reasoning"],
                grade_up_note=block.get("grade_up_note", ""),
                grade_down_note=block.get("grade_down_note", ""),
            )
            activity_block.resources.set(Resource.objects.filter(pk__in=block.get("resource_ids", [])))
            next_order += 1
            created += 1

        request.session.pop(_session_key(plan.pk), None)
        messages.success(request, f"Added {created} AI-suggested activity block(s).")
        return redirect("session-plan-detail", pk=plan.pk)


class SessionPlanSuggestRefreshView(LoginRequiredMixin, View):
    """POST-only, called via fetch from the review page: regenerates just
    one suggested block (by its index in the session list) and returns it
    as JSON for the front end to swap in with an animation."""

    def post(self, request, plan_pk, index):
        plan = get_object_or_404(SessionPlan, pk=plan_pk)
        blocks = request.session.get(_session_key(plan.pk))
        if blocks is None or not (0 <= index < len(blocks)):
            return JsonResponse({"ok": False, "error": "That suggestion has expired — regenerate the whole set."}, status=400)

        current = blocks[index]
        other_blocks = [b for i, b in enumerate(blocks) if i != index]
        try:
            new_block = ai.suggest_single_block(plan, current, other_blocks)
        except ai.AIGenerationError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)

        serialized = _serialize_block(new_block)
        blocks[index] = serialized
        request.session[_session_key(plan.pk)] = blocks
        return JsonResponse({"ok": True, "block": serialized})


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
