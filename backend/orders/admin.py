from django.contrib import admin

from .models import Label, Order, OrderStageProgress, Part, PartRoute, Product


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # current_stage/stage_status must only change through
    # production_workflow.py (which keeps OrderStageProgress in sync).
    # Editing them here directly would desync the production board from the
    # order's real stage history.
    readonly_fields = ["current_stage", "stage_status"]


admin.site.register(OrderStageProgress)
admin.site.register(Product)
admin.site.register(Part)
admin.site.register(PartRoute)
admin.site.register(Label)
